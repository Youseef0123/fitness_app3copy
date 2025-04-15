// Service Worker for AI Fitness Trainer App
const CACHE_NAME = 'ai-fitness-trainer-v1';

// Files to cache
const STATIC_CACHE_URLS = [
  '/',
  '/static/css/main.css',
  '/static/css/mobile.css',
  '/static/js/main.js',
  '/static/js/webrtc.js',
  '/static/img/placeholder.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js',
  'https://cdn.socket.io/4.6.1/socket.io.min.js'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing Service Worker...');
  
  // Skip waiting so the new service worker activates immediately
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching static files');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .catch(error => {
        console.error('[Service Worker] Cache installation error:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating Service Worker...');
  
  // Claim clients so the service worker is in control immediately
  event.waitUntil(self.clients.claim());
  
  // Remove old caches
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  // Skip WebSocket connections
  if (event.request.url.includes('/socket.io/')) {
    return;
  }
  
  // Skip video feed URLs (don't cache them)
  if (event.request.url.includes('/video_feed/')) {
    return;
  }
  
  // Skip API requests
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  // Handle static assets with cache-first strategy
  if (isStaticAsset(event.request.url)) {
    event.respondWith(
      caches.match(event.request)
        .then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          
          // Network request if not in cache
          return fetch(event.request)
            .then(response => {
              // Clone the response to store in cache
              const responseToCache = response.clone();
              
              // Open cache and save the response
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseToCache);
                });
                
              return response;
            })
            .catch(error => {
              console.error('[Service Worker] Fetch error:', error);
              
              // Return a fallback page for HTML requests
              if (event.request.headers.get('accept').includes('text/html')) {
                return caches.match('/offline.html');
              }
              
              return new Response('Network error', { 
                status: 408, 
                headers: { 'Content-Type': 'text/plain' } 
              });
            });
        })
    );
  } else {
    // For non-static assets, use network-first strategy
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match(event.request);
        })
    );
  }
});

// Helper function to check if a URL is for a static asset
function isStaticAsset(url) {
  const staticExtensions = [
    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', 
    '.svg', '.ico', '.woff', '.woff2', '.ttf'
  ];
  
  return staticExtensions.some(ext => url.endsWith(ext)) ||
         STATIC_CACHE_URLS.includes(url);
}

// Handle messages from the main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});