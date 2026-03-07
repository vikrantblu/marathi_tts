import { Logger } from '../utils/logger.js';

export class LoadingManager {
    constructor() {
        this.logger = new Logger('LoadingManager');
        this.isLoading = false;
        this.createLoadingOverlay();
    }

    createLoadingOverlay() {
        this.loadingSection = document.getElementById('loadingSection');
        if (!this.loadingSection) {
            this.loadingSection = document.createElement('div');
            this.loadingSection.id = 'loadingSection';
            this.loadingSection.className = 'loading-section hidden';
            
            const content = `
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <div id="loadingMainText" class="loading-text"></div>
                    <div id="loadingSubText" class="loading-text-sub"></div>
                    <div id="progressBar" class="progress-bar"></div>
                </div>
            `;
            
            this.loadingSection.innerHTML = content;
            
            // Find and append to the input-card instead of active section
            const inputCard = document.querySelector('.input-card');
            if (inputCard) {
                inputCard.appendChild(this.loadingSection);
            }
        }
        
        this.mainText = this.loadingSection.querySelector('#loadingMainText');
        this.subText = this.loadingSection.querySelector('#loadingSubText');
        this.progressBar = this.loadingSection.querySelector('#progressBar');
    }

    async showLoading(mainText = '', subText = '') {
        // Prevent multiple loading states
        if (this.isLoading) {
            return;
        }

        this.isLoading = true;
        
        try {
            if (this.mainText) this.mainText.textContent = mainText;
            if (this.subText) this.subText.textContent = subText;
            if (this.progressBar) this.progressBar.style.width = '0%';
            
            // Ensure any playing audio is properly stopped
            const audioPlayer = document.getElementById('audioPlayer');
            if (audioPlayer) {
                await audioPlayer.pause();
                audioPlayer.currentTime = 0;
            }
            
            this.loadingSection.classList.remove('hidden');
        } catch (error) {
            this.logger.error('Error showing loading state', error);
        }
    }

    hideLoading() {
        this.isLoading = false;
        if (this.loadingSection) {
            this.loadingSection.classList.add('hidden');
        }
    }

    updateProgress(percent) {
        if (this.progressBar && percent >= 0 && percent <= 100) {
            this.progressBar.style.width = `${percent}%`;
        }
    }
}