export async function onRequest(context) {
  const url = new URL(context.request.url);
  const myHost = url.host; // 你的 pages.dev 域名
  const targetHost = 'cn.nytimes.com'; // 纽约时报中文网目标域名
  
  // 1. 修改请求目标
  url.host = targetHost;

  const newHeaders = new Headers(context.request.headers);
  newHeaders.set('Host', targetHost);
  newHeaders.set('Referer', `https://${targetHost}/`);
  newHeaders.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36');

  const modifiedRequest = new Request(url.toString(), {
    method: context.request.method,
    headers: newHeaders,
    redirect: 'manual' 
  });

  try {
    const response = await fetch(modifiedRequest);
    const contentType = response.headers.get('content-type') || '';
    const responseHeaders = new Headers(response.headers);

    // 2. 处理重定向 (防止跳回原站)
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      let location = response.headers.get('Location');
      if (location) {
        // 将重定向目标中的原域名替换为你的代理域名
        location = location.replace('https://' + targetHost, 'https://' + myHost);
        return Response.redirect(location, response.status);
      }
    }

    // 3. 核心修改：如果是网页内容，动态替换所有链接
    if (contentType.includes('text/html')) {
      let text = await response.text();
      
      // 替换页面中所有的原域名链接，确保点击后依然走你的代理
      const modifiedText = text
        .split('https://' + targetHost).join('https://' + myHost)
        .split('//' + targetHost).join('//' + myHost);

      // 移除安全策略限制，防止脚本报错
      responseHeaders.delete('content-security-policy');
      responseHeaders.delete('content-security-policy-report-only');

      return new Response(modifiedText, {
        status: response.status,
        headers: responseHeaders
      });
    }

    // 4. 图片、CSS、JS 等资源直接返回
    return response;

  } catch (e) {
    return new Response('代理纽约时报出错: ' + e.message, { status: 500 });
  }
}
