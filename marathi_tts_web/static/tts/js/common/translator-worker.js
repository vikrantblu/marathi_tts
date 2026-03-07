self.onmessage = function(e) {
    const { text, targetLang, elementId } = e.data;
    console.log(`Worker received: ${text} to ${targetLang} for ${elementId}`);

    // Simulate translation API call
    setTimeout(() => {
        const translations = {
            en: text,
            hi: "अनुवादित " + text,
            mr: "अनुवादित " + text
        };

        const translation = translations[targetLang] || text;

        console.log(`Worker sending: ${translation} for ${elementId}`);
        self.postMessage({ elementId, translation });
    }, 100); // Simulated delay
};