export async function onRequest(context) {
  const url = new URL(context.request.url);
  const targetHost = 'www.bbc.com';
  
  // 如果用户访问根目录，自动重定向到中文版首页
  if (url.pathname === '/' || url.pathname === '') {
    url.pathname = '/zhongwen/simp';
  }

  url.host = targetHost;

  const newHeaders = new Headers(context.request.headers);
  newHeaders.set('Host', targetHost);
  newHeaders.set('Referer', `https://${targetHost}/`);
  newHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');

  const modifiedRequest = new Request(url.toString(), {
    method: context.request.method,
    headers: newHeaders,
    body: context.request.body,
    redirect: 'manual' 
  });

  try {
    const response = await fetch(modifiedRequest);
    const responseHeaders = new Headers(response.headers);

    // 允许跨域并移除安全限制，确保图片能加载
    responseHeaders.delete('content-security-policy');
    responseHeaders.set('access-control-allow-origin', '*');

    // 处理 BBC 的重定向（防止它把用户跳回原始域名）
    if ([301, 302, 307, 308].includes(response.status)) {
      const location = response.headers.get('Location');
      if (location) {
        const newLocation = new URL(location, url.origin);
        if (newLocation.host === targetHost) {
          newLocation.host = new URL(context.request.url).host;
        }
        return Response.redirect(newLocation.href, response.status);
      }
    }

    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders
    });
  } catch (e) {
    return new Response('代理 BBC 出错: ' + e.message, { status: 500 });
  }
}
