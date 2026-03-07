/**
 * Text Constants - Abbreviation maps, replacement tables, and text patterns
 * shared across JS text processing modules.
 * 
 * IMPORTANT: Check this file first before adding new text-related constants.
 */

// Abbreviation expansions for word sync display
export const ABBREVIATION_MAP = {
    'प.पू.': 'परमपूज्य',
    'श्री.': 'श्री',
    'डॉ.': 'डॉक्टर',
    'प्रा.': 'प्राध्यापक',
    'मा.': 'माननीय',
    'सौ.': 'सौभाग्यवती',
    'श्रीम.': 'श्रीमती'
};

// Text processor replacements (special chars and abbreviations)
export const TEXT_REPLACEMENTS = {
    'ॐ': 'ओम्',
    '॥': '।',
    '…': '...',
    'श्री': 'श्रीमान',
    'डॉ': 'डॉक्टर',
    'कु': 'कुमारी',
    'प्रा': 'प्राध्यापक',
    'सौ': 'सौभाग्यवती',
    'रु': 'रुपये',
    'क्र': 'क्रमांक',
    'इ': 'इत्यादी',
    'उदा': 'उदाहरण',
    'म्ह': 'म्हणजे',
    'पा': 'पान'
};

// Emphasis patterns for word sync highlighting
export const EMPHASIS_PATTERNS = [
    /^[अआइईउऊएऐओऔ]/,  // Words starting with vowels
    /[ः।॥!?]$/,         // Words ending with punctuation
    /^(म्हणजे|परंतु|तथापि|याशिवाय|किंवा|अथवा|तरीही|आणि|मात्र|त्यामुळे|म्हणूनच|शिवाय)$/,  // Important conjunctions
    /^(अति|महा|परम|सर्व|अधि|प्र|स्व|पुन|सु|दुर्|नि|वि|अभि|उप|प्रति)/,  // Important prefixes
    /^(आवश्यक|महत्त्व|विशेष|प्रमुख|तात्काळ|अत्यंत|गंभीर|महत्वपूर्ण|आधुनिक|वैशिष्ट्य)/,  // Important concept words
    /(त्व|पणा|कार|मान|वंत|कर्ता|धारक|वाला|कारी)$/,  // Words ending with specific suffixes
    /^[०-९]+$/  // Numerical values
];

// Pause patterns for word sync timing
export const PAUSE_PATTERNS = [
    /[।॥!?]$/,     // Major punctuation (longer pauses)
    /[,:]$/,        // Minor punctuation (shorter pauses)
    /^(परंतु|तथापि|म्हणून|कारण|अर्थात|तसेच|आणि|किंवा|पण|अथवा|मात्र|तरी|म्हणजेच|त्याचप्रमाणे|याव्यतिरिक्त|अन्यथा|तरीसुद्धा)$/,  // Conjunctions that require pauses
    /^(म्हणजे|जसे|तर|जर|तेव्हा|जेव्हा|तेथे|येथे|कधी|जिथे|जेथे|जिकडे|तिकडे|जोपर्यंत|तोपर्यंत)$/,  // Logical separation markers
    /^(का|काय|कसे|कोण|केव्हा|कुठे|किती|कशामुळे|कशासाठी|कोणी|कोणता|कोणती|कोणते)$/,  // Question words
    /.{12,}$/,      // Pause after long words
    /^[०-९]+$/,    // Numbers and dates
    /(पर्यंत|साठी|मुळे|करिता|विषयी|बाबत|संदर्भात|बद्दल|प्रमाणे|नुसार)$/  // Common phrase endings
];

// Pause duration rules (used in calculatePauseDuration)
export const PAUSE_DURATIONS = {
    majorPunctuation: { pattern: /[।॥!?]$/, duration: 0.8 },
    minorPunctuation: { pattern: /[,:]$/, duration: 0.4 },
    majorConjunctions: { pattern: /^(परंतु|तथापि|म्हणून|कारण|त्याचप्रमाणे|याव्यतिरिक्त)$/, duration: 0.5 },
    questionWords: { pattern: /^(का|काय|कसे|कोण|केव्हा|कुठे|किती|कशामुळे)$/, duration: 0.4 },
    phraseEndings: { pattern: /(पर्यंत|साठी|मुळे|करिता|विषयी|बाबत|संदर्भात)$/, duration: 0.3 },
    defaultPause: 0.2
};

// Valid Devanagari script pattern (for text validation)
export const DEVANAGARI_VALID_PATTERN = /^[\u0900-\u097F\s.,!?।॥]*$/;
