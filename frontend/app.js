/**
 * Saathi Web Sandbox — Main Application.
 * Manages state, wires all modules together.
 */

// ==================
// State Management
// ==================

const State = {
    SELECT: 'select',
    LISTENING: 'listening',
    PROCESSING: 'processing',
    SPEAKING: 'speaking',
};

const PERSONA_LABELS = {
    empathy: 'हमदर्द दोस्त',
    funny: 'कॉमेडियन यार',
    angry: 'Uncle जी',
    happy: 'चीयरलीडर',
    loving: 'प्यारे दादाजी',
};

let currentState = State.SELECT;
let currentPersona = null;
let audioSendTimestamp = null;

// ==================
// Module Instances
// ==================

const ws = new SaathiWebSocket();
const vadInstance = new SaathiVAD();
const audioPlayer = new AudioQueue();
const orb = new LivingOrb('orb-canvas');

// ==================
// DOM Elements
// ==================

const selectScreen = document.getElementById('select-screen');
const conversationScreen = document.getElementById('conversation-screen');
const ambientBg = document.getElementById('ambient-bg');
const statusText = document.getElementById('status-text');
const personaLabel = document.getElementById('persona-label');
const changePersonaBtn = document.getElementById('change-persona-btn');
const personaCards = document.querySelectorAll('.persona-card');

// ==================
// State Transitions
// ==================

function setState(newState) {
    currentState = newState;

    // Update ambient background
    ambientBg.className = 'ambient-bg ' + newState;

    // Update orb
    orb.setState(newState);

    // Update status text
    switch (newState) {
        case State.LISTENING:
            statusText.textContent = 'सुन रहा हूँ...';
            statusText.style.color = '#888';
            break;
        case State.PROCESSING:
            statusText.textContent = 'सोच रहा हूँ...';
            statusText.style.color = '#b89520';
            break;
        case State.SPEAKING:
            statusText.textContent = 'बोल रहा हूँ...';
            statusText.style.color = '#5b9bf5';
            break;
    }
}

function showSelectScreen() {
    selectScreen.classList.add('active');
    conversationScreen.classList.remove('active');
    vadInstance.pause();
    audioPlayer.stop();
    orb.stop();
    currentState = State.SELECT;
}

function showConversationScreen() {
    selectScreen.classList.remove('active');
    conversationScreen.classList.add('active');
    orb.start();
}

// ==================
// Persona Selection
// ==================

personaCards.forEach(card => {
    card.addEventListener('click', async () => {
        const persona = card.dataset.persona;
        currentPersona = persona;

        // Update persona label
        personaLabel.textContent = PERSONA_LABELS[persona] || persona;

        // Set orb color for this persona
        orb.setPersonaColor(persona);

        // Connect WebSocket if not connected
        if (!ws.isConnected) {
            ws.connect();
            await new Promise(resolve => {
                const check = setInterval(() => {
                    if (ws.isConnected) {
                        clearInterval(check);
                        resolve();
                    }
                }, 100);
                // Timeout after 5 seconds
                setTimeout(() => { clearInterval(check); resolve(); }, 5000);
            });
        }

        // Start session
        ws.startSession(persona);

        // Show conversation screen
        showConversationScreen();
        setState(State.LISTENING);

        // Initialize VAD
        try {
            await vadInstance.initialize();
            await vadInstance.start();
        } catch (err) {
            console.error('VAD init error:', err);
            enableManualMode();
        }
    });
});

// ==================
// Change Persona
// ==================

changePersonaBtn.addEventListener('click', () => {
    ws.switchPersona(currentPersona);
    showSelectScreen();
});

// ==================
// VAD Callbacks
// ==================

vadInstance.onSpeechStart = () => {
    if (currentState === State.LISTENING) {
        orb.setAudioLevel(0.5);
    }
};

let processingTimeout = null;

vadInstance.onSpeechEnd = (base64Audio) => {
    if (currentState !== State.LISTENING) return;

    vadInstance.pause();
    orb.setAudioLevel(0);
    setState(State.PROCESSING);

    audioSendTimestamp = performance.now();
    ws.sendAudio(base64Audio);

    // Safety timeout: if backend doesn't respond within 30s, reset to listening
    if (processingTimeout) clearTimeout(processingTimeout);
    processingTimeout = setTimeout(() => {
        if (currentState === State.PROCESSING) {
            console.error('⏰ Processing timeout — no response from server in 30s');
            statusText.textContent = 'कोई जवाब नहीं आया। फिर से बोलो।';
            setState(State.LISTENING);
            vadInstance.start();
        }
    }, 30000);
};

// ==================
// WebSocket Callbacks
// ==================

ws.onSessionStarted = (message) => {
    console.log('📋 Session:', message.persona);
};

ws.onTtsAudio = (message) => {
    // Clear processing timeout — we got a response
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }

    audioPlayer.enqueue(message.audio, message.index);

    if (message.index === 0 && audioSendTimestamp) {
        const ttfa = performance.now() - audioSendTimestamp;
        console.log(`⚡ TTFA: ${(ttfa / 1000).toFixed(2)}s`);
        audioSendTimestamp = null;
    }
};

ws.onSttResult = (message) => {
    // Clear processing timeout — backend is working
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.log('📝 You said:', message.text);
};

ws.onResponseComplete = (message) => {
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.log('📦 All chunks received');
};

ws.onError = (message) => {
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.error('⚠️ Server error:', message.message);
    statusText.textContent = message.message || 'कुछ गड़बड़ हो गई। फिर से बोलो।';
    setState(State.LISTENING);
    vadInstance.start();
};

ws.onConnectionChange = (connected) => {
    if (!connected && currentState !== State.SELECT) {
        statusText.textContent = 'कनेक्ट हो रहा है...';
    }
};

// ==================
// Audio Player Callbacks
// ==================

audioPlayer.onPlaybackStart = () => {
    setState(State.SPEAKING);
    // Simulate audio level for orb during playback
    _simulateSpeakingAnimation();
};

audioPlayer.onPlaybackComplete = () => {
    orb.setAudioLevel(0);
    setState(State.LISTENING);
    vadInstance.start();
};

let speakingAnimInterval = null;

function _simulateSpeakingAnimation() {
    if (speakingAnimInterval) clearInterval(speakingAnimInterval);

    speakingAnimInterval = setInterval(() => {
        if (currentState !== State.SPEAKING) {
            clearInterval(speakingAnimInterval);
            speakingAnimInterval = null;
            orb.setAudioLevel(0);
            return;
        }
        // Simulate dynamic audio level
        const level = 0.3 + Math.random() * 0.5;
        orb.setAudioLevel(level);
    }, 80);
}

// ==================
// Manual Mode Fallback
// ==================

let manualRecording = false;
let manualMediaRecorder = null;
let manualChunks = [];

function enableManualMode() {
    console.log('🔧 Manual recording mode');
    statusText.textContent = 'बोलने के लिए टैप करें';

    const orbContainer = document.getElementById('orb-container');
    orbContainer.style.cursor = 'pointer';

    orbContainer.addEventListener('click', async () => {
        if (currentState === State.SPEAKING || currentState === State.PROCESSING) return;

        if (!manualRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: { sampleRate: 16000, channelCount: 1 }
                });
                manualMediaRecorder = new MediaRecorder(stream, {
                    mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                        ? 'audio/webm;codecs=opus'
                        : 'audio/webm'
                });
                manualChunks = [];

                manualMediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) manualChunks.push(e.data);
                };

                manualMediaRecorder.onstop = async () => {
                    const blob = new Blob(manualChunks, { type: 'audio/webm' });
                    const arrayBuffer = await blob.arrayBuffer();
                    const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

                    setState(State.PROCESSING);
                    audioSendTimestamp = performance.now();
                    ws.sendAudio(base64);
                    stream.getTracks().forEach(t => t.stop());
                };

                manualMediaRecorder.start();
                manualRecording = true;
                setState(State.LISTENING);
                orb.setAudioLevel(0.4);
                statusText.textContent = 'रोकने के लिए टैप करें...';
            } catch (err) {
                alert('माइक्रोफ़ोन एक्सेस नहीं मिला: ' + err.message);
            }
        } else {
            manualRecording = false;
            orb.setAudioLevel(0);
            if (manualMediaRecorder && manualMediaRecorder.state === 'recording') {
                manualMediaRecorder.stop();
            }
        }
    });
}

// ==================
// Page Lifecycle
// ==================

window.addEventListener('beforeunload', () => {
    ws.endSession();
    ws.disconnect();
    vadInstance.destroy();
    orb.stop();
});

// Pre-connect WebSocket
ws.connect();
