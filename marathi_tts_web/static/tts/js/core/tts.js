import { TTSEngine } from './tts-engine.js';
import { UIControls } from '../ui/controls.js';
import { CONFIG } from '../utils/config.js';
import { TextProcessor } from './text-processor.js';
import { AudioController } from './audio-controller.js';
import { WordSync } from '../utils/word-sync.js';
import { ImageProcessor } from './image-processor.js';
import { Logger } from '../utils/logger.js';
import { LoadingManager } from '../ui/loading-manager.js';
import { AudioQueue } from '../utils/audio-queue.js';
import { PdfProcessor } from './pdf-processor.js';
import { TextCorrection } from '../utils/text-correction.js';
import { fix_content_structure } from '../core/text-processor.js';
import { GENERATE_AUDIO_URL } from '../constants/api-endpoints.js';
import { getNotyf } from '../utils/notifications.js';

window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

function is_valid_text(text) {
    // Example validation: Check if text is non-empty and contains valid characters
    const validPattern = /^[\u0900-\u097F\s.,!?।॥]*$/; // Example: Devanagari script with punctuation
    return validPattern.test(text);
}

export class MarathiTTS {
    constructor() {
        this.logger = new Logger('MarathiTTS');
        this._instanceId = Math.random().toString(36).substr(2, 9);
        
        // Initialize notifications first
        this.notifications = {
            error: (msg) => {
                if (this.notyf) {
                    this.notyf.error(msg);
                } else {
                    console.error(msg);
                }
            },
            success: (msg) => {
                if (this.notyf) {
                    this.notyf.success(msg);
                } else {
                    console.log(msg);
                }
            }
        };
        
        this.initializeDependencies();

        // Update API endpoint to match Django URL pattern
        this.apiEndpoint = GENERATE_AUDIO_URL;
        // Use the same protocol as the current page
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            this.apiEndpoint = window.location.protocol + '//' + window.location.host + this.apiEndpoint;
        }
    }

    initializeDependencies() {
        this.logger.debug('Initializing dependencies...');
        try {
            // Initialize core services first
            this.loadingManager = new LoadingManager();
            
            // Use shared Notyf singleton
            this.notyf = getNotyf();

            // Initialize processors - use try/catch for each to prevent initialization failures
            try {
                this.ttsEngine = new TTSEngine(this.loadingManager);
                window.ttsEngine = this.ttsEngine; // Make it globally accessible to prevent undefined errors
            } catch (e) {
                this.logger.error('Failed to initialize TTSEngine', e);
            }

            try {
                this.textProcessor = new TextProcessor();
            } catch (e) {
                this.logger.error('Failed to initialize TextProcessor', e);
            }
            
            try {
                this.imageProcessor = new ImageProcessor(this.loadingManager, this.notyf);
            } catch (e) {
                this.logger.error('Failed to initialize ImageProcessor', e);
            }
            
            try {
                this.pdfProcessor = new PdfProcessor(this.loadingManager, this.notyf);
            } catch (e) {
                this.logger.error('Failed to initialize PdfProcessor', e);
            }
            
            try {
                this.audioController = new AudioController();
            } catch (e) {
                this.logger.error('Failed to initialize AudioController', e);
            }
            
            try {
                this.wordSync = new WordSync();
            } catch (e) {
                this.logger.error('Failed to initialize WordSync', e);
            }

            try {
                this.textCorrection = new TextCorrection(); // Initialize TextCorrection
            } catch (e) {
                this.logger.error('Failed to initialize TextCorrection', e);
            }
            
            // Initialize UI controls last
            try {
                this.uiControls = new UIControls(this.ttsEngine, this.notyf);
            } catch (e) {
                this.logger.error('Failed to initialize UIControls', e);
            }
            
            // Define voiceParams globally to avoid reference errors
            window.voiceParams = {
                speed: 1.0,
                pitch: 0,
                volume: 0,
                emotion_intensity: 0.8,
                enable_emotions: true
            };
            
            this.logger.info('All dependencies initialized successfully');
        } catch (error) {
            this.logger.error('Failed to initialize dependencies', error);
            throw error;
        }
    }

    initialize() {
        try {
            this.initializeUI();
            this.setupEventListeners();
            console.log('MarathiTTS initialized');
        } catch (error) {
            console.error('Initialization error:', error);
        }
    }

    initializeUI() {
        this.logger.group('Initializing UI Elements');
        try {
            console.log(`[DEBUG] ${this._instanceId} - initializeUI called`);
            this.ui = {
                // Existing UI elements
                urlInput: document.getElementById('websiteUrl'),
                textArea: document.getElementById('marathiText'),
                fetchButton: document.getElementById('fetchTextBtn'),
                loadingSection: document.getElementById('loadingSection'),
                
                // Tab buttons
                textInputBtn: document.getElementById('textInputBtn'),
                urlInputBtn: document.getElementById('urlInputBtn'),
                imageInputBtn: document.getElementById('imageInputBtn'),
                pdfInputBtn: document.getElementById('pdfInputBtn'),
                
                // Tab sections
                textInputSection: document.getElementById('textInputSection'),
                urlInputSection: document.getElementById('urlInputSection'),
                imageInputSection: document.getElementById('imageInputSection'),
                pdfInputSection: document.getElementById('pdfInputSection'),
                
                // PDF elements
                pdfUpload: document.getElementById('pdfUpload'),
                pdfPreview: document.getElementById('pdfPreview'),
                extractPdfTextBtn: document.getElementById('extractPdfTextBtn'),
                
                // Existing audio elements
                generateBtn: document.getElementById('generateBtn'),
                listenAgainBtn: document.getElementById('listenAgainBtn'),
                audioPlayer: document.getElementById('audioPlayer'),
                audioSource: document.getElementById('audioSource'),
                audioPlayerModal: document.getElementById('audioPlayerModal'),
                loadingMainText: document.getElementById('loadingMainText'),
                loadingSubText: document.getElementById('loadingSubText'),
                progressBar: document.getElementById('progressBar')
            };

            // Log UI elements
            Object.entries(this.ui).forEach(([key, element]) => {
                this.logger.debug(`UI Element '${key}': ${element ? 'Found' : 'Missing'}`);
            });

            // Validate UI elements
            const missingElements = Object.entries(this.ui)
                .filter(([key, element]) => !element)
                .map(([key]) => key);

            if (missingElements.length > 0) {
                throw new Error(`Missing UI elements: ${missingElements.join(', ')}`);
            }
        } catch (error) {
            this.logger.error('Failed to initialize UI', error);
            throw error;
        } finally {
            this.logger.groupEnd();
        }
    }

    setupEventListeners() {
        console.log(`[DEBUG] ${this._instanceId} - setupEventListeners called`);
        
        // Remove duplicate fetch button handlers
        if (this.ui.fetchButton) {
            // Clone and replace to remove all existing listeners
            const oldButton = this.ui.fetchButton;
            const newButton = oldButton.cloneNode(true);
            oldButton.parentNode.replaceChild(newButton, oldButton);
            this.ui.fetchButton = newButton;
            
            // Add single click handler
            this.ui.fetchButton.addEventListener('click', async (e) => {
                e.preventDefault();
                
                if (this.isFetching) {
                    console.log('Fetch already in progress');
                    return;
                }

                this.isFetching = true;
                console.log(`[DEBUG] ${this._instanceId} - Starting fetch operation`);
                
                try {
                    await this.handleUrlFetch();
                } finally {
                    console.log(`[DEBUG] ${this._instanceId} - Fetch operation completed`);
                    this.isFetching = false;
                }
            });
        }

        // Text area paste handler - apply basic text cleanup on paste
        if (this.ui.textArea) {
            this.ui.textArea.onpaste = () => {
                setTimeout(() => {
                    const text = this.ui.textArea.value;
                    if (text) {
                        try {
                            const cleaned = fix_content_structure(text);
                            if (cleaned && is_valid_text(cleaned)) {
                                this.ui.textArea.value = cleaned;
                            }
                        } catch (e) {
                            this.logger.error('Error cleaning pasted text:', e);
                        }
                    }
                }, 0);
            };
        }

        // Tab switching handlers
        if (this.ui.textInputBtn) {
            this.ui.textInputBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchToTextTab();
            });
        }
        
        if (this.ui.urlInputBtn) {
            this.ui.urlInputBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchToUrlTab();
            });
        }

        if (this.ui.imageInputBtn) {
            this.ui.imageInputBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchToImageTab();
            });
        }
        
        // Add handler for PDF tab
        if (this.ui.pdfInputBtn) {
            this.ui.pdfInputBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchToPdfTab();
            });
        }

        // URL fetch handler - Check for duplicate listeners
        if (this.ui.fetchButton) {
            // Remove any existing listeners first
            this.ui.fetchButton.replaceWith(this.ui.fetchButton.cloneNode(true));
            this.ui.fetchButton = document.getElementById('fetchTextBtn');
            
            // Add single event listener
            this.ui.fetchButton.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation(); // Prevent event bubbling
                await this.handleUrlFetch();
            });
        }

        // Add enhanced keyboard support to textarea
        if (this.ui.textArea) {
            this.ui.textArea.addEventListener('keydown', (e) => {
                // Handle Ctrl+A (Select All)
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
                    e.preventDefault();
                    e.target.select();
                    return;
                }

                // Only handle Tab key, let all other shortcuts work normally
                if (e.key === 'Tab') {
                    e.preventDefault();
                    const start = e.target.selectionStart;
                    const end = e.target.selectionEnd;
                    
                    e.target.value = e.target.value.substring(0, start) + 
                                   '\t' + 
                                   e.target.value.substring(end);
                    
                    e.target.selectionStart = e.target.selectionEnd = start + 1;
                }
            });

            // Handle paste events - apply basic text cleanup
            this.ui.textArea.addEventListener('paste', (e) => {
                setTimeout(() => {
                    const text = this.ui.textArea.value;
                    if (text) {
                        try {
                            const cleaned = fix_content_structure(text);
                            if (cleaned && is_valid_text(cleaned)) {
                                this.ui.textArea.value = cleaned;
                            }
                        } catch (err) {
                            console.error('Error cleaning pasted text:', err);
                        }
                    }
                }, 0);
            });

            // Auto-resize
            this.ui.textArea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight + 2) + 'px';
            });
        }

        // CLEAN UP GENERATE BUTTON - REMOVE ALL DUPLICATES
        // This is the only generate button handler we need - all others should be removed
        if (this.ui.generateBtn) {
            console.log('Setting up generate button handler');
            // Remove any existing listeners completely
            const oldBtn = this.ui.generateBtn;
            const newBtn = oldBtn.cloneNode(true);
            oldBtn.parentNode.replaceChild(newBtn, oldBtn);
            this.ui.generateBtn = newBtn;

            // Add a single, properly managed event listener
            this.ui.generateBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('Generate button clicked');
                
                // Prevent multiple submissions
                if (this.isProcessing) {
                    console.log('Already processing, ignoring click');
                    return;
                }
                
                // Get and validate text
                const text = document.getElementById('marathiText').value;
                if (!text || !text.trim()) {
                    this.notifications?.error('कृपया मजकूर टाका');
                    return;
                }
                
                // Set processing flag
                this.isProcessing = true;
                this.ui.generateBtn.classList.add('processing');
                
                try {
                    // Check text length and warn if very large
                    if (text.length > 10000) {
                        console.log(`Processing large text: ${text.length} characters`);
                        this.showLoading('मोठा मजकूर प्रक्रिया करत आहे...', `${text.length} अक्षरे. थोडा वेळ लागू शकतो.`);
                    } else {
                        this.showLoading('तुमच्या मजकुराचे ध्वनी रुपांतर तयार होत आहे...', 'कृपया थांबा');
                    }
                    
                    console.log('Sending TTS request...');
                    const response = await this.generateTTS(text);
                    console.log('TTS response received:', response);
                    
                    if (response.success && response.audio_url) {
                        await this.handleTTSResponse(response.audio_url);
                    } else {
                        throw new Error(response.error || 'TTS generation failed without specific error');
                    }
                } catch (error) {
                    console.error('TTS generation error:', error);
                    this.notifications?.error('त्रुटी आली: ' + (error.message || 'अज्ञात त्रुटी'));
                } finally {
                    // Always reset processing state
                    console.log('Resetting processing state');
                    this.isProcessing = false;
                    this.ui.generateBtn.classList.remove('processing');
                    this.hideLoading();
                }
            });
        }

        // Listen button click handler
        if (this.ui.listenAgainBtn) {
            // Remove existing listeners
            const oldBtn = this.ui.listenAgainBtn;
            const newBtn = oldBtn.cloneNode(true);
            oldBtn.parentNode.replaceChild(newBtn, oldBtn);
            this.ui.listenAgainBtn = newBtn;

            this.ui.listenAgainBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // Show Fancybox modal
                Fancybox.show([{
                    src: '#audioPlayerModal',
                    type: 'inline',
                    touch: false,
                    autoFocus: false,
                    dragToClose: false,
                    closeButton: true,
                    on: {
                        reveal: () => {
                            // Reset audio and word sync
                            if (this.ui.audioPlayer) {
                                this.ui.audioPlayer.currentTime = 0;
                                // Apply current slider values to audio element
                                const speedSlider = document.getElementById('speedRange');
                                const volumeSlider = document.getElementById('volumeRange');
                                if (speedSlider) {
                                    this.ui.audioPlayer.playbackRate = parseFloat(speedSlider.value) || 1.0;
                                }
                                if (volumeSlider) {
                                    const dbVal = parseFloat(volumeSlider.value) || 0;
                                    this.ui.audioPlayer.volume = Math.max(0, Math.min(1, Math.pow(10, dbVal / 20)));
                                }
                            }
                            const currentText = document.getElementById('marathiText').value;
                            if (currentText) {
                                this.wordSync.init(currentText, this.ui.audioPlayer, 'syncText', {
                                    enableEmphasis: true,
                                    enablePauses: true
                                });
                            }
                        },
                        destroy: () => {
                            this.wordSync.cleanup();
                            if (this.ui.audioPlayer) {
                                this.ui.audioPlayer.pause();
                            }
                        }
                    }
                }]);
            });
        }
    }

    processMarathiText(text) {
        if (!text) return '';

        // Step 1: Protect time formats and abbreviations
        text = text
            .replace(/([०-९\d]+)\s*\.\s*([०-९\d]+)/g, '$1__TIME_DOT__$2')
            .replace(/([प-ह])\.([प-ह])\./g, '$1__DOT__$2__DOT__');

        // Step 2: Process paragraphs
        let paragraphs = text.split(/\n{2,}/).filter(p => p.trim());
        
        paragraphs = paragraphs.map(paragraph => {
            // Clean extra whitespace
            paragraph = paragraph.replace(/\s+/g, ' ').trim();
            
            // Handle existing punctuation without adding new ones
            paragraph = paragraph
                // Keep original sentence endings
                .replace(/([.!?।॥])\s*/g, '$1 ')
                // Fix spacing around commas
                .replace(/\s*,\s*/g, ', ')
                // Remove any automatic danda additions
                .replace(/\s*।\s*(?=\S)/g, ' ');
            
            return paragraph.trim();
        });

        // Step 3: Join paragraphs
        text = paragraphs.join('\n\n');
        
        // Step 4: Restore protected patterns
        text = text
            .replace(/__TIME_DOT__/g, '.')
            .replace(/__DOT__/g, '.');

        // Step 5: Final cleanup
        return text
            .replace(/\n{3,}/g, '\n\n')
            .replace(/[ \t]+$/gm, '')
            .replace(/^[ \t]+/gm, '')
            .trim();
    }

    async handleFetchContent() {
        console.log('Fetch content handler called at:', new Date().toISOString());
        let url = this.ui.urlInput?.value?.trim();
        
        if (!url) {
            this.notifications.error('कृपया वेबसाइट लिंक टाका');
            return;
        }

        const requestUrl = '/marathi_tts/tts/fetch-website-content/';
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                credentials: 'same-origin',  // Add this line
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ 
                    url: url.startsWith('http') ? url : `https://${url}`
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'मजकूर मिळवण्यात त्रुटी आली');
            }

            if (data.content && this.ui.textArea) {
                let cleanContent;
                try {
                    cleanContent = fix_content_structure(data.content);
                } catch (e) {
                    this.logger.error(`Error in fixing content structure: ${e.message}`);
                    this.logger.debug(e.stack); // Log the full stack trace for debugging
                    cleanContent = data.content; // Fallback to original text
                }
                this.ui.textArea.value = cleanContent;
                this.switchToTextTab();
                this.notifications.success('मजकूर यशस्वीरित्या मिळवला');
            }

        } catch (error) {
            console.error(`[DEBUG] ${this._instanceId} - Fetch error:`, error);
            throw error;
        }
    }

    async handleUrlFetch() {
        try {
            const url = this.ui.urlInput?.value?.trim();
            if (!url) {
                this.notifications.error('कृपया वैध URL टाका');
                return;
            }

            this.setLoading(true);
            await this.handleFetchContent();

        } catch (error) {
            console.error('URL fetch error:', error);
            this.notifications.error('URL वरून मजकूर मिळवण्यात त्रुटी आली');
        } finally {
            this.setLoading(false);
        }
    }

    getCsrfToken() {
        // Try to get token from cookie first
        const name = 'csrftoken=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookieArray = decodedCookie.split(';');
        
        for (let cookie of cookieArray) {
            cookie = cookie.trim();
            if (cookie.indexOf(name) === 0) {
                return cookie.substring(name.length);
            }
        }

        // Fallback to getting token from hidden input field
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenElement) {
            return tokenElement.value;
        }

        // Log error if no token found
        console.error('CSRF token not found');
        throw new Error('CSRF token not found');
    }

    async generateTTS(text, options = {}) {
        try {
            const csrfToken = this.getCsrfToken();
            
            console.log('Making TTS request with CSRF token:', csrfToken ? 'Token found' : 'No token');
            
            const start_time = performance.now();
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    text: text,
                    voice: this.currentVoice || 'default',
                    pitch: this.pitch || 0,
                    speed: this.speed || 1,
                    volume: this.volume || 1,
                    language: document.getElementById('languageSelect')?.value || 'mr',
                    engine: document.getElementById('ttsEngineSelect')?.value || 'auto',
                    gender: document.getElementById('genderSelect')?.value || 'female',
                    verse_mode: document.getElementById('verseModeCheckbox')?.checked || false,
                    emotion_intensity: options.emotion_intensity || 0.8,
                    enable_emotions: options.enable_emotions || true
                }),
                credentials: 'include'
            });

            const duration = performance.now() - start_time;
            this.logger.info(`API call completed in ${(duration / 1000).toFixed(2)} seconds`);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            return await response.json();
            
        } catch (error) {
            console.error('TTS generation error:', error);
            throw error;
        }
    }

    showLoading(mainText, subText = '') {
        if (this.ui.loadingSection) {
            this.ui.loadingSection.classList.remove('hidden');
            if (this.ui.loadingMainText) {
                this.ui.loadingMainText.textContent = mainText;
            }
            if (this.ui.loadingSubText) {
                this.ui.loadingSubText.textContent = subText;
            }
            if (this.ui.progressBar) {
                this.ui.progressBar.style.width = '0%';
                this.startProgressAnimation();
            }
        }
    }

    hideLoading() {
        if (this.ui.loadingSection) {
            this.ui.loadingSection.classList.add('hidden');
            if (this.ui.progressBar) {
                this.ui.progressBar.style.width = '0%';
            }
        }
    }

    startProgressAnimation() {
        let progress = 0;
        const interval = setInterval(() => {
            if (progress >= 90) {
                clearInterval(interval);
                return;
            }
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;
            if (this.ui.progressBar) {
                this.ui.progressBar.style.width = `${progress}%`;
            }
        }, 500);
    }

    async handleTTSResponse(audioUrl) {
        try {
            if (this.ui.audioPlayer && this.ui.audioSource) {
                // Stop any current playback
                this.ui.audioPlayer.pause();
                this.ui.audioPlayer.currentTime = 0;
                
                // Update source
                this.ui.audioSource.src = audioUrl;
                this.ui.audioPlayer.autoplay = false;
                
                // Load the audio
                await this.ui.audioPlayer.load();
                
                // Show listen button
                if (this.ui.listenAgainBtn) {
                    this.ui.listenAgainBtn.classList.remove('hidden');
                }

                // Open Fancybox immediately after generating
                const currentText = document.getElementById('marathiText').value;
                if (currentText) {
                    this.wordSync.init(currentText, this.ui.audioPlayer, 'syncText', {
                        enableEmphasis: true,
                        enablePauses: true
                    });
                }

                Fancybox.show([{
                    src: '#audioPlayerModal',
                    type: 'inline',
                    touch: false,
                    autoFocus: false,
                    dragToClose: false,
                    closeButton: true,
                    on: {
                        destroy: () => {
                            this.wordSync.cleanup();
                            if (this.ui.audioPlayer) {
                                this.ui.audioPlayer.pause();
                            }
                        }
                    }
                }]);
            }
        } catch (error) {
            console.error('Error handling TTS response:', error);
            this.notifications.error('ध्वनी वाजवण्यात त्रुटी आली');
        }
    }

    switchToTextTab() {
        if (!this.ui.textInputBtn || !this.ui.urlInputBtn) return;
        
        this.ui.textInputBtn.classList.add('active');
        this.ui.urlInputBtn.classList.remove('active');
        
        if (this.ui.textInputSection) {
            this.ui.textInputSection.classList.remove('hidden');
        }
        if (this.ui.urlInputSection) {
            this.ui.urlInputSection.classList.add('hidden');
        }

        // Prevent form submission
        return false;
    }

    switchToUrlTab() {
        if (!this.ui.textInputBtn || !this.ui.urlInputBtn) return;
        
        this.ui.urlInputBtn.classList.add('active');
        this.ui.textInputBtn.classList.remove('active');
        
        if (this.ui.urlInputSection) {
            this.ui.urlInputSection.classList.remove('hidden');
        }
        if (this.ui.textInputSection) {
            this.ui.textInputSection.classList.add('hidden');
        }

        // Prevent form submission
        return false;
    }

    switchToPdfTab() {
        if (!this.ui.pdfInputBtn) return;
        
        // Remove active class from all tabs
        [this.ui.textInputBtn, this.ui.urlInputBtn, this.ui.imageInputBtn, this.ui.pdfInputBtn]
            .forEach(btn => {
                if (btn) btn.classList.remove('active');
            });
        
        // Add active class to PDF tab
        this.ui.pdfInputBtn.classList.add('active');
        
        // Hide all sections
        [this.ui.textInputSection, this.ui.urlInputSection, this.ui.imageInputSection, this.ui.pdfInputSection]
            .forEach(section => {
                if (section) {
                    section.classList.add('hidden');
                    section.classList.remove('active');
                }
            });
        
        // Show PDF section
        if (this.ui.pdfInputSection) {
            this.ui.pdfInputSection.classList.remove('hidden');
            this.ui.pdfInputSection.classList.add('active');
        }
        
        // Prevent form submission
        return false;
    }

    switchToImageTab() {
        if (!this.ui.imageInputBtn) return;
        
        // Remove active class from all tabs
        [this.ui.textInputBtn, this.ui.urlInputBtn, this.ui.imageInputBtn, this.ui.pdfInputBtn]
            .forEach(btn => {
                if (btn) btn.classList.remove('active');
            });
        
        // Add active class to image tab
        this.ui.imageInputBtn.classList.add('active');
        
        // Hide all sections
        [this.ui.textInputSection, this.ui.urlInputSection, this.ui.imageInputSection, this.ui.pdfInputSection]
            .forEach(section => {
                if (section) {
                    section.classList.add('hidden');
                    section.classList.remove('active');
                }
            });
        
        // Show image section
        if (this.ui.imageInputSection) {
            this.ui.imageInputSection.classList.remove('hidden');
            this.ui.imageInputSection.classList.add('active');
        }
        
        // Prevent form submission
        return false;
    }

    setLoading(isLoading) {
        if (isLoading) {
            this.ui.loadingSection.classList.remove('hidden');
            this.ui.fetchButton.disabled = true;
        } else {
            this.ui.loadingSection.classList.add('hidden');
            this.ui.fetchButton.disabled = false;
        }
    }

    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            // Skip service worker registration on localhost/development
            if (window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1') {
                console.log('Skipping service worker registration in development');
                return;
            }
            
            // Only register on HTTPS
            if (window.location.protocol !== 'https:') {
                console.log('Service worker requires HTTPS');
                return;
            }

            navigator.serviceWorker.register('/static/tts/js/common/service-worker.js')
                .then(registration => {
                    console.log('ServiceWorker registration successful');
                })
                .catch(error => {
                    console.error('ServiceWorker registration failed:', error);
                });
        }
    }
}

// Initialize on DOMContentLoaded
let app = null;

document.addEventListener('DOMContentLoaded', () => {
    // Prevent multiple initializations
    if (app) return;
    
    try {
        app = new MarathiTTS();
        app.initialize();
    } catch (error) {
        console.error('Failed to initialize application:', error);
    }
}, { once: true });

export default MarathiTTS;
