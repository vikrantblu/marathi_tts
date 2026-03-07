import { getNotyf } from './notifications.js';
import { SUGGEST_CORRECTION_URL } from '../constants/api-endpoints.js';

export class CorrectionSuggestion {
    constructor() {
        this.setupEventListeners();
        this.selectedText = '';
        this.notyfInstance = getNotyf();
    }

    setupEventListeners() {
        // Handle text selection in main textarea
        const marathiText = document.getElementById('marathiText');
        marathiText?.addEventListener('mouseup', () => this.handleTextSelection());

        // Handle suggestion form submission
        const form = document.getElementById('suggestCorrectionForm');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));

        // Handle paste selected text button
        const pasteBtn = document.getElementById('pasteSelectedBtn');
        pasteBtn?.addEventListener('click', () => this.pasteSelectedText());

        // Character counter for notes
        const notesInput = document.getElementById('notesInput');
        notesInput?.addEventListener('input', (e) => this.updateCharCount(e));

        // Reset form when modal is closed
        const modal = document.getElementById('suggestCorrectionModal');
        modal?.addEventListener('hidden.bs.modal', () => this.resetForm());
    }

    handleTextSelection() {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        
        if (selectedText) {
            this.selectedText = selectedText;
            const display = document.getElementById('selectedTextDisplay');
            const container = document.querySelector('.selected-text-info');
            
            if (display && container) {
                display.textContent = selectedText;
                container.classList.remove('d-none');
            }
        }
    }

    pasteSelectedText() {
        if (this.selectedText) {
            const incorrectInput = document.getElementById('incorrectInput');
            if (incorrectInput) {
                incorrectInput.value = this.selectedText;
            }
        }
    }

    updateCharCount(event) {
        const counter = document.getElementById('notesCharCount');
        if (counter) {
            counter.textContent = event.target.value.length;
        }
    }

    async handleSubmit(event) {
        event.preventDefault();

        const formData = {
            incorrect_text: document.getElementById('incorrectInput').value,
            correct_text: document.getElementById('correctInput').value,
            category: document.getElementById('categoryInput').value,
            notes: document.getElementById('notesInput').value
        };

        try {
            const response = await fetch(SUGGEST_CORRECTION_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.notyfInstance.success('सुधारणा यशस्वीरित्या सादर केली!');
                this.resetForm();
                bootstrap.Modal.getInstance(document.getElementById('suggestCorrectionModal')).hide();
            } else {
                throw new Error('Submission failed');
            }
        } catch (error) {
            this.notyfInstance.error('सुधारणा सादर करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.');
        }
    }

    resetForm() {
        const form = document.getElementById('suggestCorrectionForm');
        if (form) {
            form.reset();
            document.querySelector('.selected-text-info')?.classList.add('d-none');
        }
        this.selectedText = '';
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content;
    }
}