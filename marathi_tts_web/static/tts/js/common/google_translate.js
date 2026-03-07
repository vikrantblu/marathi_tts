// FILE: google_translate.js

document.addEventListener('DOMContentLoaded', function() {
    const translateElement = document.getElementById('google_translate_element');
    const translateCombo = translateElement.querySelector('.goog-te-combo');

    // Monitor for the appearance of the Google Translate header
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList.contains('goog-te-banner-frame')) {
                        translateCombo.classList.add('hide-dropdown');
                    }
                });
            }
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Ensure the dropdown is visible initially
    translateCombo.classList.remove('hide-dropdown');
    
    // Wait for Google Translate to initialize
    if (window.google && google.translate) {
        // Force retranslation of elements
        const elements = document.querySelectorAll('[data-translate="true"]');
        elements.forEach(element => {
            const text = element.textContent;
            element.textContent = text;
        });
    }

    // Force initial translation state
    const translateElements = document.querySelectorAll('[data-translate="true"]');
    translateElements.forEach(element => {
        if (!element.hasAttribute('translated')) {
            element.setAttribute('original-text', element.textContent);
        }
    });
});

function googleTranslateElementInit() {
    new google.translate.TranslateElement({
        pageLanguage: 'en',
        includedLanguages: 'en,hi,mr',
        layout: google.translate.TranslateElement.InlineLayout.SIMPLE,
        autoDisplay: true,
        multilanguagePage: true,
    }, 'google_translate_element');

    // Initialize translation handling
    if (document.readyState === 'complete') {
        handleTranslation();
    } else {
        window.addEventListener('load', handleTranslation);
    }
}

function handleTranslation() {
    // Create translation observer
    const observer = new MutationObserver((mutations) => {
        if (document.querySelector('.goog-te-banner-frame')) {
            document.body.classList.add('translating');
            
            // Force retranslation of all elements
            const translateElements = document.querySelectorAll('td, th, h2, .tab');
            translateElements.forEach(element => {
                if (!element.hasAttribute('translated')) {
                    // Store original text
                    if (!element.getAttribute('data-original')) {
                        element.setAttribute('data-original', element.textContent);
                    }
                    
                    // Force retranslation
                    const originalText = element.getAttribute('data-original');
                    element.textContent = originalText;
                    element.setAttribute('translated', 'true');
                }
            });

            // Check translation completion with longer timeout
            setTimeout(() => {
                document.body.classList.remove('translating');
                document.body.classList.add('translated');
                
                // Verify translation completion
                translateElements.forEach(element => {
                    if (element.textContent === element.getAttribute('data-original')) {
                        // If text hasn't changed, force retranslation
                        element.textContent = element.getAttribute('data-original');
                    }
                });
            }, 2000);
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        characterData: true
    });
}