export async function onRequest(context) {
  const url = new URL(context.request.url);
  url.host = 'www.google.com';

  // 1. 创建新的请求头，模仿真实浏览器
  const newHeaders = new Headers(context.request.headers);
  newHeaders.set('Host', 'www.google.com');
  newHeaders.set('Referer', 'https://www.google.com/');
  newHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  const modifiedRequest = new Request(url.toString(), {
    method: context.request.method,
    headers: newHeaders,
    body: context.request.body,
    redirect: 'manual'
  });

  // 2. 发起请求
  try {
    const response = await fetch(modifiedRequest);
    
    // 3. 处理重定向，防止跳回原域名
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      const location = response.headers.get('Location');
      if (location) {
        const newLocation = new URL(location);
        newLocation.host = url.host; // 保持在代理域名下
        return Response.redirect(newLocation.href, response.status);
      }
    }

    return response;
  } catch (e) {
    return new Response('Proxy Error: ' + e.message, { status: 500 });
  }
}
