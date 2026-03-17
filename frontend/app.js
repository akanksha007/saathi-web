/**
 * Saathi Web Sandbox — Main Application.
 * Manages state, wires all modules together.
 * Supports: gapless audio, streaming TTS, interruption, backchannel,
 *           mic permission interstitial, live transcript, persona avatar.
 */

// ==================
// State Management
// ==================

const State = {
    SELECT: 'select',
    MIC_PERMISSION: 'mic_permission',
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

const PERSONA_AVATAR_LETTERS = {
    empathy: 'ह',
    funny: 'क',
    angry: 'अ',
    happy: 'च',
    loving: 'द',
};

const PERSONA_AVATAR_COLORS = {
    empathy: 'linear-gradient(135deg, #66BB6A, #43A047)',
    funny: 'linear-gradient(135deg, #FFB74D, #FB8C00)',
    angry: 'linear-gradient(135deg, #EF5350, #E53935)',
    happy: 'linear-gradient(135deg, #BA68C8, #8E24AA)',
    loving: 'linear-gradient(135deg, #F06292, #D81B60)',
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
const micPermissionScreen = document.getElementById('mic-permission-screen');
const conversationScreen = document.getElementById('conversation-screen');
const ambientBg = document.getElementById('ambient-bg');
const statusText = document.getElementById('status-text');
const personaLabel = document.getElementById('persona-label');
const convPersonaAvatar = document.getElementById('conv-persona-avatar');
const changePersonaBtn = document.getElementById('change-persona-btn');
const personaCards = document.querySelectorAll('.persona-card');
const allowMicBtn = document.getElementById('allow-mic-btn');
const micNote = document.querySelector('.mic-note');
const transcriptContent = document.getElementById('transcript-content');
const transcriptArea = document.getElementById('transcript-area');

// ==================
// Transcript Manager
// ==================

let thinkingBubble = null;

function addTranscriptBubble(text, role) {
    // role: 'user' | 'assistant' | 'thinking'
    const bubble = document.createElement('div');
    bubble.className = `transcript-bubble ${role}`;
    bubble.textContent = text;
    transcriptContent.appendChild(bubble);

    // Auto-scroll to bottom
    transcriptArea.scrollTop = transcriptArea.scrollHeight;

    // Keep max 20 bubbles to avoid memory issues
    while (transcriptContent.children.length > 20) {
        transcriptContent.removeChild(transcriptContent.firstChild);
    }

    return bubble;
}

function removeThinkingBubble() {
    if (thinkingBubble && thinkingBubble.parentNode) {
        thinkingBubble.parentNode.removeChild(thinkingBubble);
        thinkingBubble = null;
    }
}

function clearTranscript() {
    transcriptContent.innerHTML = '';
    thinkingBubble = null;
}

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

// ==================
// Screen Transitions
// ==================

function _fadeOutScreen(screen) {
    return new Promise(resolve => {
        screen.classList.add('fade-out');
        setTimeout(() => {
            screen.classList.remove('active', 'fade-out');
            screen.style.display = '';
            resolve();
        }, 350);
    });
}

function _fadeInScreen(screen, displayStyle) {
    screen.style.display = displayStyle || 'flex';
    screen.style.opacity = '0';
    screen.offsetHeight; // force reflow
    screen.classList.add('active');
    screen.style.opacity = '';
}

function showSelectScreen() {
    // Fade out conversation screen, fade in select screen
    conversationScreen.classList.add('fade-out');
    micPermissionScreen.classList.remove('active');
    micPermissionScreen.style.display = '';
    vadInstance.pause();
    audioPlayer.stop();
    orb.stop();
    currentState = State.SELECT;

    // Reset mic button state for next time
    allowMicBtn.textContent = '🎤 माइक Allow करें';
    allowMicBtn.classList.remove('denied');
    micNote.textContent = 'Allow पर tap करें, फिर browser permission दें';

    setTimeout(() => {
        conversationScreen.classList.remove('active', 'fade-out');
        conversationScreen.style.display = '';

        _fadeInScreen(selectScreen, 'flex');

        // Re-trigger card entry animations
        personaCards.forEach(card => {
            card.classList.remove('loading');
            card.style.animation = 'none';
            card.offsetHeight; // force reflow
            card.style.animation = '';
        });
    }, 350);
}

async function showMicPermissionScreen() {
    await _fadeOutScreen(selectScreen);
    _fadeInScreen(micPermissionScreen, 'flex');
    currentState = State.MIC_PERMISSION;
}

function showConversationScreen() {
    // Can come from either select screen or mic permission screen
    const activeScreen = micPermissionScreen.classList.contains('active')
        ? micPermissionScreen
        : selectScreen;

    activeScreen.classList.add('fade-out');

    setTimeout(() => {
        activeScreen.classList.remove('active', 'fade-out');
        activeScreen.style.display = '';

        _fadeInScreen(conversationScreen, 'flex');

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

        // Update persona label and avatar in conversation header
        personaLabel.textContent = PERSONA_LABELS[persona] || persona;
        convPersonaAvatar.textContent = PERSONA_AVATAR_LETTERS[persona] || '?';
        convPersonaAvatar.style.background = PERSONA_AVATAR_COLORS[persona] || PERSONA_AVATAR_COLORS.empathy;

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

        // Clear transcript from any previous session
        clearTranscript();

        // Small delay so user sees the loading state before transition
        await new Promise(r => setTimeout(r, 300));

        // Check if we already have mic permission
        let micGranted = false;
        try {
            const permStatus = await navigator.permissions.query({ name: 'microphone' });
            micGranted = (permStatus.state === 'granted');
        } catch (e) {
            // permissions.query not supported — we'll need to ask
        }

        if (micGranted) {
            // Already have permission — go straight to conversation
            showConversationScreen();
            setState(State.LISTENING);
            try {
                await vadInstance.initialize();
                await vadInstance.start();
            } catch (err) {
                console.error('VAD init error:', err);
                enableManualMode();
            }
        } else {
            // Show mic permission interstitial
            await showMicPermissionScreen();
        }

        // Clear loading state after transition
        card.classList.remove('loading');
    });
});

// ==================
// Mic Permission Screen
// ==================

allowMicBtn.addEventListener('click', async () => {
    allowMicBtn.textContent = '⏳ Loading...';

    try {
        await vadInstance.initialize();
        await vadInstance.start();

        // Success — transition to conversation
        showConversationScreen();
        setState(State.LISTENING);
    } catch (err) {
        console.error('Mic permission error:', err);
        // Permission denied — show helpful message
        allowMicBtn.textContent = '❌ Permission denied';
        allowMicBtn.classList.add('denied');
        micNote.textContent = 'Browser settings में जाकर mic allow करें, फिर page refresh करें।';
    }
});

// ==================
// Change Persona
// ==================

changePersonaBtn.addEventListener('click', () => {
    ws.switchPersona(currentPersona);
    clearTranscript();
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

    // Show thinking indicator in transcript
    removeThinkingBubble();
    thinkingBubble = addTranscriptBubble('सोच रहा हूँ...', 'thinking');

    audioSendTimestamp = performance.now();
    ws.sendAudio(base64Audio);

    // Safety timeout: if backend doesn't respond within 30s, reset to listening
    if (processingTimeout) clearTimeout(processingTimeout);
    processingTimeout = setTimeout(() => {
        if (currentState === State.PROCESSING) {
            console.error('⏰ Processing timeout — no response from server in 30s');
            removeThinkingBubble();
            addTranscriptBubble('कोई जवाब नहीं आया। फिर से बोलो।', 'thinking');
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

    // Remove thinking bubble on first audio
    if (message.chunk_index === 0 && message.sub_index === 0) {
        removeThinkingBubble();
    }

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

    // Remove thinking bubble on first audio
    if (message.index === 0) {
        removeThinkingBubble();
    }

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

    // Show what user said in transcript
    addTranscriptBubble(message.text, 'user');
};

ws.onResponseComplete = (message) => {
    if (processingTimeout) { clearTimeout(processingTimeout); processingTimeout = null; }
    console.log('📦 All chunks received' + (message.interrupted ? ' (interrupted)' : ''));

    // Remove any lingering thinking bubble
    removeThinkingBubble();

    // Show AI's full response in transcript
    if (message.full_text && message.full_text.trim()) {
        addTranscriptBubble(message.full_text, 'assistant');
    }

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
    removeThinkingBubble();
    statusText.textContent = message.message || 'कुछ गड़बड़ हो गई। फिर से बोलो।';
    setState(State.LISTENING);
    vadInstance.start();
};

ws.onConnectionChange = (connected) => {
    if (!connected && currentState !== State.SELECT && currentState !== State.MIC_PERMISSION) {
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
                    thinkingBubble = addTranscriptBubble('सोच रहा हूँ...', 'thinking');
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
