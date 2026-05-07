const CACHE_NAME = 'yu-corner-v2';

// 缓存的壳资源（保证离线也能打开框架）
const SHELL_FILES = [
  '/',
  '/index.html',
  '/manifest.json',
  // 如果需要缓存其他公共样式或脚本，可以加在这里
  // '/your-css-or-js.css',
];

// 安装时缓存壳
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

// 激活时清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// 请求策略：缓存优先（壳资源），网络优先（数据接口）
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 如果是 API 或数据文件（daily.json, stats.json 等），走网络优先
  if (url.pathname.startsWith('/data/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => response)
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 其他请求（包含页面）：缓存优先，网络更新
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((response) => {
        // 更新缓存
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) =>
            cache.put(event.request, clone)
          );
        }
        return response;
      });
      return cached || fetchPromise;
    })
  );
});
