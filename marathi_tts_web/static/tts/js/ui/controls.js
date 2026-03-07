import { CONFIG } from '../utils/config.js';
import { WordSync } from '../utils/word-sync.js';
import { AudioController } from '../core/audio-controller.js';
import { PdfProcessor } from '../core/pdf-processor.js';
import { getNotyf } from '../utils/notifications.js';

export class UIControls {
    constructor(ttsEngine, notifications) {
        if (!ttsEngine || !notifications) {
            throw new Error('TTSEngine and notifications are required');
        }
        
        this.ttsEngine = ttsEngine;
        this.notifications = notifications;
        this.elements = this._initializeElements();
        this.isProcessing = false;
        this.boundHandleGenerate = this.handleGenerateClick.bind(this);
        
        // Initialize controllers
        this.audioController = new AudioController();
        this.wordSync = new WordSync();
        
        // Single initialization of event listeners
        this.initializeOnce();

        // Tab buttons
        this.textInputBtn = document.getElementById('textInputBtn');
        this.urlInputBtn = document.getElementById('urlInputBtn');
        this.imageInputBtn = document.getElementById('imageInputBtn');
        this.pdfInputBtn = document.getElementById('pdfInputBtn');
        
        // Content sections
        this.textInputSection = document.getElementById('textInputSection');
        this.urlInputSection = document.getElementById('urlInputSection');
        this.imageInputSection = document.getElementById('imageInputSection');
        this.pdfInputSection = document.getElementById('pdfInputSection');
        
        this.initializeTabControls();
        
        // Initialize sliders immediately
        this.setupSliders();
        console.log('Sliders initialized'); // Debug log
    }

    _initializeElements() {
        // These selectors are optional — they may not exist on every page variant
        const optionalSelectors = new Set(['voiceSelect']);
        const elements = {};
        for (const [key, selector] of Object.entries(CONFIG.ui.selectors)) {
            const element = document.querySelector(selector);
            if (!element && !optionalSelectors.has(key)) {
                console.warn(`Element not found: ${selector}`);
            }
            elements[key] = element;
        }
        return elements;
    }

    initializeOnce() {
        if (this._initialized) return;
        this._initialized = true;
        
        const { generateBtn } = this.elements;
        if (generateBtn) {
            // Remove existing listeners
            generateBtn.removeEventListener('click', this.boundHandleGenerate);
            // Add single listener
            generateBtn.addEventListener('click', this.boundHandleGenerate);
        }
    }

    initializeControls() {
        this.setupGenerateButton();
        this.setupAudioControls();
        this.setupSliders();
    }

    setupGenerateButton() {
        const { generateBtn, marathiText } = this.elements;
        
        if (generateBtn && marathiText) {
            // Remove any existing listeners first
            generateBtn.replaceWith(generateBtn.cloneNode(true));
            
            // Get the new button reference after cloning
            this.elements.generateBtn = document.querySelector(CONFIG.ui.selectors.generateBtn);
            
            // Add new listener WITHOUT the once:true option
            this.elements.generateBtn.addEventListener('click', async (e) => {
                // Prevent handling if already processing
                if (this.isProcessing) return;
                await this.handleGenerateClick(e);
            });
        } else {
            console.error('Required elements not found:', {
                generateBtn: !!generateBtn,
                marathiText: !!marathiText
            });
        }
    }

    getOptions() {
        return {
            voice: this.elements.voiceSelect?.value || 'google',
            speed: parseFloat(this.elements.speedRange?.value || 1.0),
            pitch: parseInt(this.elements.pitchRange?.value || 0),
            volume: parseInt(this.elements.volumeRange?.value || 0)
        };
    }

    async handleGenerateClick(event) {
        if (event) event.preventDefault();
        if (this.isProcessing) return;

        this.isProcessing = true;
        console.log("Generate clicked"); // Debug log

        try {
            const text = this.elements.marathiText?.value;
            
            if (!text?.trim()) {
                this.notifications.error('कृपया मजकूर प्रविष्ट करा');
                return;
            }

            this.showLoadingState(true);

            // Get and log current slider values
            const voiceParams = {
                speed: parseFloat(document.getElementById('speedRange').value),
                pitch: parseInt(document.getElementById('pitchRange').value),
                volume: parseInt(document.getElementById('volumeRange').value),
                emotion_intensity: parseFloat(document.getElementById('emotionIntensityRange').value),
                enable_emotions: true
            };

            console.log('Sending voice params:', voiceParams); // Debug log

            const requestData = {
                text: text,
                voice_params: voiceParams
            };

            console.log('Sending request:', requestData); // Debug log

            const response = await fetch('/tts/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: JSON.stringify(requestData)
            });

            console.log('Response received:', response.status); // Debug log
            const result = await response.json();
            console.log('Response data:', result); // Debug log

            if (result.success) {
                // Update the UI with emotion scoring
                if (result.emotion_score) {
                    document.getElementById('emotionScore').textContent = `Emotion Score: ${result.emotion_score}`;
                }
                this.notifications.success('ध्वनी तयार झाला!');
                await this.handleAudioPlayback(result.audio_url, text);
            } else {
                throw new Error(result.error || 'Failed to generate audio');
            }

        } catch (error) {
            console.error("Generate error:", error);
            this.notifications?.error('त्रुटी आली: ' + (error.message || 'अज्ञात त्रुटी'));
        } finally {
            // Always reset processing state and re-enable the button
            this.isProcessing = false;
            this.showLoadingState(false);
        }
    }

    async handleAudioPlayback(audioUrl, text) {
        try {
            if (!this.audioController || !this.wordSync) {
                console.error('Controllers not initialized');
                throw new Error('Audio controllers not initialized');
            }

            if (this.elements.audioPlayerModal) {
                // Close any existing fancybox instance and cleanup
                $.fancybox.close(true);
                
                // Ensure controllers exist before cleanup
                if (this.audioController && typeof this.audioController.cleanup === 'function') {
                    this.audioController.cleanup();
                }
                if (this.wordSync && typeof this.wordSync.cleanup === 'function') {
                    this.wordSync.cleanup();
                }

                let audioInitialized = false;

                $.fancybox.open({
                    src: this.elements.audioPlayerModal,
                    type: 'inline',
                    opts: {
                        touch: false,
                        hash: false,
                        baseClass: 'audio-player-modal fancybox-no-scroll',
                        afterShow: async () => {
                            if (!audioInitialized && this.elements.audioPlayer) {
                                audioInitialized = true;
                                
                                this.elements.audioPlayer.src = audioUrl;
                                await this.elements.audioPlayer.load();
                                
                                // Set up audio controller
                                this.audioController.setAudio(this.elements.audioPlayer);
                                
                                // Initialize word sync after audio is loaded
                                this.wordSync.init(text, this.elements.audioPlayer);
                            }
                        },
                        beforeClose: () => {
                            // Clean up audio and word sync with checks
                            if (this.audioController?.cleanup) {
                                this.audioController.cleanup();
                            }
                            if (this.wordSync?.cleanup) {
                                this.wordSync.cleanup();
                            }
                            audioInitialized = false;
                            return true;
                        },
                        afterClose: () => {
                            $('body').removeClass('fancybox-modal-open');
                            $('.fancybox-container').remove();
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Audio playback setup error:', error);
            throw error;
        }
    }

    showLoadingState(show) {
        if (this.elements.loadingSection) {
            this.elements.loadingSection.classList.toggle('hidden', !show);
        }
        if (this.elements.loadingMainText && show) {
            this.elements.loadingMainText.textContent = 'ध्वनी तयार होत आहे...';
        }
        
        // Disable/enable generate button
        if (this.elements.generateBtn) {
            this.elements.generateBtn.disabled = show;
        }
    }

    setupAudioControls() {
        if (!this.elements.audioPlayer) return;

        // Remove existing listeners
        const newAudioPlayer = this.elements.audioPlayer.cloneNode(true);
        this.elements.audioPlayer.replaceWith(newAudioPlayer);
        this.elements.audioPlayer = newAudioPlayer;

        if (this.elements.playPauseBtn) {
            this.elements.playPauseBtn.addEventListener('click', () => {
                if (this.elements.audioPlayer.paused) {
                    this.elements.audioPlayer.play();
                } else {
                    this.elements.audioPlayer.pause();
                }
            });
        }

        // Single timeupdate listener
        this.elements.audioPlayer.addEventListener('timeupdate', () => {
            if (this.elements.progressBar) {
                const progress = (this.elements.audioPlayer.currentTime / this.elements.audioPlayer.duration) * 100;
                this.elements.progressBar.value = progress;
            }
        });

        // Single progress bar listener
        if (this.elements.progressBar) {
            this.elements.progressBar.addEventListener('input', () => {
                const time = (this.elements.progressBar.value / 100) * this.elements.audioPlayer.duration;
                this.elements.audioPlayer.currentTime = time;
            });
        }
    }

    setupSliders() {
        const sliderConfigs = {
            speed: {
                range: document.getElementById('speedRange'),
                value: document.getElementById('speedValue'),
                initial: 1.0,
                format: (v) => v.toFixed(1) + 'x',
                param: 'speed'
            },
            pitch: {
                range: document.getElementById('pitchRange'),
                value: document.getElementById('pitchValue'),
                initial: 0,
                format: (v) => v.toString(),
                param: 'pitch'
            },
            volume: {
                range: document.getElementById('volumeRange'),
                value: document.getElementById('volumeValue'),
                initial: 0,
                format: (v) => v + ' dB',
                param: 'volume'
            },
            emotion: {
                range: document.getElementById('emotionIntensityRange'),
                value: document.getElementById('emotionIntensityValue'),
                initial: 0.8,
                format: (v) => v.toString(),
                param: 'emotionIntensity'
            }
        };

        // Store current values
        this.ttsParams = {
            speed: 1.0,
            pitch: 0,
            volume: 0,
            emotionIntensity: 0.8
        };

        Object.entries(sliderConfigs).forEach(([name, config]) => {
            const slider = config.range;
            const display = config.value;

            if (!slider || !display) return;

            // Set initial value
            slider.value = config.initial;
            display.textContent = config.format(config.initial);
            this.ttsParams[config.param] = config.initial;

            // Add input event listener
            slider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                display.textContent = config.format(value);
                this.ttsParams[config.param] = value;
                console.log(`Updated ${config.param} to:`, value); // Debug log

                // Apply real-time playback adjustments to audio element
                const audioPlayer = document.getElementById('audioPlayer')
                    || document.querySelector('.fancybox__container audio');
                if (audioPlayer) {
                    if (config.param === 'speed') {
                        audioPlayer.playbackRate = value;
                    } else if (config.param === 'volume') {
                        // Volume slider is in dB (-20 to +20), convert to 0-1 linear
                        const linearVol = Math.pow(10, value / 20);
                        audioPlayer.volume = Math.max(0, Math.min(1, linearVol));
                    }
                }
            });
        });
    }

    initializeTabControls() {
        // Text tab
        this.textInputBtn.addEventListener('click', () => {
            this.switchTab('text');
        });

        // URL tab
        this.urlInputBtn.addEventListener('click', () => {
            this.switchTab('url');
        });

        // Image tab
        this.imageInputBtn.addEventListener('click', () => {
            this.switchTab('image');
        });

        // PDF tab
        this.pdfInputBtn.addEventListener('click', () => {
            this.switchTab('pdf');
        });
    }

    switchTab(tabName) {
        // Remove active class from all buttons
        [this.textInputBtn, this.urlInputBtn, this.imageInputBtn, this.pdfInputBtn].forEach(btn => {
            btn.classList.remove('active');
        });

        // Hide all sections
        [this.textInputSection, this.urlInputSection, this.imageInputSection, this.pdfInputSection].forEach(section => {
            section.classList.add('hidden');
        });

        // Show selected section and activate button
        switch(tabName) {
            case 'text':
                this.textInputBtn.classList.add('active');
                this.textInputSection.classList.remove('hidden');
                break;
            case 'url':
                this.urlInputBtn.classList.add('active');
                this.urlInputSection.classList.remove('hidden');
                break;
            case 'image':
                this.imageInputBtn.classList.add('active');
                this.imageInputSection.classList.remove('hidden');
                break;
            case 'pdf':
                this.pdfInputBtn.classList.add('active');
                this.pdfInputSection.classList.remove('hidden');
                break;
        }
    }
}

// Tab switching functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create necessary utilities
    const loadingManager = {
        showLoading: showLoading,
        hideLoading: hideLoading
    };
    
    const notyfInstance = getNotyf();
    
    // Initialize processors
    const pdfProcessor = new PdfProcessor(loadingManager, notyfInstance);
    
    // Get all tab buttons
    const textInputBtn = document.getElementById('textInputBtn');
    const urlInputBtn = document.getElementById('urlInputBtn');
    const imageInputBtn = document.getElementById('imageInputBtn');
    const pdfInputBtn = document.getElementById('pdfInputBtn');
    
    // Get all section containers
    const textInputSection = document.getElementById('textInputSection');
    const urlInputSection = document.getElementById('urlInputSection');
    const imageInputSection = document.getElementById('imageInputSection');
    const pdfInputSection = document.getElementById('pdfInputSection');
    
    // Function to switch tabs
    function switchTab(activeBtn, activeSection) {
        // Reset all buttons and sections
        [textInputBtn, urlInputBtn, imageInputBtn, pdfInputBtn].forEach(btn => {
            btn.classList.remove('active');
        });
        
        [textInputSection, urlInputSection, imageInputSection, pdfInputSection].forEach(section => {
            section.classList.remove('active');
            section.classList.add('hidden');
        });
        
        // Activate selected button and section
        activeBtn.classList.add('active');
        activeSection.classList.remove('hidden');
        activeSection.classList.add('active');
    }
    
    // Add event listeners for tab buttons
    textInputBtn.addEventListener('click', () => switchTab(textInputBtn, textInputSection));
    urlInputBtn.addEventListener('click', () => switchTab(urlInputBtn, urlInputSection));
    imageInputBtn.addEventListener('click', () => switchTab(imageInputBtn, imageInputSection));
    pdfInputBtn.addEventListener('click', () => switchTab(pdfInputBtn, pdfInputSection));
});

// Helper functions for notifications and loading
function showNotification(message, type) {
    const notyf = getNotyf();
    
    if (type === 'error') {
        notyf.error(message);
    } else {
        notyf.success(message);
    }
}

// Replace the showLoading and hideLoading functions with these fixed versions

function showLoading(mainText, subText) {
    const loadingSection = document.getElementById('loadingSection');
    if (!loadingSection) {
        console.error('Loading section not found');
        return;
    }
    
    const loadingMainText = document.getElementById('loadingMainText');
    const loadingSubText = document.getElementById('loadingSubText');
    
    // If elements exist, update them, otherwise just show the loading overlay
    if (loadingMainText) loadingMainText.textContent = mainText || 'प्रक्रिया चालू आहे...';
    if (loadingSubText) loadingSubText.textContent = subText || 'कृपया थांबा';
    
    loadingSection.classList.remove('hidden');
}

function hideLoading() {
    const loadingSection = document.getElementById('loadingSection');
    if (loadingSection) {
        loadingSection.classList.add('hidden');
    }
}

// Word count functionality
function updateWordCount() {
    const text = document.getElementById('marathiText').value;
    
    // Handle empty text
    if (!text.trim()) {
        document.getElementById('wordCount').textContent = '0';
        return;
    }

    // Remove extra spaces and normalize whitespace
    const normalizedText = text.replace(/\s+/g, ' ').trim();

    // Split by Marathi word boundaries:
    // - whitespace
    // - punctuation marks (।॥,!?)
    // - Devanagari numbers
    // - Special characters
    const words = normalizedText
        .split(/[\s।॥,!?]+|(?=[०-९])|(?<=[०-९])|(?=[\/\(\)\[\]\{\}""''-])|(?<=[\/\(\)\[\]\{\}""''-])/)
        .filter(word => {
            // Filter out empty strings and standalone punctuation
            return word.trim() && !/^[।॥,!?०-९\/\(\)\[\]\{\}""''-]+$/.test(word);
        });

    // Update the word count display
    document.getElementById('wordCount').textContent = words.length;
    
    // Optional: Add character count
    const charCount = text.replace(/\s/g, '').length;
    
    // If you want to show both word and character count
    document.getElementById('wordCount').textContent = 
       `एकूण अक्षरे: ${words.length + charCount}`;
}

// Add event listener when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const textArea = document.getElementById('marathiText');
    textArea.addEventListener('input', updateWordCount);
    // Initial count
    updateWordCount();
});