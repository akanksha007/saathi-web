/**
 * Saathi Web Sandbox — WebSocket Client.
 * Handles communication between browser and backend.
 */

class SaathiWebSocket {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
        this.userId = this._getOrCreateUserId();

        // Message handlers (set by app.js)
        this.onSessionStarted = null;
        this.onSttResult = null;
        this.onTtsAudio = null;
        this.onTtsAudioStream = null;
        this.onTtsChunkDone = null;
        this.onBackchannelAudio = null;
        this.onInterrupted = null;
        this.onResponseComplete = null;
        this.onCrisisDetected = null;
        this.onError = null;
        this.onConnectionChange = null;
    }

    /**
     * Get or create a persistent anonymous user ID.
     */
    _getOrCreateUserId() {
        let id = localStorage.getItem('saathi_user_id');
        if (!id) {
            id = 'user_' + crypto.randomUUID();
            localStorage.setItem('saathi_user_id', id);
        }
        return id;
    }

    /**
     * Get the WebSocket URL based on current page location.
     */
    _getWsUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws`;
    }

    /**
     * Connect to the WebSocket server.
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        const url = this._getWsUrl();
        console.log('🔗 Connecting to:', url);

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            if (this.onConnectionChange) this.onConnectionChange(true);
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this._handleMessage(message);
        };

        this.ws.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            this.isConnected = false;
            if (this.onConnectionChange) this.onConnectionChange(false);
            this._tryReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
    }

    /**
     * Handle incoming messages from server.
     */
    _handleMessage(message) {
        switch (message.type) {
            case 'session_started':
                if (this.onSessionStarted) this.onSessionStarted(message);
                break;
            case 'stt_result':
                console.log('📝 STT:', message.text);
                if (this.onSttResult) this.onSttResult(message);
                break;
            case 'tts_audio':
                // Legacy MP3 chunk (fallback)
                if (this.onTtsAudio) this.onTtsAudio(message);
                break;
            case 'tts_audio_stream':
                // Streaming PCM audio sub-chunk
                if (this.onTtsAudioStream) this.onTtsAudioStream(message);
                break;
            case 'tts_chunk_done':
                // A text chunk's TTS streaming is complete
                if (this.onTtsChunkDone) this.onTtsChunkDone(message);
                break;
            case 'backchannel_audio':
                // Short filler audio ("hmm", "achha") while thinking
                console.log('💬 Backchannel:', message.text);
                if (this.onBackchannelAudio) this.onBackchannelAudio(message);
                break;
            case 'crisis_detected':
                // Crisis/safety keywords detected — show helplines
                console.log('🚨 Crisis detected:', message.severity);
                if (this.onCrisisDetected) this.onCrisisDetected(message);
                break;
            case 'interrupted':
                // Server acknowledged interruption
                console.log('⛔ Interruption acknowledged');
                if (this.onInterrupted) this.onInterrupted(message);
                break;
            case 'response_complete':
                console.log(`✅ Response complete: ${message.chunks} chunks, ${message.total_time?.toFixed(2)}s${message.interrupted ? ' (interrupted)' : ''}`);
                if (this.onResponseComplete) this.onResponseComplete(message);
                break;
            case 'error':
                console.error('⚠️ Server error:', message.message);
                if (this.onError) this.onError(message);
                break;
            case 'mood_saved':
                console.log('😊 Mood saved:', message.timing, message.mood);
                break;
            case 'pong':
                break;
            default:
                console.log('Unknown message:', message);
        }
    }

    /**
     * Try to reconnect after disconnect.
     */
    _tryReconnect() {
        if (this.reconnectAttempts >= this.maxReconnects) {
            console.error('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(2000 * this.reconnectAttempts, 10000);
        console.log(`🔄 Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempts})`);

        setTimeout(() => this.connect(), delay);
    }

    /**
     * Send a message to the server.
     */
    send(type, data = {}) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }
        this.ws.send(JSON.stringify({ type, ...data }));
    }

    /**
     * Start a new session with selected persona.
     */
    startSession(persona, token) {
        const payload = { persona, user_id: this.userId };
        if (token) payload.token = token;
        this.send('start_session', payload);
    }

    /**
     * Send a mood check-in.
     */
    sendMoodCheckin(mood, timing) {
        this.send('mood_checkin', { mood, timing });
    }

    /**
     * Send recorded audio to server.
     */
    sendAudio(base64Audio) {
        this.send('audio_data', { audio: base64Audio });
    }

    /**
     * Switch to a different persona.
     */
    switchPersona(persona) {
        this.send('switch_persona', { persona });
    }

    /**
     * Send interrupt signal — user started speaking while AI was talking.
     */
    interrupt() {
        this.send('interrupt');
    }

    /**
     * End the current session.
     */
    endSession() {
        this.send('end_session');
    }

    /**
     * Disconnect WebSocket.
     */
    disconnect() {
        if (this.ws) {
            this.maxReconnects = 0;  // Prevent auto-reconnect
            this.ws.close();
        }
    }
}
