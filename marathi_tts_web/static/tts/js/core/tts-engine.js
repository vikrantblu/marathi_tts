import { preprocessMarathiText } from '../utils/text-correction.js';
import { EmotionHandler } from '../utils/emotions-processor.js';
import { GENERATE_AUDIO_URL, ANALYZE_EMOTION_URL, BASE_URL } from '../constants/api-endpoints.js';
export class TTSEngine {
    constructor() {
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        this.baseUrl = document.querySelector('meta[name="base-url"]')?.content || BASE_URL;
        this.initializeStatusElement();
        this.eventHandlers = new Map();
        this.currentAudio = null;
        this.pendingRequest = null;
        // Add a cache for emotion results
        this.emotionCache = new Map();
    }

    initializeStatusElement() {
        this.statusElement = document.getElementById('tts-status');
        if (!this.statusElement) {
            const container = document.querySelector('.tts-container');
            if (container) {
                this.statusElement = this.createStatusElement(container);
            } else {
                console.warn('TTS container not found, creating fallback status element');
                this.statusElement = this.createFallbackStatusElement();
            }
        }
    }

    createStatusElement(container) {
        const status = document.createElement('div');
        status.id = 'tts-status';
        status.className = 'tts-status hidden';
        container.appendChild(status);
        return status;
    }

    createFallbackStatusElement() {
        // Create a floating status element if container is not found
        const status = document.createElement('div');
        status.id = 'tts-status';
        status.className = 'tts-status floating hidden';
        document.body.appendChild(status);
        return status;
    }

    updateStatus(message, type = 'info') {
        if (!this.statusElement) {
            console.warn('Status element not available:', message);
            return;
        }
        this.statusElement.textContent = message;
        this.statusElement.className = `tts-status ${type}`;
        this.statusElement.classList.remove('hidden');
        this.emit('statusUpdate', { message, type });
    }

    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }

    emit(event, data) {
        const handlers = this.eventHandlers.get(event);
        if (handlers) {
            handlers.forEach(handler => handler(data));
        }
    }

    async generateSpeech(text, options = {}) {
        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('speed', options.speed || 1.0);
            formData.append('pitch', options.pitch || 0);
            formData.append('volume', options.volume || 0);
            formData.append('emotion_intensity', options.emotionIntensity || 0.8);

            const response = await fetch('/tts/generate/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result;

        } catch (error) {
            console.error('TTS Engine error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    // Add this helper method to identify words to emphasize
    shouldEmphasize(word) {
        // Words/patterns that should be emphasized in Marathi
        const emphasisPatterns = [
            /^(अत्यंत|अति|महा|परम|सर्व|अधि|स्व)/,  // Intensifiers and prefixes
            /^(महत्त्वाचे|विशेष|अनिवार्य|आवश्यक)/,  // Important adjectives
            /^[०-९]+$/,                            // Numbers
            /^(श्री|डॉ|कु|प्रा)/,                  // Honorifics
            /(तम|तर)$/,                           // Superlative suffixes
            /^(अखिल|सर्व|समस्त)/,                 // Universal quantifiers
            /^(अत्युत्तम|सर्वोत्तम|सर्वश्रेष्ठ)/,    // Excellence indicators
            /^(तात्काळ|त्वरित|लवकर)/              // Urgency indicators
        ];
        return emphasisPatterns.some(pattern => pattern.test(word));
    }


    async generateAudio(text, options = {}) {
        // Cancel any pending request
        if (this.pendingRequest) {
            this.pendingRequest.abort();
        }

        // Clear current audio
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }

        if (!text?.trim()) {
            this.updateStatus('No text provided', 'error');
            return { success: false, error: 'No text provided' };
        }

        this.updateStatus('Generating audio...', 'info');
        this.emit('generateStart', { text });

        try {
            // Process text for SSML if needed
            const processedText = options.useSSML !== false 
                ? preprocessMarathiText(text).text 
                : text;
            
            // Create FormData to send to the server
            const formData = new FormData();
            formData.append('text', processedText);
            formData.append('speed', options.speed || 1.0);
            formData.append('pitch', options.pitch || 1.0);
            formData.append('volume', options.volume || 1.0);
            formData.append('emotion_intensity', options.emotionIntensity || 0.8);
            
            if (options.voiceQuality) {
                formData.append('breathiness', options.voiceQuality.breathiness || 0.2);
                formData.append('richness', options.voiceQuality.richness || 1.0);
                formData.append('clarity', options.voiceQuality.clarity || 1.0);
            }
            
            if (options.emotion) {
                formData.append('emotion', options.emotion);
            }

            const controller = new AbortController();
            this.pendingRequest = controller;

            const response = await fetch(GENERATE_AUDIO_URL, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                signal: controller.signal
            });

            this.pendingRequest = null;

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // IMPORTANT: Update emotion display whenever we get a response
                if (data.emotion_data) {
                    this.updateEmotionDisplay(data.emotion_data);
                    window.emotionHandler.updateEmotionDisplay(data.emotion_data);
                }
                
                this.updateStatus('Audio generated successfully', 'success');
                this.emit('generateComplete', data);
                
                if (data.audio_url) {
                    const audio = new Audio(data.audio_url);
                    this.currentAudio = audio;
                    
                    audio.addEventListener('play', () => this.emit('audioPlay', { audio }));
                    audio.addEventListener('pause', () => this.emit('audioPause', { audio }));
                    audio.addEventListener('ended', () => {
                        this.updateStatus('Playback complete', 'info');
                        this.emit('audioEnd', { audio });
                    });
                    
                    if (options.autoplay) {
                        audio.play().catch(e => console.warn('Auto-play prevented:', e));
                    }
                }
            } else {
                this.updateStatus(`Error: ${data.error || 'Unknown error'}`, 'error');
                this.emit('generateError', { error: data.error });
            }
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Audio generation request canceled');
                return { success: false, canceled: true };
            }
            
            console.error('TTS Engine error:', error);
            this.updateStatus(`Error: ${error.message}`, 'error');
            this.emit('generateError', { error: error.message });
            
            return {
                success: false,
                error: error.message
            };
        }
    }

}

// Add this function to get CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Update your fetch calls
async function analyzeEmotion(text) {
    const response = await fetch(ANALYZE_EMOTION_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ text })
    });
    return response.json();
}

function handleTTSResponse(response) {
    if (response.success) {
        // Create audio player
        const audioPlayer = `
            <div class="audio-player">
                <a href="#audio-modal-${response.filename}" 
                   data-fancybox="audio-player" 
                   class="btn btn-primary">
                    <i class="fas fa-play"></i> Play Audio
                </a>
                
                <div id="audio-modal-${response.filename}" style="display:none;">
                    <audio controls autoplay>
                        <source src="${response.audio_url}" type="audio/wav">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>`;
            
        // Add to page and initialize Fancybox
        $('#audio-output').html(audioPlayer);
        $('[data-fancybox="audio-player"]').fancybox({
            toolbar: true,
            smallBtn: true,
            iframe: {
                preload: false
            }
        });
    } else {
        showError(response.error);
    }
}

// Add this before the EmotionHandler class

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add this before the EmotionHandler class
function getVoiceParams() {
    return {
        speed: document.getElementById('speedRange')?.value || 1.0,
        pitch: document.getElementById('pitchRange')?.value || 1.0,
        volume: document.getElementById('volumeRange')?.value || 1.0,
        voice_quality: {
            breathiness: document.getElementById('breathinessRange')?.value || 0.2,
            richness: document.getElementById('richnessRange')?.value || 1.2,
            clarity: document.getElementById('clarityRange')?.value || 1.1
        }
    };
}



// Add DOM ready handler at the end of the file
document.addEventListener('DOMContentLoaded', () => {
    // Get required elements
    const ttsInput = document.getElementById('tts-input');
    const emotionDisplay = document.getElementById('emotion-display');
    
    // Initialize TTS Engine and store globally
    const ttsEngine = new TTSEngine();
    window.ttsEngine = ttsEngine; // Make it globally available
    
    if (ttsInput) {
        // Add input listener with proper checks
        ttsInput.addEventListener('input', (e) => {
            const text = e.target.value;
            
            // Only analyze if we have text and emotion display element
            if (text && emotionDisplay) {
                ttsEngine.analyzeEmotions(text).then(emotionResult => {
                    ttsEngine.updateEmotionDisplay(emotionResult);
                    window.currentEmotion = emotionResult;
                }).catch(error => {
                    console.error('Error analyzing emotions:', error);
                });
            }
        });
    }

    // Initialize emotion handler only if needed elements exist
    if (document.getElementById('emotionIntensityRange')) {
        const emotionHandler = new EmotionHandler();
        window.emotionHandler = emotionHandler;
    }
});



// Also add this to your form submission handler 
$('#ttsForm').submit(function(e) {
    e.preventDefault();
    const text = $('#tts-input').val();
    console.log("Current emotion state:", window.currentEmotion);
    // Get the parameters for TTS
    
    // Get voice parameters from UI controls
    const voiceParams = getVoiceParams();
    
    // Get emotion data from the current emotion state or UI controls
    let emotionParams = {};
    if (window.currentEmotion) {
        emotionParams = {
            emotion: window.currentEmotion.dominant,
            emotionIntensity: window.currentEmotion.intensity || 0.8
        };
    } else if (window.emotionHandler) {
        const handlerParams = window.emotionHandler.getEmotionParams();
        emotionParams = {
            emotionIntensity: handlerParams.intensity
        };
    }
    
    // Combine all parameters
    const ttsParams = {
        ...voiceParams,
        ...emotionParams,
        useSSML: true,  // Enable SSML by default
        autoplay: true  // Auto-play the generated audio
    };
    
    // Show loading state
    $('#generate-btn').prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Generating...');
    
    // Call the TTS engine to generate audio
    window.ttsEngine.generateAudio(text, ttsParams)
        .then(response => {
            // Reset button state
            $('#generate-btn').prop('disabled', false).html('Generate Speech');
            
            // Handle response
            if (response.success) {
                // If we're not showing the audio player through the engine's events,
                // we can use the handleTTSResponse function
                if (!response.handled) {
                    handleTTSResponse(response);
                }
            } else if (!response.canceled) {
                // Show error if not just a cancellation
                const errorMessage = response.error || 'Failed to generate speech';
                $('#error-container').text(errorMessage).show();
                setTimeout(() => $('#error-container').fadeOut(), 5000);
            }
        })
        .catch(error => {
            // Reset button state and show error
            $('#generate-btn').prop('disabled', false).html('Generate Speech');
            $('#error-container').text('Error: ' + error.message).show();
            setTimeout(() => $('#error-container').fadeOut(), 5000);
        });
});