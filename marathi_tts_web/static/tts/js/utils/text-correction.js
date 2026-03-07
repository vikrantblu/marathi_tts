import { getNotyf } from './notifications.js';
import { CORRECT_TEXT_URL, FORMAT_TEXT_URL } from '../constants/api-endpoints.js';

export class TextCorrection {
    constructor() {
        if (window.textCorrectionInstance) {
            return window.textCorrectionInstance;
        }
        this.correctionEndpoint = CORRECT_TEXT_URL;
        this.formatEndpoint = FORMAT_TEXT_URL;
        this.processing = false;
        this.lastOperation = null;

        this.toast = getNotyf();
        this.initializeListeners();
        window.textCorrectionInstance = this;
    }
    
    initializeListeners() {
        const correctBtn = document.getElementById('aiCorrectBtn');
        const formatBtn = document.getElementById('aiFormatBtn');
        
        if (correctBtn) {
            correctBtn.addEventListener('click', () => this.handleButtonClick('correction'));
        }
        
        if (formatBtn) {
            formatBtn.addEventListener('click', () => this.handleButtonClick('format'));
        }
    }
    
    async handleButtonClick(type) {
        if (this.processing) {
            console.log('Already processing, please wait...');
            return;
        }

        const textArea = document.getElementById('marathiText');
        if (!textArea || !textArea.value.trim()) return;

        const button = document.getElementById(type === 'correction' ? 'aiCorrectBtn' : 'aiFormatBtn');
        
        try {
            this.processing = true;
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> प्रक्रिया सुरू आहे...';
            }

            // Force model initialization on first correction
            const endpoint = type === 'correction' ? this.correctionEndpoint : this.formatEndpoint;
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    text: textArea.value,
                    operation_type: type,
                    force_init: type === 'correction' && !this.lastOperation
                })
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const result = await response.json();
            if (result.success) {
                textArea.value = result.correctedText || result.formattedText;
                this.lastOperation = type;
            }
        } catch (error) {
            console.error('Error:', error);
            this.toast.error('त्रुटी: ' + error.message);
        } finally {
            this.processing = false;
            if (button) {
                button.disabled = false;
                button.innerHTML = type === 'correction' ? 
                    '<i class="fas fa-spell-check"></i> शब्द सुधारा' : 
                    '<i class="fas fa-align-left"></i> मजकूर स्वरूपित करा';
            }
        }
    }
    
    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content;
    }
}

// Initialize only once when DOM is ready
if (typeof window !== 'undefined' && !window.textCorrectionInitialized) {
    window.textCorrectionInitialized = true;
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.textCorrection) {
            window.textCorrection = new TextCorrection();
        }
    });
}


export function preprocessMarathiText(text, useSSML = true) {
    if (!useSSML) {
        return { text, isSSML: false };
    }

    text = text.trim()
              .replace(/\s*([।॥!?])\s*/g, '$1\n')  
              .replace(/\s+/g, ' ')                 
              .replace(/([^।॥!?])(\s*\n\s*)/g, '$1। '); 

    let ssmlText = '<speak><prosody rate="medium">';
    
    const sentences = text.split(/\n/).filter(s => s.trim());
    
    for (let i = 0; i < sentences.length; i++) {
        const sentence = sentences[i].trim();
        if (!sentence) continue;

        const match = sentence.match(/^(.+?)([।॥!?])?$/);
        if (!match) continue;

        const [, content, marker] = match;
        
        ssmlText += '<s><prosody rate="95%">';
        
        const words = content.trim().split(/\s+/);
        words.forEach((word, idx) => {
            ssmlText += word;
            
            if (idx < words.length - 1) {
                ssmlText += ' ';
            }
        });

        if (marker) {
            ssmlText += `${marker}<break time="1000ms" strength="x-strong"/>`;
        }
        
        ssmlText += '</prosody></s>';
    }
    
    ssmlText += '</prosody></speak>';

    return {
        text: ssmlText,
        isSSML: true,
        metadata: {
            sentenceCount: sentences.length,
            hasSentenceMarkers: true
        }
    };
}