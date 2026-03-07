import { Logger } from '../utils/logger.js';
import { EXTRACT_TEXT_URL } from '../constants/api-endpoints.js';

export class ImageProcessor {
    constructor(loadingManager, notyf) {
        this.logger = new Logger('ImageProcessor');
        this.logger.info('Initializing ImageProcessor...');

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
            this.logger.info('ImageProcessor initialized successfully');
        } catch (error) {
            this.logger.error('Failed to initialize ImageProcessor', error);
            throw error;
        }
    }

    initializeElements() {
        this.container = document.querySelector('.image-upload-container');
        this.input = document.getElementById('imageUpload');
        this.preview = document.getElementById('imagePreview');
        this.image = document.getElementById('uploadedImage');
        this.extractBtn = document.getElementById('extractTextBtn');
        this.textArea = document.getElementById('marathiText');
        this.loadingSection = document.getElementById('loadingSection');
        this.loadingMainText = document.getElementById('loadingMainText');
        this.loadingSubText = document.getElementById('loadingSubText');
        this.progressBar = document.getElementById('progressBar');
    }

    bindEvents() {
        // File input change
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop events
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

        // Extract button click
        this.extractBtn.addEventListener('click', () => this.extractText());
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        const validTypes = ['image/jpeg', 'image/png', 'image/gif'];
        const maxSize = 5 * 1024 * 1024; // 5MB

        if (!validTypes.includes(file.type)) {
            this.notyf.error('फक्त JPG, PNG किंवा GIF छायाचित्रे स्वीकारली जातील');
            return;
        }

        if (file.size > maxSize) {
            this.notyf.error('छायाचित्र 5MB पेक्षा कमी असावे');
            return;
        }

        this.loadingManager.showLoading('छायाचित्र लोड करत आहे...', 'कृपया प्रतीक्षा करा...');

        this.optimizeImage(file).then(optimizedFile => {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.image.src = e.target.result;
                this.preview.classList.remove('hidden');
                this.notyf.success('छायाचित्र यशस्वीरित्या अपलोड केले');
                this.loadingManager.hideLoading();
            };
            reader.onerror = () => {
                this.notyf.error('छायाचित्र लोड करताना त्रुटी आली');
                this.loadingManager.hideLoading();
            };
            reader.readAsDataURL(optimizedFile || file);
        });
    }

    async optimizeImage(file) {
        try {
            // Create an image bitmap for faster processing
            const bitmap = await createImageBitmap(file);
            
            // Calculate new dimensions while maintaining aspect ratio
            const maxDim = 1024;
            let width = bitmap.width;
            let height = bitmap.height;
            
            if (width > maxDim || height > maxDim) {
                if (width > height) {
                    height = Math.round(height * (maxDim / width));
                    width = maxDim;
                } else {
                    width = Math.round(width * (maxDim / height));
                    height = maxDim;
                }
            }

            // Create canvas for resizing
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            // Use better image smoothing
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            
            // Draw resized image
            ctx.drawImage(bitmap, 0, 0, width, height);
            
            // Convert to blob with optimal quality
            return new Promise(resolve => {
                canvas.toBlob(
                    blob => resolve(blob),
                    'image/jpeg',
                    0.85  // Optimal quality setting
                );
            });
        } catch (error) {
            this.logger.error('Image optimization failed', error);
            return null;
        }
    }

    async extractText() {
        if (this.isProcessing) {
            this.logger.debug('Text extraction already in progress');
            return;
        }

        try {
            this.isProcessing = true;
            const file = this.input.files[0];
            if (!file) {
                this.notyf.error('कृपया प्रथम एक छायाचित्र निवडा');
                return;
            }

            this.loadingManager.showLoading('छायाचित्रातील मजकूर ओळखत आहे...', 'कृपया प्रतीक्षा करा');
            
            // Create FormData object
            const formData = new FormData();
            formData.append('image', file); // Make sure this field name matches what the server expects
            
            // Get CSRF token
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                            document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
                            getCookie('csrftoken');
            
            if (csrftoken) {
                formData.append('csrfmiddlewaretoken', csrftoken);
            }
            
            // Use the correct URL path for the OCR endpoint
            const response = await fetch(EXTRACT_TEXT_URL, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.text) {
                // Update text area
                if (this.textArea) {
                    this.textArea.value = data.text;
                    this.textArea.dispatchEvent(new Event('input'));
                }
                
                // Show success message
                this.notyf.success('छायाचित्रातील मजकूर यशस्वीरित्या ओळखला गेला');
                
                // Switch to text input tab
                const textInputBtn = document.getElementById('textInputBtn');
                if (textInputBtn) {
                    setTimeout(() => {
                        textInputBtn.click();
                    }, 500);
                }
            } else {
                throw new Error(data.error || 'छायाचित्रातून मजकूर ओळखण्यात त्रुटी आली');
            }
        } catch (error) {
            this.logger.error('Text extraction failed', error);
            this.notyf.error(error.message || 'छायाचित्रातून मजकूर ओळखण्यात त्रुटी आली');
        } finally {
            this.isProcessing = false;
            this.loadingManager.hideLoading();
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