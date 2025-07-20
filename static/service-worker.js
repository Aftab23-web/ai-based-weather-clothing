self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open('outfit-cache').then(function(cache) {
      return cache.addAll([
        '/',
        '/static/css/styles.css',
        '/static/icons/icon-192.png',
        '/static/icons/icon-512.png'
        // Add more assets if needed
      ]);
    })
  );
});

self.addEventListener('fetch', function(e) {
  e.respondWith(
    caches.match(e.request).then(function(response) {
      return response || fetch(e.request);
    })
  );
});
