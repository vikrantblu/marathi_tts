export class Logger {
    constructor(moduleName) {
        this.moduleName = moduleName;
        this.isDebug = true;  // Set to false in production
    }

    _formatMessage(message) {
        return `[${this.moduleName}][${new Date().toISOString()}] ${message}`;
    }

    debug(message, ...args) {
        if (this.isDebug) {
            console.debug(this._formatMessage(message), ...args);
        }
    }

    info(message, ...args) {
        console.info(this._formatMessage(message), ...args);
    }

    warn(message, ...args) {
        console.warn(this._formatMessage(message), ...args);
    }

    error(message, error = null) {
        console.error(this._formatMessage(message));
        if (error) {
            console.error('Error details:', error);
        }
    }

    group(label) {
        console.group(this._formatMessage(label));
    }

    groupEnd() {
        console.groupEnd();
    }
    warning(message) {
        console.warn(`[${this.context}] ${message}`);
    }
}