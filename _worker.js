import { connect } from 'cloudflare:sockets';

// --- 基础配置区域 ---
// 1. UUID: 必须与你客户端配置的 UUID 一致（可使用 uuidgenerator.net 生成）
let userID = '3182b972-b8b8-4203-beed-832dfa53229a';

// 2. 伪装网页: 当直接访问域名时显示的页面地址（可选）
let proxyIP = ''; // 如果你觉得速度慢，可以填入优选后的 IP/域名

export default {
  async fetch(request, env, ctx) {
    try {
      // 优先从环境变量读取 UUID，如果环境变量不存在则使用上方定义的默认值
      userID = env.UUID || userID;
      proxyIP = env.PROXYIP || proxyIP;

      const upgradeHeader = request.headers.get('Upgrade');
      if (!upgradeHeader || upgradeHeader !== 'websocket') {
        // 如果不是 WebSocket 请求，则返回一个普通的网页（伪装）
        const url = new URL(request.url);
        url.hostname = 'www.google.com'; // 你可以改为任何其他网站
        const newRequest = new Request(url, request);
        return fetch(newRequest);
      }

      return await vlessOverWSHandler(request);
    } catch (err) {
      return new Response(err.toString(), { status: 500 });
    }
  },
};

/**
 * 处理 VLESS Over WebSocket
 */
async function vlessOverWSHandler(request) {
  const webSocketPair = new ArrayBuffer(0);
  const [client, server] = new Array(2).fill(null).map(() => new WebSocketPair());

  server.accept();

  let remoteSocketWapper = {
    read: null,
    write: null,
  };

  let isVlessHeaderResolved = false;
  let address = '';
  let portWithRandomLog = '';

  // 监听来自客户端的数据
  server.addEventListener('message', async (event) => {
    const message = event.data;
    if (isVlessHeaderResolved) {
      // 转发数据到目标服务器
      remoteSocketWapper.write(message);
      return;
    }

    // 解析 VLESS 头部
    const buffer = message;
    if (buffer.byteLength < 24) {
      return; // 头部长度不足
    }

    const version = new Uint8Array(buffer.slice(0, 1));
    const uuid = [...new Uint8Array(buffer.slice(1, 17))].map(b => b.toString(16).padStart(2, '0')).join('');
    
    // 验证 UUID
    if (uuid.replace(/-/g, '') !== userID.replace(/-/g, '')) {
      return; 
    }

    const optLength = new Uint8Array(buffer.slice(17, 18))[0];
    const command = new Uint8Array(buffer.slice(18 + optLength, 19 + optLength))[0];

    // 仅支持 CONNECT 命令 (0x01)
    if (command !== 1) {
      return;
    }

    const portIndex = 19 + optLength;
    const port = new DataView(buffer.slice(portIndex, portIndex + 2)).getUint16(0);

    const addressIndex = portIndex + 2;
    const addressType = new Uint8Array(buffer.slice(addressIndex, addressIndex + 1))[0];

    let addressLength = 0;
    let addressValueIndex = addressIndex + 1;

    if (addressType === 1) { // IPv4
      addressLength = 4;
      address = new Uint8Array(buffer.slice(addressValueIndex, addressValueIndex + addressLength)).join('.');
    } else if (addressType === 2) { // Domain
      addressLength = new Uint8Array(buffer.slice(addressValueIndex, addressValueIndex + 1))[0];
      addressValueIndex += 1;
      address = new TextDecoder().decode(buffer.slice(addressValueIndex, addressValueIndex + addressLength));
    } else if (addressType === 3) { // IPv6
      addressLength = 16;
      const dataView = new DataView(buffer.slice(addressValueIndex, addressValueIndex + addressLength));
      const ipv6 = [];
      for (let i = 0; i < 8; i++) {
        ipv6.push(dataView.getUint16(i * 2).toString(16));
      }
      address = ipv6.join(':');
    }

    const vlessDataIndex = addressValueIndex + addressLength;
    const vlessData = buffer.slice(vlessDataIndex);

    // 建立与远程目标的连接
    try {
      const tcpSocket = connect({
        hostname: address,
        port: port,
      });

      remoteSocketWapper.write = (data) => {
        const writer = tcpSocket.writable.getWriter();
        writer.write(data);
        writer.releaseLock();
      };

      isVlessHeaderResolved = true;

      // 响应 VLESS 握手成功 (0x00 0x00)
      server.send(new Uint8Array([version[0], 0]));

      // 将剩余数据发送到远程
      if (vlessData.byteLength > 0) {
        remoteSocketWapper.write(vlessData);
      }

      // 管道传输：远程 -> 客户端
      tcpSocket.readable.pipeTo(new WritableStream({
        write(chunk) {
          server.send(chunk);
        }
      }));

    } catch (e) {
      server.close();
    }
  });

  server.addEventListener('close', () => {
    // 处理连接关闭
  });

  server.addEventListener('error', () => {
    // 处理错误
  });

  return new Response(null, {
    status: 101,
    webSocket: client,
  });
}
