/**
 * Enhanced diff display utility for Marathi text corrections
 */
class DiffDisplayUtil {
    constructor() {
        console.log("DiffDisplay initialized");
        // Check if diff_match_patch is available
        if (typeof diff_match_patch !== 'function') {
            console.error('diff_match_patch library not loaded!');
        }
    }
    
    /**
     * Generate a visually clear HTML diff between original and corrected text
     */
    generateVisualDiff(original, corrected) {
        console.log("Generating visual diff");
        
        if (!original || !corrected) {
            return '<p>No text provided for comparison</p>';
        }
        
        try {
            // Create diff_match_patch instance
            const dmp = new diff_match_patch();
            
            // Get the differences
            const diffs = dmp.diff_main(original, corrected);
            
            // Clean up the diff for better readability
            dmp.diff_cleanupSemantic(diffs);
            
            // Generate HTML
            let html = '<div class="diff-container">';
            
            // Add the detailed diff
            html += '<div class="diff-text">';
            
            for (const diff of diffs) {
                const [type, text] = diff;
                const processedText = this.processTextForDisplay(text);
                
                if (type === 0) { // DIFF_EQUAL
                    html += `<span class="diff-equal">${processedText}</span>`;
                } else if (type === 1) { // DIFF_INSERT
                    html += `<span class="diff-added">${processedText}</span>`;
                } else if (type === -1) { // DIFF_DELETE
                    html += `<span class="diff-removed">${processedText}</span>`;
                }
            }
            
            html += '</div></div>';
            
            return html;
        } catch (error) {
            console.error('Error generating diff:', error);
            // Fallback to simple diff
            return this.generateSimpleDiff(original, corrected);
        }
    }
    
    /**
     * Process text to make spaces visible
     */
    processTextForDisplay(text) {
        // Escape HTML entities
        let processed = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
        
        // Make spaces visible with a special character
        processed = processed.replace(/ /g, '<span class="space-marker">·</span>');
        
        return processed;
    }
    
    /**
     * Generate a simple side-by-side diff as fallback
     */
    generateSimpleDiff(original, corrected) {
        return `
            <div class="simple-diff">
                <div class="diff-original">
                    <h6>मूळ मजकूर (Original):</h6>
                    <pre>${this.escapeHtml(original)}</pre>
                </div>
                <div class="diff-corrected">
                    <h6>सुधारित मजकूर (Corrected):</h6>
                    <pre>${this.escapeHtml(corrected)}</pre>
                </div>
            </div>
        `;
    }
    
    /**
     * Escape HTML characters
     */
    escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Create a global instance
window.DiffDisplay = new DiffDisplayUtil();
console.log("DiffDisplay utility loaded globally");