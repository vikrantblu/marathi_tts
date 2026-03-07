/**
 * stt-modi-tabs.js
 * Handles the Speech-to-Text and Script Converter tabs on the TTS home page.
 */

const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content ?? '';

// ── Tab switching helpers ────────────────────────────────────────────────────
const ALL_SECTION_IDS = [
    'textInputSection',
    'urlInputSection',
    'imageInputSection',
    'pdfInputSection',
    'sttInputSection',
    'modiInputSection',
    'stotraInputSection',
];

const ALL_BTN_IDS = [
    'textInputBtn',
    'urlInputBtn',
    'imageInputBtn',
    'pdfInputBtn',
    'sttInputBtn',
    'modiInputBtn',
    'stotraInputBtn',
];

function showSection(visibleId, activeBtnId) {
    ALL_SECTION_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', id !== visibleId);
    });
    ALL_BTN_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', id === activeBtnId);
    });
}

// ── STT Tab ──────────────────────────────────────────────────────────────────

let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

function setupSttTab() {
    const sttInputBtn     = document.getElementById('sttInputBtn');
    const sttFileUpload   = document.getElementById('sttFileUpload');
    const sttTranscribeBtn= document.getElementById('sttTranscribeBtn');
    const sttRecordBtn    = document.getElementById('sttRecordBtn');
    const sttRecordLabel  = document.getElementById('sttRecordLabel');
    const sttTranscript   = document.getElementById('sttTranscriptArea');
    const sttSendBtn      = document.getElementById('sttSendToTtsBtn');
    const sttStatus       = document.getElementById('sttStatusText');
    const langSelect      = document.getElementById('sttLanguageSelect');

    if (!sttInputBtn) return;

    sttInputBtn.addEventListener('click', () => showSection('sttInputSection', 'sttInputBtn'));

    // Enable transcribe button when file chosen
    sttFileUpload?.addEventListener('change', () => {
        if (sttTranscribeBtn) sttTranscribeBtn.disabled = !sttFileUpload.files?.length;
    });

    // File transcription
    sttTranscribeBtn?.addEventListener('click', async () => {
        const file = sttFileUpload?.files?.[0];
        if (!file) return;

        sttTranscribeBtn.disabled = true;
        if (sttStatus) sttStatus.textContent = 'Transcribing…';

        const formData = new FormData();
        formData.append('audio', file);
        formData.append('language', langSelect?.value ?? 'mr-IN');

        try {
            const resp = await fetch('/marathi_tts/tts/api/transcribe-audio/', {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN },
                body: formData,
            });
            const data = await resp.json();
            if (data.success) {
                if (sttTranscript) sttTranscript.value = data.transcript;
                if (sttSendBtn) sttSendBtn.disabled = !data.transcript;
                if (sttStatus) sttStatus.textContent = `Engine: ${data.engine} ✓`;
            } else {
                if (sttStatus) sttStatus.textContent = `Error: ${data.error}`;
            }
        } catch (err) {
            if (sttStatus) sttStatus.textContent = `Network error: ${err.message}`;
        } finally {
            sttTranscribeBtn.disabled = false;
        }
    });

    // Live recording via MediaRecorder + Web Speech API fallback
    sttRecordBtn?.addEventListener('click', async () => {
        if (isRecording) {
            // Stop recording
            mediaRecorder?.stop();
            isRecording = false;
            if (sttRecordLabel) sttRecordLabel.textContent = 'थेट रेकॉर्ड करा';
            return;
        }

        // Try Web Speech API first (no server round-trip needed)
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognizer = new SR();
            recognizer.lang = langSelect?.value ?? 'mr-IN';
            recognizer.continuous = false;
            recognizer.interimResults = true;
            recognizer.maxAlternatives = 1;

            recognizer.onstart = () => {
                isRecording = true;
                if (sttRecordLabel) sttRecordLabel.textContent = '⏹ थांबवा';
                if (sttStatus) sttStatus.textContent = 'Listening…';
            };
            recognizer.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(r => r[0].transcript)
                    .join('');
                if (sttTranscript) sttTranscript.value = transcript;
                if (sttSendBtn) sttSendBtn.disabled = !transcript;
            };
            recognizer.onend = () => {
                isRecording = false;
                if (sttRecordLabel) sttRecordLabel.textContent = 'थेट रेकॉर्ड करा';
                if (sttStatus) sttStatus.textContent = 'Done ✓';
            };
            recognizer.onerror = (e) => {
                isRecording = false;
                if (sttRecordLabel) sttRecordLabel.textContent = 'थेट रेकॉर्ड करा';
                if (sttStatus) sttStatus.textContent = `Error: ${e.error}`;
            };

            try {
                recognizer.start();
                // Allow click to stop
                sttRecordBtn._recognizer = recognizer;
                sttRecordBtn.addEventListener('click', () => recognizer.stop(), { once: true });
            } catch (err) {
                if (sttStatus) sttStatus.textContent = `Could not start: ${err.message}`;
            }
            return;
        }

        // Fallback: MediaRecorder
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recordedChunks = [];
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => { if (e.data.size) recordedChunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(recordedChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', blob, 'recording.webm');
                formData.append('language', langSelect?.value ?? 'mr-IN');

                if (sttStatus) sttStatus.textContent = 'Transcribing recording…';
                try {
                    const resp = await fetch('/marathi_tts/tts/api/transcribe-audio/', {
                        method: 'POST',
                        headers: { 'X-CSRFToken': CSRF_TOKEN },
                        body: formData,
                    });
                    const data = await resp.json();
                    if (data.success) {
                        if (sttTranscript) sttTranscript.value = data.transcript;
                        if (sttSendBtn) sttSendBtn.disabled = !data.transcript;
                        if (sttStatus) sttStatus.textContent = `Engine: ${data.engine} ✓`;
                    } else {
                        if (sttStatus) sttStatus.textContent = `Error: ${data.error}`;
                    }
                } catch (err) {
                    if (sttStatus) sttStatus.textContent = `Network error: ${err.message}`;
                }
            };
            mediaRecorder.start();
            isRecording = true;
            if (sttRecordLabel) sttRecordLabel.textContent = '⏹ थांबवा';
            if (sttStatus) sttStatus.textContent = 'Recording…';
        } catch (err) {
            if (sttStatus) sttStatus.textContent = `Microphone error: ${err.message}`;
        }
    });

    // Send transcript to TTS textarea
    sttSendBtn?.addEventListener('click', () => {
        const text = sttTranscript?.value ?? '';
        if (!text.trim()) return;
        const ttsArea = document.getElementById('marathiText');
        if (ttsArea) ttsArea.value = text;
        showSection('textInputSection', 'textInputBtn');
        // Trigger word count update if handler exists
        ttsArea?.dispatchEvent(new Event('input'));
    });
}


// ── Script Converter (Modi/IAST/Brahmi) Tab ──────────────────────────────────

const MODI_MODE_HINTS = {
    'modi_to_devanagari' : 'मोडी लिपीतील मजकूर देवनागरीत रूपांतरित करा',
    'devanagari_to_iast' : 'देवनागरी मजकूर IAST Roman लिपीत रूपांतरित करा',
    'iast_to_devanagari' : 'IAST Roman मजकूर देवनागरीत रूपांतरित करा',
    'brahmi_to_devanagari': 'ब्राह्मी लिपीतील मजकूर देवनागरीत रूपांतरित करा',
};

function setupModiTab() {
    const modiInputBtn   = document.getElementById('modiInputBtn');
    const modiModeSelect = document.getElementById('modiModeSelect');
    const modiModeHint   = document.getElementById('modiModeHint');
    const modiInputArea  = document.getElementById('modiInputArea');
    const modiConvertBtn = document.getElementById('modiConvertBtn');
    const modiOutputArea = document.getElementById('modiOutputArea');
    const modiSendBtn    = document.getElementById('modiSendToTtsBtn');
    const modiStatus     = document.getElementById('modiStatusText');

    if (!modiInputBtn) return;

    modiInputBtn.addEventListener('click', () => showSection('modiInputSection', 'modiInputBtn'));

    modiModeSelect?.addEventListener('change', () => {
        if (modiModeHint)
            modiModeHint.textContent = MODI_MODE_HINTS[modiModeSelect.value] ?? '';
    });

    modiConvertBtn?.addEventListener('click', async () => {
        const text = modiInputArea?.value?.trim() ?? '';
        if (!text) return;

        modiConvertBtn.disabled = true;
        if (modiStatus) modiStatus.textContent = 'Converting…';

        try {
            const resp = await fetch('/marathi_tts/tts/api/convert-script/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN,
                },
                body: JSON.stringify({
                    text,
                    mode: modiModeSelect?.value ?? 'modi_to_devanagari',
                }),
            });
            const data = await resp.json();
            if (data.success) {
                if (modiOutputArea) modiOutputArea.value = data.converted;
                if (modiSendBtn) modiSendBtn.disabled = !data.converted;
                if (modiStatus) modiStatus.textContent = `✓ (${data.output_length} chars)`;
            } else {
                if (modiStatus) modiStatus.textContent = `Error: ${data.error}`;
            }
        } catch (err) {
            if (modiStatus) modiStatus.textContent = `Network error: ${err.message}`;
        } finally {
            modiConvertBtn.disabled = false;
        }
    });

    modiSendBtn?.addEventListener('click', () => {
        const text = modiOutputArea?.value ?? '';
        if (!text.trim()) return;
        const ttsArea = document.getElementById('marathiText');
        if (ttsArea) ttsArea.value = text;
        showSection('textInputSection', 'textInputBtn');
        ttsArea?.dispatchEvent(new Event('input'));
    });
}


// ── Stotra Library Tab ───────────────────────────────────────────────────────

let stotraCache = [];
let currentDeity = 'all';

function setupStotraTab() {
    const stotraInputBtn  = document.getElementById('stotraInputBtn');
    const stotraSearch    = document.getElementById('stotraSearch');
    const stotraList      = document.getElementById('stotraList');
    const stotraDetail    = document.getElementById('stotraDetailSection');
    const stotraTitle     = document.getElementById('stotraDetailTitle');
    const stotraDesc      = document.getElementById('stotraDetailDesc');
    const stotraTextArea  = document.getElementById('stotraTextArea');
    const stotraSendBtn   = document.getElementById('stotraSendToTtsBtn');
    const stotraBackBtn   = document.getElementById('stotraBackBtn');
    const deityChipEls    = document.querySelectorAll('.stotra-chip');

    if (!stotraInputBtn) return;

    stotraInputBtn.addEventListener('click', () => {
        showSection('stotraInputSection', 'stotraInputBtn');
        if (stotraCache.length === 0) loadStotras();
    });

    async function loadStotras(deity, q) {
        const params = new URLSearchParams();
        if (deity && deity !== 'all') params.set('deity', deity);
        if (q) params.set('q', q);
        try {
            const resp = await fetch(`/marathi_tts/tts/api/stotras/?${params}`);
            const data = await resp.json();
            if (data.success) {
                stotraCache = data.stotras;
                renderList(data.stotras);
            }
        } catch (err) {
            if (stotraList) stotraList.innerHTML = `<div class="text-center text-danger py-3">Error: ${err.message}</div>`;
        }
    }

    function renderList(stotras) {
        if (!stotraList) return;
        if (stotras.length === 0) {
            stotraList.innerHTML = '<div class="text-center text-muted py-3">कोणतेही स्तोत्र सापडले नाही</div>';
            return;
        }
        stotraList.innerHTML = stotras.map(s => `
            <div class="stotra-item card mb-2 p-2" style="cursor:pointer" data-id="${s.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <strong>${s.name}</strong>
                    <span class="badge bg-secondary">${s.language}</span>
                </div>
                <small class="text-muted">${s.deity} · ${s.source || ''}</small>
            </div>
        `).join('');

        stotraList.querySelectorAll('.stotra-item').forEach(el => {
            el.addEventListener('click', () => openStotra(parseInt(el.dataset.id)));
        });
    }

    async function openStotra(id) {
        try {
            const resp = await fetch(`/marathi_tts/tts/api/stotras/${id}/`);
            const data = await resp.json();
            if (data.success) {
                const s = data.stotra;
                if (stotraTitle) stotraTitle.textContent = s.name;
                if (stotraDesc) stotraDesc.textContent = `${s.deity} · ${s.meter || ''} · ${s.source || ''}`;
                if (stotraTextArea) stotraTextArea.value = s.text;
                if (stotraDetail) stotraDetail.classList.remove('hidden');
                if (stotraList) stotraList.style.display = 'none';
            }
        } catch (err) {
            console.error('Stotra load error:', err);
        }
    }

    stotraBackBtn?.addEventListener('click', () => {
        if (stotraDetail) stotraDetail.classList.add('hidden');
        if (stotraList) stotraList.style.display = '';
    });

    stotraSendBtn?.addEventListener('click', () => {
        const text = stotraTextArea?.value ?? '';
        if (!text.trim()) return;
        const ttsArea = document.getElementById('marathiText');
        if (ttsArea) ttsArea.value = text;
        // Enable verse mode for stotras
        const verseCheck = document.getElementById('verseModeCheckbox');
        if (verseCheck) verseCheck.checked = true;
        showSection('textInputSection', 'textInputBtn');
        ttsArea?.dispatchEvent(new Event('input'));
    });

    deityChipEls.forEach(chip => {
        chip.addEventListener('click', () => {
            deityChipEls.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentDeity = chip.dataset.deity;
            loadStotras(currentDeity, stotraSearch?.value?.trim());
        });
    });

    let searchTimeout;
    stotraSearch?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadStotras(currentDeity, stotraSearch.value.trim());
        }, 300);
    });
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setupSttTab();
    setupModiTab();
    setupStotraTab();
});
