export class AudioController {
    constructor() {
        this.currentAudio = null;
        this.isPlaying = false;
        this.eventsBound = false;
    }

    setAudio(audio) {
        if (this.currentAudio === audio) return;
        
        if (this.currentAudio) {
            this.cleanup();
        }
        
        this.currentAudio = audio;
        this.bindEvents();
    }

    bindEvents() {
        if (!this.currentAudio || this.eventsBound) return;
        
        this.currentAudio.addEventListener('play', () => this.isPlaying = true);
        this.currentAudio.addEventListener('pause', () => this.isPlaying = false);
        this.currentAudio.addEventListener('ended', () => this.isPlaying = false);
        
        this.eventsBound = true;
    }

    cleanup() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.isPlaying = false;
        this.eventsBound = false;
    }

    async play(audio) {
        try {
            if (this.currentAudio && this.currentAudio !== audio) {
                await this.stop();
            }
            
            this.currentAudio = audio;
            this.isPlaying = true;
            
            // Manual play only when requested
            if (!this.currentAudio.paused) {
                await this.currentAudio.pause();
            }
            
        } catch (error) {
            console.error('Playback error:', error);
            this.isPlaying = false;
        }
    }

    pause() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.isPlaying = false;
        }
    }

    async stop() {
        if (this.currentAudio) {
            await this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.isPlaying = false;
        }
    }

    setVolume(value) {
        if (this.currentAudio) {
            this.currentAudio.volume = Math.max(0, Math.min(1, value));
        }
    }

    setPlaybackRate(value) {
        if (this.currentAudio) {
            this.currentAudio.playbackRate = Math.max(0.25, Math.min(4, value));
        }
    }

    async downloadAudio(audioUrl) {
        try {
            let fullUrl = audioUrl.startsWith('/') ? 
                window.location.origin + audioUrl : audioUrl;

            const response = await fetch(fullUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            
            link.href = blobUrl;
            link.download = audioUrl.split('/').pop() || 'audio.wav';
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            
            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(blobUrl);
            }, 100);

            return true;
        } catch (error) {
            console.error('Download error:', error);
            throw error;
        }
    }

    async stopPlayback() {
        if (this.currentAudio && !this.currentAudio.paused) {
            await this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
        }
    }

    onPlay() {
        this.isPlaying = true;
        // Disable navigation controls while playing
        if ($.fancybox.getInstance()) {
            $.fancybox.getInstance().update({
                closeButton: false,
                keyboard: false,
                clickSlide: false,
                clickOutside: false
            });
        }
    }

    onPause() {
        this.isPlaying = false;
        // Re-enable navigation controls
        if ($.fancybox.getInstance()) {
            $.fancybox.getInstance().update({
                closeButton: true,
                keyboard: true,
                clickSlide: 'close',
                clickOutside: 'close'
            });
        }
    }

    onEnded() {
        this.isPlaying = false;
        // Reset UI elements when audio ends
        const syncText = document.getElementById('syncText');
        if (syncText) {
            const activeWord = syncText.querySelector('.sync-word.active');
            if (activeWord) {
                activeWord.classList.remove('active');
            }
        }
        // Re-enable navigation controls
        if ($.fancybox.getInstance()) {
            $.fancybox.getInstance().update({
                closeButton: true,
                keyboard: true,
                clickSlide: 'close',
                clickOutside: 'close'
            });
        }
    }
}

function createAudioPlayer(audioUrl, filename, text) {
    const uniqueId = 'audio-' + Math.random().toString(36).substr(2, 9);
    const syncId = 'sync-' + uniqueId;
    
    const playerHtml = `
        <div class="audio-player-container">
            <a href="#${uniqueId}" 
               data-fancybox="audio-player"
               class="btn btn-primary play-button">
                <i class="fas fa-play"></i> Play Audio
            </a>
            
            <div id="${uniqueId}" style="display:none;">
                <div class="audio-modal">
                    <div id="${syncId}" class="word-sync-text"></div>
                    
                    <audio controls class="audio-player" preload="auto">
                        <source src="${audioUrl}" type="audio/wav">
                        Your browser does not support the audio element.
                    </audio>
                    
                    <a href="${audioUrl}" 
                       download="${filename}"
                       class="btn btn-secondary download-button">
                        <i class="fas fa-download"></i> Download
                    </a>
                </div>
            </div>
        </div>
    `;

    $('#audioPlayerModal').html(playerHtml);

    // Initialize Fancybox with WordSync support
    $('[data-fancybox="audio-player"]').fancybox({
        afterShow: function(instance, current) {
            const audioElement = current.$slide.find('audio')[0];
            const wordSync = new WordSync();
            
            wordSync.init(text, audioElement, syncId, {
                enableEmphasis: true,
                enablePauses: true
            });

            // Auto-play audio
            if (audioElement) {
                audioElement.play();
            }
        },
        beforeClose: function() {
            // Pause audio when closing modal
            const audioElement = this.$slide.find('audio')[0];
            if (audioElement) {
                audioElement.pause();
            }
        }
    });

    // Trigger custom event
    $(document).trigger('audioReady');
}