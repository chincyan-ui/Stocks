export async function onRequest(context) {
  const url = new URL(context.request.url);
  const myHost = url.host;
  
  // --- 1. 媒体路由表配置 ---
  const proxyMap = {
    'bbc': 'www.bbc.com',
    'nyt': 'cn.nytimes.com',
    'wsj': 'cn.wsj.com',
    'reuters': 'www.reuters.com',
    'dw': 'www.dw.com',
    'voa': 'www.voachinese.com',
    'rfi': 'www.rfi.fr',
    'zaobao': 'www.zaobao.com',
    'nikkei': 'cn.nikkei.com',
    'ft': 'chinese.ft.com'
  };

  // --- 2. 识别当前用户想看哪家媒体 ---
  // 路径格式: /bbc/content... 或 /nyt/content...
  const pathParts = url.pathname.split('/').filter(Boolean);
  const prefix = pathParts[0];

  if (!prefix || !proxyMap[prefix]) {
    // 如果直接访问首页，显示导航列表
    return generateIndex(proxyMap, myHost);
  }

  const targetHost = proxyMap[prefix];
  
  // 构造目标 URL：去掉路径里的前缀 (例如把 /bbc/news 变成 /news)
  const targetPath = '/' + pathParts.slice(1).join('/');
  const targetUrl = new URL(targetPath + url.search, `https://${targetHost}`);

  // --- 3. 构造请求头 (深度伪装) ---
  const newHeaders = new Headers(context.request.headers);
  newHeaders.set('Host', targetHost);
  newHeaders.set('Referer', `https://${targetHost}/`);
  newHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');

  try {
    const response = await fetch(targetUrl.toString(), {
      method: context.request.method,
      headers: newHeaders,
      redirect: 'manual'
    });

    let responseHeaders = new Headers(response.headers);
    const contentType = responseHeaders.get('content-type') || '';

    // --- 4. 处理重定向 ---
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      let location = responseHeaders.get('Location');
      if (location) {
        // 将重定向后的地址重新包装回我们的代理路径
        const locUrl = new URL(location, `https://${targetHost}`);
        return Response.redirect(`https://${myHost}/${prefix}${locUrl.pathname}${locUrl.search}`, response.status);
      }
    }

    // --- 5. 处理 HTML 里的链接 (核心：确保点击后不掉队) ---
    if (contentType.includes('text/html')) {
      let text = await response.text();
      // 替换页面中所有的相对路径和绝对路径，加上我们的前缀
      // 这里的正则比较粗暴，但对大多数媒体站有效
      const modifiedText = text
        .replace(/(href|src)="\/(?!\/)/g, `$1="/${prefix}/`) // 替换 /path 为 /prefix/path
        .replace(new RegExp(`https://${targetHost}`, 'g'), `https://${myHost}/${prefix}`)
        .replace('content-security-policy', 'disabled-csp');

      return new Response(modifiedText, {
        status: response.status,
        headers: responseHeaders
      });
    }

    return response;
  } catch (e) {
    return new Response(`代理 ${prefix} 失败: ` + e.message, { status: 500 });
  }
}

// 辅助函数：生成一个简单的导航首页
function generateIndex(map, host) {
  const links = Object.keys(map).map(k => `<li><a href="/${k}/">${k.toUpperCase()} - ${map[k]}</a></li>`).join('');
  const html = `<html><body style="font-family:sans-serif;padding:2rem;">
    <h1>媒体聚合代理</h1>
    <ul>${links}</ul>
    <p style="color:red">注意：部分站点加载较慢，点击链接后请耐心等待。</p>
    </body></html>`;
  return new Response(html, { headers: { 'content-type': 'text/html;charset=UTF-8' } });
}
