import { Logger } from '../utils/logger.js';

export class PdfProcessor {
    constructor(loadingManager, notyf) {
        this.logger = new Logger('PdfProcessor');
        this.logger.info('Initializing PdfProcessor...');

        if (!loadingManager || !notyf) {
            const error = new Error('LoadingManager and Notyf are required');
            this.logger.error('Initialization failed', error);
            throw error;
        }

        try {
            this.loadingManager = loadingManager;
            this.notyf = notyf;
            this.isProcessing = false;
            
            this.initializeElements();
            this.bindEvents();
            this.logger.info('PdfProcessor initialized successfully');
        } catch (error) {
            this.logger.error('Failed to initialize PdfProcessor', error);
            throw error;
        }
    }

    initializeElements() {
        this.container = document.querySelector('.pdf-upload-container');
        this.input = document.getElementById('pdfUpload');
        this.preview = document.getElementById('pdfPreview');
        this.fileName = document.getElementById('pdfFileName');
        this.thumbnail = document.getElementById('pdfThumbnail');
        this.extractBtn = document.getElementById('extractPdfTextBtn');
        this.textArea = document.getElementById('marathiText');
    }

    bindEvents() {
        // File input change
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop events
        if (this.container) {
            this.container.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.container.classList.add('drag-over');
            });

            this.container.addEventListener('dragleave', () => {
                this.container.classList.remove('drag-over');
            });

            this.container.addEventListener('drop', (e) => {
                e.preventDefault();
                this.container.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length) {
                    this.input.files = files;
                    this.handleFileSelect({ target: this.input });
                }
            });
        }

        // Extract button click
        if (this.extractBtn) {
            this.extractBtn.addEventListener('click', () => this.extractText());
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        if (file.type !== 'application/pdf') {
            this.notyf.error('फक्त PDF फाईल स्वीकारली जाईल');
            return;
        }

        // Validate file size (10MB max)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            this.notyf.error('PDF फाईल 10MB पेक्षा कमी असावी');
            return;
        }

        // Update UI
        this.fileName.textContent = file.name;
        this.thumbnail.innerHTML = '<i class="fas fa-file-pdf fa-3x"></i>';
        this.preview.classList.remove('hidden');
        
        // Enable extract button
        this.extractBtn.disabled = false;
        
        this.notyf.success('PDF फाईल यशस्वीरित्या निवडली');
    }

    // Update extractText method with better debugging
    async extractText() {
        if (this.isProcessing) {
            this.logger.debug('PDF text extraction already in progress');
            return;
        }

        try {
            this.isProcessing = true;
            const file = this.input.files[0];
            if (!file) {
                this.notyf.error('कृपया प्रथम एक PDF फाईल निवडा');
                return;
            }

            this.loadingManager.showLoading('PDF मधून मजकूर काढत आहे...', 'कृपया प्रतीक्षा करा...');
            
            const formData = new FormData();
            formData.append('pdf_file', file);
            
            // Get CSRF token
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                              document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
                              getCookie('csrftoken');
            
            if (csrftoken) {
                formData.append('csrfmiddlewaretoken', csrftoken);
                this.logger.debug('CSRF token found and added to form data');
            } else {
                this.logger.warn('CSRF token not found');
            }

            // Log the request details
            this.logger.debug(`Sending PDF extraction request for file: ${file.name}, size: ${file.size} bytes`);
            
            try {
                // Try the correct URL from your urls.py
                const url = '/marathi_tts/tts/extract-pdf-text/';
                this.logger.debug(`Sending request to: ${url}`);
                
                // Update your fetch request to handle development environments better
                const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

                const response = await fetch(url, {
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin'
                    // Don't add any SSL-specific options here as fetch will use the browser's settings
                });

                this.logger.debug(`Server response status: ${response.status} ${response.statusText}`);
                
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status} ${response.statusText}`);
                }

                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error(`Expected JSON response but got ${contentType}`);
                }

                const data = await response.json();
                this.logger.debug('Response data:', data);
                
                if (data.success && data.text) {
                    // Check if the text is actually empty (just whitespace)
                    const trimmedText = data.text.trim();
                    if (!trimmedText) {
                        throw new Error('PDF मध्ये काहीही मजकूर सापडला नाही');
                    }
                    this.processExtractedText(data.text);
                } else {
                    throw new Error(data.error || 'PDF मधून मजकूर काढताना त्रुटी आली');
                }
            } catch (fetchError) {
                this.logger.error('Fetch error:', fetchError);
                throw fetchError;
            }
        } catch (error) {
            this.logger.error('PDF text extraction failed', error);
            
            if (error.name === 'AbortError') {
                this.notyf.error('प्रक्रिया खूप वेळ घेत आहे');
            } else if (error.message.includes('404')) {
                this.notyf.error('सर्व्हर एंडपॉइंट उपलब्ध नाही (404). URL तपासा.');
            } else if (error.message.includes('काहीही मजकूर सापडला नाही')) {
                this.notyf.error('या PDF मध्ये वाचनयोग्य मराठी मजकूर नाही. कदाचित ही स्कॅन केलेली प्रतिमा असू शकते.');
            } else {
                this.notyf.error(`PDF मधून मजकूर काढताना त्रुटी आली: ${error.message}`);
            }
        } finally {
            this.isProcessing = false;
            this.loadingManager.hideLoading();
        }
    }

    // Add a separate method for handling extracted text
    processExtractedText(text) {
        // Update text area
        if (this.textArea) {
            this.textArea.value = text;
            this.textArea.dispatchEvent(new Event('input'));
        }
        
        // Show success message
        this.notyf.success('PDF मधून मजकूर यशस्वीरित्या काढला');
        
        // Switch to text input tab
        const textInputBtn = document.getElementById('textInputBtn');
        if (textInputBtn) {
            setTimeout(() => {
                textInputBtn.click();
            }, 500);
        }
    }

    async cleanupBeforeTabSwitch() {
        // Stop any playing audio
        const audioPlayer = document.getElementById('audioPlayer');
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer.currentTime = 0;
        }

        // Close any open fancybox
        if (window.$.fancybox) {
            window.$.fancybox.close();
        }

        // Wait for animations to complete
        await new Promise(resolve => setTimeout(resolve, 300));
    }
}

// Helper function to get cookies (for CSRF token)
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}