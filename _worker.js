import { connect } from 'cloudflare:sockets';

// --- 基础配置区域 ---
let userID = '3182b972-b8b8-4203-beed-832dfa53229a';
let proxyIP = ''; 

export default {
  async fetch(request, env, ctx) {
    try {
      userID = env.UUID || userID;
      proxyIP = env.PROXYIP || proxyIP;

      const upgradeHeader = request.headers.get('Upgrade');
      
      // 【修改点】：如果不是 WebSocket 请求，直接返回 404 或简单页面
      // 不再执行 fetch(newRequest)，从而将 Subrequests 降为 0
      if (!upgradeHeader || upgradeHeader !== 'websocket') {
        return new Response('<html><body><h1>404 Not Found</h1></body></html>', {
          status: 404,
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
      }

      return await vlessOverWSHandler(request);
    } catch (err) {
      return new Response(err.toString(), { status: 500 });
    }
  },
};

/**
 * 处理 VLESS Over WebSocket (保持原样)
 */
async function vlessOverWSHandler(request) {
  const [client, server] = new WebSocketPair();
  server.accept();

  let remoteSocketWapper = { write: null };
  let isVlessHeaderResolved = false;
  let address = '';

  server.addEventListener('message', async (event) => {
    const buffer = event.data;
    if (isVlessHeaderResolved) {
      remoteSocketWapper.write(buffer);
      return;
    }

    if (buffer.byteLength < 24) return;

    const version = new Uint8Array(buffer.slice(0, 1));
    const uuid = [...new Uint8Array(buffer.slice(1, 17))].map(b => b.toString(16).padStart(2, '0')).join('');
    
    if (uuid.replace(/-/g, '') !== userID.replace(/-/g, '')) return;

    const optLength = new Uint8Array(buffer.slice(17, 18))[0];
    const command = new Uint8Array(buffer.slice(18 + optLength, 19 + optLength))[0];

    if (command !== 1) return;

    const portIndex = 19 + optLength;
    const port = new DataView(buffer.slice(portIndex, portIndex + 2)).getUint16(0);
    const addressIndex = portIndex + 2;
    const addressType = new Uint8Array(buffer.slice(addressIndex, addressIndex + 1))[0];

    let addressLength = 0;
    let addressValueIndex = addressIndex + 1;

    if (addressType === 1) { 
      addressLength = 4;
      address = new Uint8Array(buffer.slice(addressValueIndex, addressValueIndex + addressLength)).join('.');
    } else if (addressType === 2) { 
      addressLength = new Uint8Array(buffer.slice(addressValueIndex, addressValueIndex + 1))[0];
      addressValueIndex += 1;
      address = new TextDecoder().decode(buffer.slice(addressValueIndex, addressValueIndex + addressLength));
    } else if (addressType === 3) { 
      addressLength = 16;
      const dataView = new DataView(buffer.slice(addressValueIndex, addressValueIndex + addressLength));
      const ipv6 = [];
      for (let i = 0; i < 8; i++) ipv6.push(dataView.getUint16(i * 2).toString(16));
      address = ipv6.join(':');
    }

    const vlessData = buffer.slice(addressValueIndex + addressLength);

    try {
      const tcpSocket = connect({ hostname: address, port: port });
      remoteSocketWapper.write = (data) => {
        const writer = tcpSocket.writable.getWriter();
        writer.write(data);
        writer.releaseLock();
      };

      isVlessHeaderResolved = true;
      server.send(new Uint8Array([version[0], 0]));

      if (vlessData.byteLength > 0) remoteSocketWapper.write(vlessData);

      tcpSocket.readable.pipeTo(new WritableStream({
        write(chunk) { server.send(chunk); }
      }));
    } catch (e) {
      server.close();
    }
  });

  return new Response(null, { status: 101, webSocket: client });
}
