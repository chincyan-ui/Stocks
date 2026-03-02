export async function onRequest(context) {
  const url = new URL(context.request.url);
  const myHost = url.host;
  const targetHost = 'cn.nytimes.com';
  
  // 1. 拦截对 NYT 资源域名的请求（处理图片和脚本加载）
  // 如果链接包含特定的 NYT 资源标识，强制拉取原站资源
  if (url.pathname.includes('static01.nyt.com')) {
    const resourceUrl = 'https:/' + url.pathname;
    return fetch(resourceUrl, { headers: { 'Referer': 'https://cn.nytimes.com/' } });
  }

  // 2. 构造目标 URL
  const targetUrl = new URL(context.request.url);
  targetUrl.host = targetHost;

  // 3. 构造请求头
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

    const contentType = response.headers.get('content-type') || '';
    let responseHeaders = new Headers(response.headers);

    // 4. 处理重定向
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      let location = response.headers.get('Location');
      if (location) {
        location = location.replace('https://' + targetHost, 'https://' + myHost)
                           .replace('https://www.nytimes.com', 'https://' + myHost);
        return Response.redirect(location, response.status);
      }
    }

    // 5. 针对 HTML 进行深度替换
    if (contentType.includes('text/html')) {
      let text = await response.text();
      
      // 替换所有发现的域名，防止点击跳转
      const modifiedText = text
        .split('https://cn.nytimes.com').join('https://' + myHost)
        .split('https://www.nytimes.com').join('https://' + myHost)
        .split('//cn.nytimes.com').join('//' + myHost)
        // 强制让页面中的脚本认为它就在原站运行
        .replace(/window\.location\.hostname/g, `"${targetHost}"`);

      // 移除安全限制头，否则浏览器会拒绝加载代理的脚本
      responseHeaders.delete('content-security-policy');
      responseHeaders.delete('content-security-policy-report-only');
      responseHeaders.set('Access-Control-Allow-Origin', '*');

      return new Response(modifiedText, {
        status: response.status,
        headers: responseHeaders
      });
    }

    // 6. 其他资源（图片、JS等）直接返回
    return response;

  } catch (e) {
    return new Response('代理出错: ' + e.message, { status: 500 });
  }
}
