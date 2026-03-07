/**
 * Request Batcher to group multiple TTS requests into batches
 */
export class RequestBatcher {
    constructor(ttsEngine, options = {}) {
        this.ttsEngine = ttsEngine;
        this.batchSize = options.batchSize || 10;
        this.maxWaitTime = options.maxWaitTime || 500; // ms
        this.queue = [];
        this.isProcessing = false;
        this.timer = null;
    }

    /**
     * Add a request to the batch
     * @param {Object} request - The request to batch
     * @returns {Promise} Promise that resolves with the result
     */
    addRequest(request) {
        return new Promise((resolve, reject) => {
            this.queue.push({
                request,
                resolve,
                reject,
                time: Date.now()
            });

            // Start the timer if not already running
            if (!this.timer) {
                this.timer = setTimeout(() => this.processQueue(), this.maxWaitTime);
            }

            // Process immediately if batch size reached
            if (this.queue.length >= this.batchSize) {
                clearTimeout(this.timer);
                this.timer = null;
                this.processQueue();
            }
        });
    }

    /**
     * Process the batch queue
     */
    async processQueue() {
        if (this.isProcessing || this.queue.length === 0) return;

        this.isProcessing = true;
        const batch = this.queue.splice(0, this.batchSize);
        
        try {
            // Create a batch request
            const batchRequest = {
                texts: batch.map(item => item.request.text),
                params: batch[0].request.params // Use params from first request for simplicity
            };
            
            // Send the batch request
            const results = await this.ttsEngine.processBatchRequest(batchRequest);
            
            // Distribute results to individual promises
            batch.forEach((item, index) => {
                if (results && results[index]) {
                    item.resolve(results[index]);
                } else {
                    item.reject(new Error('Batch processing failed for this item'));
                }
            });
        } catch (error) {
            // Reject all promises in the batch
            batch.forEach(item => item.reject(error));
        } finally {
            this.isProcessing = false;
            
            // Process next batch if queue is not empty
            if (this.queue.length > 0) {
                this.timer = setTimeout(() => this.processQueue(), 0);
            } else {
                this.timer = null;
            }
        }
    }

    /**
     * Cancel all pending requests
     */
    cancelAll() {
        clearTimeout(this.timer);
        this.timer = null;
        
        // Reject all pending requests
        this.queue.forEach(item => {
            item.reject(new Error('Request cancelled'));
        });
        
        this.queue = [];
    }
}
