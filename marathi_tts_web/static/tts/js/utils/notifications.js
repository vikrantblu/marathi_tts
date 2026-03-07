// Lightweight custom toast notification system.
// Replaces Notyf to avoid blank / stuck toast issues.
let _instance = null;

class SimpleToast {
    constructor() {
        this.container = document.createElement('div');
        this.container.id = 'simpleToastContainer';
        Object.assign(this.container.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: '99999',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            pointerEvents: 'none'
        });
        document.body.appendChild(this.container);
    }

    _show(message, type = 'success') {
        // Accept both string and {message, ...} object
        if (message && typeof message === 'object') {
            message = message.message || '';
        }
        if (!message) return;

        const toast = document.createElement('div');
        Object.assign(toast.style, {
            padding: '12px 36px 12px 16px',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '14px',
            fontFamily: 'sans-serif',
            boxShadow: '0 4px 12px rgba(0,0,0,0.18)',
            pointerEvents: 'auto',
            opacity: '0',
            transform: 'translateX(30px)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            cursor: 'pointer',
            maxWidth: '340px',
            wordWrap: 'break-word',
            position: 'relative',
            background: type === 'error' ? '#dc3545' : type === 'info' ? '#17a2b8' : '#28a745'
        });
        toast.textContent = message;

        // Close button
        const close = document.createElement('span');
        close.innerHTML = '&times;';
        Object.assign(close.style, {
            position: 'absolute',
            top: '6px',
            right: '10px',
            fontSize: '18px',
            fontWeight: 'bold',
            cursor: 'pointer',
            lineHeight: '1'
        });
        close.addEventListener('click', (e) => {
            e.stopPropagation();
            this._dismiss(toast);
        });
        toast.appendChild(close);

        // Click anywhere on toast to dismiss
        toast.addEventListener('click', () => this._dismiss(toast));

        this.container.appendChild(toast);

        // Trigger slide-in animation
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });

        // Auto-dismiss after 4 seconds
        const timer = setTimeout(() => this._dismiss(toast), 4000);
        toast._dismissTimer = timer;
    }

    _dismiss(toast) {
        if (!toast || !toast.parentNode) return;
        clearTimeout(toast._dismissTimer);
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 350);
    }

    success(msg) { this._show(msg, 'success'); }
    error(msg)   { this._show(msg, 'error'); }
    open(opts)   { this._show(opts?.message || '', opts?.type || 'success'); }
}

function getNotyf() {
    if (!_instance) {
        _instance = new SimpleToast();
    }
    return _instance;
}

export { getNotyf };

export class Notifications {
    constructor() {
        this.toast = getNotyf();
    }

    success(message) { this.toast.success(message); }
    error(message)   { this.toast.error(message); }
    info(message)    { this.toast._show(message, 'info'); }
}