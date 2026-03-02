export async function onRequest(context) {
  const url = new URL(context.request.url);
  url.host = 'www.google.com';

  return fetch(url.toString(), context.request);
}