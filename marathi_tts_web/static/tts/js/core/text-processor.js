import { TEXT_REPLACEMENTS, DEVANAGARI_VALID_PATTERN } from '../constants/text-constants.js';

export class TextProcessor {
    constructor() {
        this.wordSyncEnabled = true;
        this.currentWordIndex = 0;
        this.replacements = TEXT_REPLACEMENTS;
    }

    processText(text) {
        if (!text) return {
            words: [],
            sentences: [],
            timing: []
        };

        // Clean and process text
        text = this._cleanText(text);
        text = this._normalizeText(text);
        text = this._applyReplacements(text);

        return {
            words: this.splitIntoWords(text),
            sentences: this.splitIntoSentences(text),
            timing: this.calculateWordTimings(text)
        };
    }

    _cleanText(text) {
        return text.trim()
                  .replace(/\s+/g, ' ')
                  .replace(/[^\u0900-\u097F\s।,.!?]/g, '');
    }

    _normalizeText(text) {
        return text.replace(/([।,.!?])(?=\S)/g, '$1 ')
                  .replace(/\s+/g, ' ');
    }

    _applyReplacements(text) {
        for (const [from, to] of Object.entries(this.replacements)) {
            text = text.replace(new RegExp(from, 'g'), to);
        }
        return text;
    }

    splitIntoWords(text) {
        return text.trim().split(/\s+/);
    }

    splitIntoSentences(text) {
        return text.match(/[^।?!]+[।?!]+/g) || [text];
    }

    calculateWordTimings(text) {
        const words = this.splitIntoWords(text);
        const averageWordDuration = 300; // ms
        return words.map((word, index) => ({
            word,
            start: index * averageWordDuration,
            duration: word.length * 50 // Adjust duration based on word length
        }));
    }
}
export function fix_content_structure(content) {
    if (!content) return ''; // Use the correct parameter name

    // Step 1: Protect time formats and abbreviations
    content = content
        .replace(/([०-९\d]+)\s*\.\s*([०-९\d]+)/g, '$1__TIME_DOT__$2')
        .replace(/([प-ह])\.([प-ह])\./g, '$1__DOT__$2__DOT__');

    // Step 2: Process paragraphs
    let paragraphs = content.split(/\n{2,}/).filter(p => p.trim());
    
    paragraphs = paragraphs.map(paragraph => {
        // Clean extra whitespace
        paragraph = paragraph.replace(/\s+/g, ' ').trim();
        
        // Handle existing punctuation without adding new ones
        paragraph = paragraph
            .replace(/([.!?।॥])\s*/g, '$1 ') // Keep original sentence endings
            .replace(/\s*,\s*/g, ', ')       // Fix spacing around commas
            .replace(/\s*।\s*(?=\S)/g, ' '); // Remove any automatic danda additions
        
        return paragraph.trim();
    });

    // Step 3: Join paragraphs
    content = paragraphs.join('\n\n');
    
    // Step 4: Restore protected patterns
    content = content
        .replace(/__TIME_DOT__/g, '.')
        .replace(/__DOT__/g, '.');

    // Step 5: Final cleanup
    return content
        .replace(/\n{3,}/g, '\n\n')
        .replace(/[ \t]+$/gm, '')
        .replace(/^[ \t]+/gm, '')
        .trim();
}
