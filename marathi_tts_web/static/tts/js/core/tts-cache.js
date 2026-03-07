/**
 * TTS Cache manager to reduce API calls
 */
export class TTSCache {
    constructor() {
        this.cache = new Map();
        this.enabled = true;
        this.maxSize = 50; // Maximum number of cached items
        
        // Try to use persistent storage when available
        this.initStorage();
    }

    initStorage() {
        try {
            // Check if localStorage is available
            if (window.localStorage) {
                // Load cached items from localStorage
                const storedCache = localStorage.getItem('tts_cache');
                if (storedCache) {
                    const parsed = JSON.parse(storedCache);
                    Object.entries(parsed).forEach(([key, value]) => {
                        this.cache.set(key, value);
                    });
                }
            }
        } catch (e) {
            console.warn('Could not initialize persistent cache:', e);
        }
    }

    /**
     * Get cached TTS audio for text
     * @param {string} text - The text to look up
     * @param {Object} params - TTS parameters
     * @returns {string|null} - Audio URL if found, null otherwise
     */
    get(text, params = {}) {
        if (!this.enabled || !text) return null;
        
        // Create a cache key from text and relevant params
        const key = this.createCacheKey(text, params);
        return this.cache.get(key) || null;
    }

    /**
     * Store TTS audio in cache
     * @param {string} text - The source text
     * @param {string} audioUrl - Audio URL to cache
     * @param {Object} params - TTS parameters 
     */
    set(text, audioUrl, params = {}) {
        if (!this.enabled || !text || !audioUrl) return;
        
        // Manage cache size - remove oldest entries if needed
        if (this.cache.size >= this.maxSize) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }
        
        // Create cache key
        const key = this.createCacheKey(text, params);
        this.cache.set(key, audioUrl);
        
        // Try to persist to localStorage
        this.persistCache();
    }

    /**
     * Create a deterministic cache key for text and params
     */
    createCacheKey(text, params) {
        // Extract only the parameters that affect audio output
        const relevantParams = {
            voice: params.voice || 'default',
            pitch: params.pitch || 0,
            speed: params.speed || 1,
            emotion: params.emotion || 'neutral'
        };
        
        // Create deterministic string for the parameters
        const paramsStr = JSON.stringify(relevantParams, Object.keys(relevantParams).sort());
        
        // Use only first 100 chars of text for the key to avoid very long keys
        const textPart = text.slice(0, 100);
        
        return `${textPart}|${paramsStr}`;
    }

    /**
     * Persist cache to localStorage if available
     */
    persistCache() {
        try {
            if (window.localStorage) {
                const cacheObj = {};
                this.cache.forEach((value, key) => {
                    cacheObj[key] = value;
                });
                localStorage.setItem('tts_cache', JSON.stringify(cacheObj));
            }
        } catch (e) {
            console.warn('Could not persist cache:', e);
        }
    }

    /**
     * Clear the cache
     */
    clear() {
        this.cache.clear();
        try {
            if (window.localStorage) {
                localStorage.removeItem('tts_cache');
            }
        } catch (e) {
            console.warn('Could not clear persistent cache:', e);
        }
    }
}
