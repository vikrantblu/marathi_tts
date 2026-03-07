/**
 * AudioQueue - Manages sequential playback of audio chunks
 * This is the single source of truth for the AudioQueue implementation
 */
export class AudioQueue {
    constructor(audioElement) {
        if (!audioElement) throw new Error('Audio element is required');
        
        this.audioElement = audioElement;
        this.queue = [];
        this.isPlaying = false;
        this.onQueueEmpty = null;
        this.onStartPlaying = null;
        this.onTrackChange = null;
        this.pausedManually = false;
        
        // Clear any existing event listeners
        this.audioElement.onended = null;
        this.audioElement.onerror = null;
        
        // Set up event listeners
        this.audioElement.addEventListener('ended', this.playNext.bind(this));
        this.audioElement.addEventListener('error', (e) => {
            console.error('Audio playback error:', e);
            setTimeout(() => this.playNext(), 500); // Skip failed track after a short delay
        });
    }
    
    addToQueue(url) {
        if (!url) {
            console.error('Cannot add empty URL to queue');
            return;
        }
        
        console.log('Adding to queue:', url);
        this.queue.push(url);
        
        // If not playing, start playback
        if (!this.isPlaying && !this.pausedManually) {
            this.playNext();
        }
    }
    
    playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            console.log('Queue empty, playback complete');
            if (this.onQueueEmpty) {
                this.onQueueEmpty();
            }
            return;
        }
        
        // Get next URL
        const nextUrl = this.queue.shift();
        
        // Notify about track change
        if (this.onTrackChange) {
            this.onTrackChange(nextUrl);
        }
        
        console.log('Playing next chunk:', nextUrl);
        
        // Set audio source
        this.audioElement.src = nextUrl;
        this.audioElement.load();
        
        // Start playback
        const playPromise = this.audioElement.play();
        if (playPromise !== undefined) {
            playPromise
                .then(() => {
                    this.isPlaying = true;
                    if (this.onStartPlaying) {
                        this.onStartPlaying();
                    }
                })
                .catch(error => {
                    console.error('Error playing audio:', error);
                    // Try the next one after a short delay
                    setTimeout(() => this.playNext(), 1000);
                });
        }
    }
    
    pause() {
        if (this.audioElement && this.isPlaying) {
            this.audioElement.pause();
            this.pausedManually = true;
            this.isPlaying = false;
        }
    }
    
    resume() {
        if (this.audioElement && this.pausedManually) {
            this.audioElement.play()
                .then(() => {
                    this.isPlaying = true;
                    this.pausedManually = false;
                })
                .catch(error => {
                    console.error('Error resuming audio:', error);
                });
        }
    }
    
    clear() {
        console.log('Clearing audio queue');
        this.queue = [];
        this.isPlaying = false;
        this.pausedManually = false;
        if (this.audioElement) {
            this.audioElement.pause();
        }
    }
}