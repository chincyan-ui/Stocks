export async function onRequest(context) {
  const url = new URL(context.request.url);
  const myHost = url.host; // 你的 pages.dev 域名
  const targetHost = 'www.bbc.com';
  
  // 1. 自动跳转到中文版首页
  if (url.pathname === '/' || url.pathname === '') {
    return Response.redirect(`https://${myHost}/zhongwen/simp`, 302);
  }

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

    // 2. 处理重定向 (Location Header 替换)
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      let location = response.headers.get('Location');
      if (location) {
        location = location.replace('https://' + targetHost, 'https://' + myHost);
        return Response.redirect(location, response.status);
      }
    }

    // 3. 核心修改：如果是 HTML 页面，替换里面的所有链接
    if (contentType.includes('text/html')) {
      let text = await response.text();
      // 把页面中所有的 www.bbc.com 替换为你的域名
      // 这样点击新闻链接时，依然会通过你的代理访问
      const modifiedText = text.replace(new RegExp('https://' + targetHost, 'g'), 'https://' + myHost)
                               .replace(new RegExp('//' + targetHost, 'g'), '//' + myHost);

      return new Response(modifiedText, {
        status: response.status,
        headers: response.headers
      });
    }

    // 4. 非 HTML 内容（图片、JS、CSS）直接返回
    return response;

  } catch (e) {
    return new Response('代理出错: ' + e.message, { status: 500 });
  }
}
