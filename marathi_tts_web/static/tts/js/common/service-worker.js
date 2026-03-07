// Service Worker for Marathi TTS
// This file runs in the Service Worker context — no access to window, document, or navigator.
const CACHE_NAME = 'marathi-tts-cache-v4';
const AUDIO_CACHE_NAME = 'marathi-tts-audio-cache-v2';
const processedRequests = new Set();

// Install event
self.addEventListener('install', event => {
    event.waitUntil(
        Promise.all([
            caches.open(CACHE_NAME).then(cache => {
                return cache.addAll([
                    '/marathi_tts/tts/',
                    '/static/tts/css/common/base.css',
                    '/static/tts/js/core/tts.js',
                    '/static/tts/js/core/image-processor.js',
                    '/static/tts/js/core/pdf-processor.js',
                    '/static/tts/js/core/tts-cache.js',
                    '/static/tts/js/core/request-batcher.js',
                    '/static/tts/js/core/tts-engine.js',
                    '/static/tts/js/common/jquery-3.6.0.min.js',
                    '/static/tts/js/common/bootstrap.min.js',
                    '/static/tts/js/common/jquery.fancybox.min.js',
                    '/static/tts/js/common/chart.js'
                ]);
            }),
            caches.open(AUDIO_CACHE_NAME)
        ])
    );
    self.skipWaiting();
});

// Activate event with improved cache cleanup
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME && name !== AUDIO_CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        })
    );
    return self.clients.claim();
});

// Fetch event with deduplication and specialized audio caching
self.addEventListener('fetch', event => {
    const requestUrl = event.request.url;
    
    // Deduplicate requests
    if (processedRequests.has(requestUrl)) {
        return;
    }
    
    processedRequests.add(requestUrl);
    setTimeout(() => processedRequests.delete(requestUrl), 1000);

    // Special handling for audio files
    if (requestUrl.includes('/media/tts/') && 
        (requestUrl.endsWith('.wav') || requestUrl.endsWith('.mp3'))) {
        event.respondWith(cacheAudioThenFetch(event.request));
        return;
    }

    // Standard handling for other requests
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                
                return fetch(event.request).then(response => {
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseToCache);
                    });

                    return response;
                });
            })
            .catch(error => {
                console.error('Fetch failed:', error);
                return new Response('Network error', { status: 503 });
            })
    );
});

// Specialized function for caching audio files
function cacheAudioThenFetch(request) {
    return caches.open(AUDIO_CACHE_NAME).then(cache => {
        return cache.match(request).then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;
            }
            
            return fetch(request).then(response => {
                if (!response || !response.ok) {
                    return response;
                }
                
                // Clone the response and store it in the cache
                const responseToCache = response.clone();
                cache.put(request, responseToCache);
                
                return response;
            });
        });
    });
}

// Add background sync for offline support
self.addEventListener('sync', event => {
    if (event.tag === 'tts-sync') {
        event.waitUntil(syncPendingRequests());
    }
});

// Function to sync pending requests
async function syncPendingRequests() {
    // Implementation for syncing pending TTS requests when online
    console.log('Syncing pending TTS requests');
    // This would be implemented to handle offline TTS requests
}