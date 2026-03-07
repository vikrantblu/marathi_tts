import { ABBREVIATION_MAP, EMPHASIS_PATTERNS, PAUSE_PATTERNS, PAUSE_DURATIONS } from '../constants/text-constants.js';

export class WordSync {
    constructor() {
        this.words = [];
        this.currentIndex = 0;
        this.container = null;
        this.audioElement = null;
        this.updateInterval = null;
        this.eventListeners = new Map();
        this.syncDrift = 0; // Track cumulative drift
        this.options = {
            enableEmphasis: false,
            enablePauses: false
        };

        // Use centralized abbreviation mapping
        this.abbreviationMap = ABBREVIATION_MAP;
    }

    init(text, audioElement, containerId = 'syncText', options = {}) {
        this.cleanup(); // Clean up before initializing
        this.options = { ...this.options, ...options };
        
        this.container = document.getElementById(containerId);
        this.audioElement = audioElement;
        this.words = this.processText(text);
        
        if (!this.container || !this.audioElement) return;

        this.renderWords();
        this.bindAudioEvents();
    }

    cleanup() {
        // Clear interval if exists
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }

        // Remove all event listeners
        if (this.audioElement && this.eventListeners.size > 0) {
            this.eventListeners.forEach((handler, event) => {
                this.audioElement.removeEventListener(event, handler);
            });
            this.eventListeners.clear();
        }

        // Reset state
        this.words = [];
        this.currentIndex = 0;
        this.audioElement = null;
        
        // Clear container
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.container = null;
    }

    shouldEmphasize(word) {
        // Rules for word emphasis in Marathi (using centralized patterns)
        return EMPHASIS_PATTERNS.some(pattern => pattern.test(word));
        }

        shouldPauseAfter(word) {
        // Enhanced rules for pauses in Marathi (using centralized patterns)
        return PAUSE_PATTERNS.some(pattern => pattern.test(word));
        }

        calculatePauseDuration(word) {
        // Different pause durations based on word type
        if (/[।॥!?]$/.test(word)) return 0.8; // Long pause after major punctuation
        if (/[,:]$/.test(word)) return 0.4;   // Medium pause after minor punctuation
        if (/^(परंतु|तथापि|म्हणून|कारण|त्याचप्रमाणे|याव्यतिरिक्त)$/.test(word)) return 0.5; // Major conjunctions
        if (/^(का|काय|कसे|कोण|केव्हा|कुठे|किती|कशामुळे)$/.test(word)) return 0.4; // Question words
        if (/(पर्यंत|साठी|मुळे|करिता|विषयी|बाबत|संदर्भात)$/.test(word)) return 0.3; // Phrase endings
        if (/^[०-९]+$/.test(word)) return 0.3; // Numbers
        if (/.{12,}$/.test(word)) return 0.3; // Long words
        return 0.2; // Default small pause
    }
    processText(text) {
        if (!text) return [];
        
        // Split text into sentences first
        const sentences = text.split(/([।॥!?])/);
        let allWords = [];
        let position = 0;
        
        // Track sentence boundaries for better sync with long texts
        let sentenceStartIndex = 0;
        
        sentences.forEach((sentence, sentenceIndex) => {
            const words = sentence.trim().split(/\s+/).filter(w => w.length > 0);
            const sentenceLength = words.length;
            
            if (sentenceLength > 0) {
                sentenceStartIndex = position;
            }
            
            words.forEach((word, index) => {
                const isLastInSentence = index === sentenceLength - 1;
                const isFirstInSentence = index === 0;
                
                allWords.push({
                    text: word,
                    isEmphasis: this.options.enableEmphasis && this.shouldEmphasize(word),
                    pauseAfter: this.options.enablePauses && (
                        this.shouldPauseAfter(word) || 
                        isLastInSentence
                    ),
                    pauseDuration: this.calculatePauseDuration(word),
                    position: position++,
                    isFirstInSentence,
                    isLastInSentence,
                    sentenceIndex: sentenceIndex,
                    sentenceStartIndex: sentenceStartIndex,
                    sentencePosition: index  // Position within sentence
                });
            });
        });
        
        return allWords;
    }

    renderWords() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="word-sync-container">
                ${this.words
                    .map(word => {
                        const displayText = word.text; // Keep the original text for display
                        const expandedText = this.abbreviationMap[word.text] || word.text; // Use expanded text for timing
                        return `
                            <span class="word${word.isEmphasis ? ' emphasis' : ''}" 
                                  data-duration="${word.pauseDuration}">
                                ${displayText}
                            </span>
                            ${word.pauseAfter ? '<span class="pause"></span>' : ''}
                        `;
                    })
                    .join(' ')}
            </div>`;
    }

    bindAudioEvents() {
        if (!this.audioElement) return;

        // Store event listeners so we can remove them later
        const playHandler = () => this.startSync();
        const pauseHandler = () => this.stopSync();
        const endedHandler = () => this.reset();

        this.eventListeners.set('play', playHandler);
        this.eventListeners.set('pause', pauseHandler);
        this.eventListeners.set('ended', endedHandler);

        this.audioElement.addEventListener('play', playHandler);
        this.audioElement.addEventListener('pause', pauseHandler);
        this.audioElement.addEventListener('ended', endedHandler);
    }

    startSync() {
        if (!this.audioElement || !this.words.length) return;

        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        const totalDuration = this.audioElement.duration;
        const timings = this.calculateWordTimings(this.words);
        const playbackRate = this.audioElement.playbackRate || 1.0;

        this.wordTimings = this.scaleTimings(timings, totalDuration, playbackRate);

        // Use RAF (requestAnimationFrame) instead of setInterval for smoother updates
        const updateHighlight = () => {
            if (!this.audioElement || this.audioElement.paused) {
                return;
            }

            const currentTime = this.audioElement.currentTime;
            const wordIndex = this.findWordAtTime(currentTime, this.wordTimings, playbackRate);

            // Calculate drift
            if (wordIndex >= 0 && wordIndex < this.wordTimings.length) {
                const expectedTime = this.wordTimings[wordIndex].start;
                this.syncDrift = currentTime - expectedTime;

                // Correct drift if it exceeds a threshold
                if (Math.abs(this.syncDrift) > 0.2) { // 200ms threshold
                    this.syncDrift = 0; // Reset drift
                    this.highlightWord(wordIndex); // Force sync
                }
            }

            if (wordIndex !== this.currentIndex) {
                this.currentIndex = wordIndex;
                this.highlightWord(this.currentIndex);
            }

            // Continue the animation loop
            if (!this.audioElement.paused && !this.audioElement.ended) {
                this.animationFrame = requestAnimationFrame(updateHighlight);
            }
        };

        // Start the animation loop
        this.animationFrame = requestAnimationFrame(updateHighlight);

        // Add a listener for rate changes
        const rateChangeHandler = () => {
            // Recalculate timings when playback rate changes
            const newRate = this.audioElement.playbackRate || 1.0;
            this.wordTimings = this.scaleTimings(timings, totalDuration, newRate);
        };

        this.audioElement.addEventListener('ratechange', rateChangeHandler);
        this.eventListeners.set('ratechange', rateChangeHandler);
    }

    scaleTimings(timings, totalDuration, playbackRate) {
        if (!timings.length) return [];

        const calculatedDuration = timings[timings.length - 1].end;
        const scaleFactor = totalDuration / calculatedDuration;

        return timings.map((timing, index) => {
            const adjustedScale = scaleFactor / playbackRate;

            return {
                start: timing.start * adjustedScale,
                duration: timing.duration * adjustedScale,
                end: timing.end * adjustedScale
            };
        });
    }

    calculateWordTimings(words) {
        let currentTime = 0;
        return words.map(word => {
            // Expand abbreviations if present
            const expandedText = this.abbreviationMap[word.text] || word.text;

            // More accurate Marathi syllable-based timing
            const syllableCount = this.countSyllables(expandedText);
            const charLength = expandedText.length;

            // Base duration calculation - more nuanced approach
            let duration = syllableCount * 0.18; // ~180ms per syllable

            // Character length adjustment - longer words need proportionally less time per character
            if (charLength > 8) {
                duration *= (1 - (charLength - 8) * 0.01); // Slightly reduce duration for longer words
            }

            // Special case adjustments
            if (/[।॥!?]$/.test(word.text)) {
                duration += 0.25; // End of sentence
            } else if (/[,:]$/.test(word.text)) {
                duration += 0.12; // Mid-sentence pause
            }

            // Handle Marathi conjunct consonants
            const conjuncts = (expandedText.match(/्[कखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह]/g) || []).length;
            if (conjuncts > 0) {
                duration += conjuncts * 0.04; // Slight increase for conjuncts
            }

            // Handle nukta characters
            if (expandedText.includes('़')) {
                duration += 0.05; // Slight increase for nukta characters
            }

            // Special case for numbers - they're read more slowly
            if (/[०१२३४५६७८९]+/.test(expandedText)) {
                duration += 0.1;
            }

            // Set minimum and maximum durations
            duration = Math.max(duration, 0.1); // Minimum 100ms
            duration = Math.min(duration, 1.5); // Maximum 1.5s

            const timing = {
                start: currentTime,
                duration: duration,
                end: currentTime + duration
            };

            currentTime = timing.end;

            // Add pause after word if needed
            if (word.pauseAfter) {
                currentTime += (word.pauseDuration || 0.2) * 0.7; // Shorter pauses
            }

            return timing;
        });
    }

    countSyllables(text) {
        if (!text || typeof text !== 'string') {
            return 1;
        }
        
        // Remove punctuation that doesn't affect syllable count
        text = text.replace(/[.,।॥!?:;()[\]{}]/g, '');
        
        // Count Marathi vowels (independent and dependent forms)
        let vowelCount = (text.match(/[अआइईउऊऋएऐओऔ]|[ाीिीुूृॄेैोौंः]/g) || []).length;
        
        // Adjust for conjunct consonants (which reduce syllable count)
        const conjunctCount = (text.match(/्/g) || []).length;
        
        // Adjust for special cases in Marathi pronunciation
        // Some consonant clusters are read as single syllables
        const specialClusters = (text.match(/[त्र|ज्ञ|क्ष|श्र|द्र|ट्र|ड्र|श्व]/g) || []).length;
        
        // Ensure minimum syllable count
        return Math.max(1, vowelCount - conjunctCount - specialClusters);
    }

    findWordAtTime(time, timings, playbackRate) {
        if (!timings.length) return -1;
        
        // Dynamic look-ahead based on playback rate and position in speech
        // For long texts, also consider accumulated drift
        const baseDelay = 0.08; // Base delay in seconds
        const speedAdjustment = 1 / playbackRate; // Adjust for playback speed
        
        // Find which segment of the audio we're in (beginning, middle, end)
        const lastTime = timings[timings.length - 1].end;
        const position = Math.min(1, time / lastTime); // 0 to 1
        
        // Adjust look-ahead based on position in audio
        // Beginning: more look-ahead, End: less look-ahead
        const positionFactor = position < 0.2 ? 1.5 :
                               position > 0.8 ? 0.8 : 1.0;
        
        // For long texts, apply dynamic adjustment based on observed drift
        let driftAdjustment = 0;
        if (this.isLongText && this.syncDrift) {
            driftAdjustment = this.syncDrift * position; // Progressive adjustment
        }
        
        const lookAheadTime = (baseDelay * speedAdjustment * positionFactor) - driftAdjustment;
        const adjustedTime = Math.max(0, time - lookAheadTime);
        
        // Find the word that matches the adjusted time
        for (let i = 0; i < timings.length; i++) {
            if (adjustedTime >= timings[i].start && adjustedTime < timings[i].end) {
                return i;
            }
        }
        
        // Edge cases
        if (adjustedTime >= timings[timings.length - 1].end) {
            return timings.length - 1; // After last word
        }
        
        if (adjustedTime < timings[0].start) {
            return -1; // Before first word
        }
        
        // Find the closest word if we can't find an exact match
        return timings.reduce((closest, timing, index) => {
            const distance = Math.min(
                Math.abs(adjustedTime - timing.start),
                Math.abs(adjustedTime - timing.end)
            );
            
            if (distance < Math.min(
                Math.abs(adjustedTime - timings[closest].start),
                Math.abs(adjustedTime - timings[closest].end)
            )) {
                return index;
            }
            
            return closest;
        }, 0);
    }

    stopSync() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    highlightWord(index) {
        if (!this.container) return;
        
        const words = this.container.getElementsByClassName('word');
        Array.from(words).forEach(word => {
            word.classList.remove('active', 'previous');
        });

        if (index >= 0 && index < words.length) {
            words[index].classList.add('active');
            if (index > 0) {
                words[index - 1].classList.add('previous');
            }
            this.scrollToWord(words[index]);
        }
    }

    scrollToWord(element) {
        const container = this.container;
        const elementRect = element.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        
        if (elementRect.bottom > containerRect.bottom || elementRect.top < containerRect.top) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    reset() {
        this.stopSync();
        this.currentIndex = 0;
        this.highlightWord(0);
    }

    calibrateWithAudio(milestoneWords = []) {
        if (!this.audioElement || !this.words.length) return;

        // If no milestone words provided, use punctuation as milestones
        if (!milestoneWords.length) {
            milestoneWords = this.words
                .map((word, index) => ({ word, index }))
                .filter(item => /[।॥,!?]$/.test(item.word.text))
                .map(item => item.index);

            // Add beginning and end as milestones
            milestoneWords.unshift(0);
            milestoneWords.push(this.words.length - 1);
        }

        // Listen for timeupdate events to gather real timing data
        this.calibrationData = {
            milestones: milestoneWords,
            timings: new Array(milestoneWords.length).fill(null),
            current: 0
        };

        const calibrationHandler = () => {
            const currentTime = this.audioElement.currentTime;
            const milestone = this.calibrationData.milestones[this.calibrationData.current];

            if (this.currentIndex === milestone) {
                this.calibrationData.timings[this.calibrationData.current] = currentTime;
                this.calibrationData.current++;

                // If we've collected all milestone timings, apply the calibration
                if (this.calibrationData.current >= this.calibrationData.milestones.length) {
                    this.applyCalibration();
                    this.audioElement.removeEventListener('timeupdate', calibrationHandler);
                }
            }
        };

        this.audioElement.addEventListener('timeupdate', calibrationHandler);
    }

    applyCalibration() {
        const { milestones, timings } = this.calibrationData;

        // Interpolate timings between milestones
        for (let i = 0; i < milestones.length - 1; i++) {
            const startMilestone = milestones[i];
            const endMilestone = milestones[i + 1];
            const startTime = timings[i];
            const endTime = timings[i + 1];

            if (startTime === null || endTime === null) continue;

            const wordCount = endMilestone - startMilestone;
            const timeSpan = endTime - startTime;

            for (let j = startMilestone; j <= endMilestone; j++) {
                const progress = (j - startMilestone) / wordCount;
                const adjustedTime = startTime + (timeSpan * progress);

                this.wordTimings[j].start = adjustedTime;
                this.wordTimings[j].end = adjustedTime + this.wordTimings[j].duration;
            }
        }
    }
}