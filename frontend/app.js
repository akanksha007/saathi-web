/**
 * Saathi Web Sandbox — Main Application.
 * Manages state, wires all modules together.
 * Supports: gapless audio, streaming TTS, interruption, backchannel.
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
    // Fade out conversation screen, fade in select screen
    conversationScreen.classList.add('fade-out');
    vadInstance.pause();
    audioPlayer.stop();
    orb.stop();
    currentState = State.SELECT;

    setTimeout(() => {
        conversationScreen.classList.remove('active', 'fade-out');
        conversationScreen.style.display = '';

        // Show select screen at opacity 0, then animate to 1
        selectScreen.style.display = 'flex';
        selectScreen.style.opacity = '0';
        selectScreen.offsetHeight; // force reflow
        selectScreen.classList.add('active');
        selectScreen.style.opacity = '';

        // Re-trigger card entry animations
        personaCards.forEach(card => {
            card.classList.remove('loading');
            card.style.animation = 'none';
            card.offsetHeight; // force reflow
            card.style.animation = '';
        });
    }, 350);
}

function showConversationScreen() {
    // Fade out select screen, fade in conversation screen
    selectScreen.classList.add('fade-out');

    setTimeout(() => {
        selectScreen.classList.remove('active', 'fade-out');
        selectScreen.style.display = '';

        // Show conversation screen at opacity 0, then animate to 1
        conversationScreen.style.display = 'flex';
        conversationScreen.style.opacity = '0';
        conversationScreen.offsetHeight; // force reflow
        conversationScreen.classList.add('active');
        conversationScreen.style.opacity = '';

        orb.start();
    }, 350);
}

// ==================
// Persona Selection
// ==================

personaCards.forEach(card => {
    card.addEventListener('click', async () => {
        // Prevent double-tap
        if (card.classList.contains('loading')) return;

        const persona = card.dataset.persona;
        currentPersona = persona;

        // Show loading state on the tapped card
        personaCards.forEach(c => c.classList.remove('loading'));
        card.classList.add('loading');

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

        // Small delay so user sees the loading state before transition
        await new Promise(r => setTimeout(r, 300));

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

        // Clear loading state after transition
        card.classList.remove('loading');
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
    } else if (currentState === State.SPEAKING) {
        // User started speaking while AI is talking — INTERRUPT!
        console.log('⛔ User interrupting AI speech');
        _handleInterrupt();
    }
};

let processingTimeout = null;

vadInstance.onSpeechEnd = (base64Audio) => {
    // Allow speech end from both LISTENING and SPEAKING states (for interruption)
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
// Interruption Handler
// ==================

function _handleInterrupt() {
    // 1. Stop audio playback immediately
    const wasPlaying = audioPlayer.stop();

    if (wasPlaying) {
        // 2. Tell server to stop generating
        ws.interrupt();

        // 3. Clear any pending timeouts
        if (processingTimeout) {
            clearTimeout(processingTimeout);
            processingTimeout = null;
        }

        // 4. Switch to listening state so the new speech gets captured
        setState(State.LISTENING);
        orb.setAudioLevel(0.5); // Show user speech is being detected

        console.log('⛔ Interrupted — now listening for user speech');
    }
}

// ==================
// WebSocket Callbacks
// ==================

ws.onSessionStarted = (message) => {
    console.log('📋 Session:', message.persona);
};

// --- Streaming PCM TTS audio ---
ws.onTtsAudioStream = (message) => {
    // Clear processing timeout — we got audio
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }

    // Schedule PCM chunk for gapless playback
    audioPlayer.enqueuePcm(message.audio, message.chunk_index);

    // Log TTFA on first sub-chunk of first chunk
    if (message.chunk_index === 0 && message.sub_index === 0 && audioSendTimestamp) {
        const ttfa = performance.now() - audioSendTimestamp;
        console.log(`⚡ TTFA (streaming): ${(ttfa / 1000).toFixed(2)}s`);
        audioSendTimestamp = null;
    }
};

ws.onTtsChunkDone = (message) => {
    console.log(`📦 Text chunk ${message.chunk_index} complete (${message.sub_chunks} sub-chunks)`);
};

// --- Legacy MP3 fallback ---
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

// --- Backchannel audio (short fillers while thinking) ---
ws.onBackchannelAudio = (message) => {
    // Play the backchannel filler sound immediately via a separate path
    // Use the main audioPlayer — it will play before the main response chunks arrive
    audioPlayer.enqueue(message.audio, -1); // index -1 = backchannel, won't trigger onPlaybackStart
};

ws.onSttResult = (message) => {
    // Clear processing timeout — backend is working
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.log('📝 You said:', message.text);
};

ws.onResponseComplete = (message) => {
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.log('📦 All chunks received' + (message.interrupted ? ' (interrupted)' : ''));

    // Tell audioPlayer that no more chunks are coming
    audioPlayer.markResponseComplete();

    // If interrupted, the audioPlayer is already stopped and we're in LISTENING state
    if (message.interrupted) {
        // Already handled by _handleInterrupt
        return;
    }
};

ws.onInterrupted = (message) => {
    // Server acknowledged the interruption — nothing extra to do
    // Frontend already stopped playback in _handleInterrupt
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

    // Keep VAD active during speaking for interruption support!
    // Don't pause VAD — we need it to detect when user starts speaking
    vadInstance.start();
};

audioPlayer.onPlaybackComplete = () => {
    orb.setAudioLevel(0);
    // Only transition to listening if we're still in speaking state
    // (might already be in listening due to interruption)
    if (currentState === State.SPEAKING) {
        setState(State.LISTENING);
        vadInstance.start();
    }
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
