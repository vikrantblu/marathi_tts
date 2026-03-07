import { EMOTION_TRANSLATIONS, EMOTION_COLORS, DEFAULT_EMOTION_COLOR } from '../constants/emotion-constants.js';
import { ANALYZE_EMOTION_URL } from '../constants/api-endpoints.js';

// Add this function or update your existing one
function updateEmotionDisplay(emotionData) {
    console.log('Updating emotion display with:', emotionData);
    
    // Find the emotion display container - check both ID formats
    const emotionDisplay = document.getElementById('emotion-display') || 
                           document.getElementById('emotionDisplay');
    
    if (!emotionDisplay) {
        console.error('Emotion display element not found!');
        return;
    }
    
    // Clear previous content
    emotionDisplay.innerHTML = '';
    
    // If no emotion data, exit early
    if (!emotionData || !emotionData.scores) {
        emotionDisplay.innerHTML = '<p>No emotion data available</p>';
        return;
    }
    
    // Add emotion title with dominant emotion
    const emotionTitle = document.createElement('h5');
    emotionTitle.className = 'emotion-title';
    emotionTitle.textContent = `भावना: ${translateEmotion(emotionData.dominant || 'neutral')}`;
    emotionDisplay.appendChild(emotionTitle);
    
    // Create emotion chart
    const chartContainer = document.createElement('div');
    chartContainer.className = 'emotion-chart';
    
    // Sort emotions by score (highest first)
    const sortedEmotions = Object.entries(emotionData.scores)
        .sort((a, b) => b[1] - a[1]);
    
    // Create bars for each emotion
    sortedEmotions.forEach(([emotion, score]) => {
        // Create bar container
        const barContainer = document.createElement('div');
        barContainer.className = 'emotion-bar-container';
        
        // Create emotion label
        const label = document.createElement('div');
        label.className = 'emotion-name';
        label.textContent = translateEmotion(emotion);
        
        // Create bar outer container
        const barOuter = document.createElement('div');
        barOuter.className = 'emotion-bar-outer';
        
        // Create bar inner fill
        const barInner = document.createElement('div');
        barInner.className = `emotion-bar-inner emotion-${emotion}`;
        barInner.style.width = `${Math.round(score * 100)}%`;
        barInner.style.backgroundColor = getEmotionColor(emotion);
        
        // Create score label
        const scoreLabel = document.createElement('div');
        scoreLabel.className = 'emotion-score';
        scoreLabel.textContent = `${Math.round(score * 100)}%`;
        
        // Assemble components
        barOuter.appendChild(barInner);
        barContainer.appendChild(label);
        barContainer.appendChild(barOuter);
        barContainer.appendChild(scoreLabel);
        chartContainer.appendChild(barContainer);
    });
    
    emotionDisplay.appendChild(chartContainer);
    emotionDisplay.style.display = 'block';
}

function translateEmotion(emotion) {
    return EMOTION_TRANSLATIONS[emotion] || emotion;
}

function getEmotionColor(emotion) {
    return EMOTION_COLORS[emotion] || DEFAULT_EMOTION_COLOR;
}
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export class EmotionHandler {
    constructor() {
        this.emotionDisplay = document.getElementById('emotion-display');
        this.intensityRange = document.getElementById('emotionIntensityRange');
        this.intensityValue = document.getElementById('emotionIntensityValue');
        this.textInput = document.getElementById('marathiText') || document.getElementById('tts-input');

        if (this.textInput) {
            this.setupListeners();
        } else {
            console.warn('Required text input element not found');
        }
    }

    setupListeners() {
        if (this.intensityRange && this.intensityValue) {
            this.intensityRange.addEventListener('input', (e) => {
                this.intensityValue.textContent = e.target.value;
            });
        }

        if (this.textInput) {
            this.textInput.addEventListener(
                'input',
                debounce((e) => this.analyzeEmotions(e.target.value), 500)
            );
        }
    }

    async analyzeEmotions(text) {
        if (!text?.trim()) {
            this.updateEmotionDisplay(null);
            return;
        }

        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }

            const response = await fetch(ANALYZE_EMOTION_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ text, analyze_full: true })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }

            const result = await response.json();

            if (!result || !result.dominant) {
                throw new Error('Invalid emotion analysis response');
            }

            this.updateEmotionDisplay(result);
            return result;

        } catch (error) {
            console.error('Error analyzing emotions:', error);
            this.updateEmotionDisplay(null);
            return {
                dominant: 'neutral',
                intensity: 0.5,
                scores: { neutral: 1.0 }
            };
        }
    }

    updateEmotionDisplay(emotionData) {
        if (!this.emotionDisplay) {
            console.warn('Emotion display element not found');
            return;
        }

        if (!emotionData || !emotionData.scores) {
            this.emotionDisplay.innerHTML = '<p>No emotion data available</p>';
            return;
        }

        const emotionNames = {
            happy: 'आनंदी',
            sad: 'दुःखी',
            angry: 'रागीट',
            neutral: 'सामान्य',
            fear: 'भयभीत',
            surprise: 'आश्चर्यचकित',
            disgust: 'तिरस्कार',
            love: 'प्रेमळ',
            excitement: 'उत्साही',
            worry: 'चिंतीत',
            calm: 'शांत',
            proud: 'अभिमानी'
        };

        const dominantEmotion = emotionData.dominant || 'neutral';
        const intensity = emotionData.intensity || 0.5;
        const scores = emotionData.scores || {};

        this.emotionDisplay.innerHTML = '';

        const header = document.createElement('div');
        header.className = 'emotion-header';
        header.innerHTML = `<strong>भावना: ${emotionNames[dominantEmotion] || dominantEmotion}</strong>`;
        this.emotionDisplay.appendChild(header);

        const intensityContainer = document.createElement('div');
        intensityContainer.className = 'emotion-intensity-container';
        intensityContainer.innerHTML = `
            <div class="emotion-label">तीव्रता:</div>
            <div class="emotion-intensity-bar">
                <div class="intensity-fill" 
                     style="width: ${Math.round(intensity * 100)}%; background-color: ${getIntensityColor(intensity)}"></div>
            </div>
            <div class="intensity-value">${getIntensityDescription(intensity)}</div>
        `;
        this.emotionDisplay.appendChild(intensityContainer);

        if (scores && Object.keys(scores).length > 0) {
            const scoresContainer = document.createElement('div');
            scoresContainer.className = 'emotion-scores-container';

            const sortedEmotions = Object.entries(scores)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);

            sortedEmotions.forEach(([emotion, score]) => {
                if (score > 0.01) {
                    const emotionBar = document.createElement('div');
                    emotionBar.className = 'emotion-score-item';
                    emotionBar.innerHTML = `
                        <div class="emotion-name">${emotionNames[emotion] || emotion}</div>
                        <div class="emotion-bar-container">
                            <div class="emotion-bar ${emotion}" 
                                 style="width: ${Math.round(score * 100)}%"></div>
                        </div>
                        <div class="emotion-value">${Math.round(score * 100)}%</div>
                    `;
                    scoresContainer.appendChild(emotionBar);
                }
            });

            this.emotionDisplay.appendChild(scoresContainer);
        }

        this.emotionDisplay.style.display = 'block';
    }
}

// Initialize EmotionHandler globally
window.emotionHandler = new EmotionHandler();

// Add this helper function at the bottom of the file (or anywhere appropriate)
function getIntensityDescription(intensity) {
    // FIX: Lower thresholds to match actual distribution
    if (intensity < 0.3) return 'सौम्य';       // Mild: 0-30% (was 35%)
    if (intensity < 0.5) return 'मध्यम';       // Moderate: 30-50% (was 60%)
    if (intensity < 0.7) return 'तीव्र';        // Strong: 50-70% (was 80%)
    return 'अत्यंत तीव्र';                      // Very strong: 70-100%
}

// Add this helper function for color-coded intensity
function getIntensityColor(intensity) {
    if (intensity < 0.3) return '#28a745';  // Green
    if (intensity < 0.5) return '#17a2b8';  // Blue
    if (intensity < 0.7) return '#fd7e14';  // Orange
    return '#dc3545';  // Red
}