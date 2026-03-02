export async function onRequest(context) {
  const url = new URL(context.request.url);
  const targetHost = 'www.youtube.com';
  
  // 将你的域名替换为 YouTube 域名
  url.host = targetHost;

  // 1. 深度伪装请求头
  const newHeaders = new Headers(context.request.headers);
  newHeaders.set('Host', targetHost);
  newHeaders.set('Origin', `https://${targetHost}`);
  newHeaders.set('Referer', `https://${targetHost}/`);
  // 模拟一个真实的 Chrome 浏览器
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

    // 2. 移除安全限制头，允许在你的域名下加载资源
    responseHeaders.delete('content-security-policy');
    responseHeaders.delete('content-security-policy-report-only');
    responseHeaders.delete('clear-site-data');

    // 3. 处理重定向 (301, 302)，防止跳回 youtube.com
    if ([301, 302, 303, 307, 308].includes(response.status)) {
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
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch (e) {
    return new Response('代理 YouTube 出错: ' + e.message, { status: 500 });
  }
}
