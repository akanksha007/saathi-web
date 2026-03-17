/**
 * Saathi Web Sandbox — Gapless Audio Playback with Web Audio API.
 * Uses AudioContext to decode MP3 chunks into AudioBuffers and schedule
 * them back-to-back with sample-accurate timing — no gaps between chunks.
 * Also supports raw PCM streaming for even lower latency.
 */

class AudioQueue {
    constructor() {
        this.audioContext = null;
        this.queue = [];              // Pending chunks waiting to be decoded
        this.isPlaying = false;
        this.nextStartTime = 0;       // When the next buffer should start (AudioContext time)
        this.currentSource = null;    // Currently playing AudioBufferSourceNode
        this.activeSources = [];      // All scheduled sources (for stop/interrupt)
        this.responseComplete = false; // Whether server has sent all chunks
        this.scheduledCount = 0;       // Number of chunks scheduled so far
        this.totalScheduled = 0;       // Total buffers scheduled for this turn
        this.onPlaybackStart = null;   // Callback when first chunk starts playing
        this.onPlaybackComplete = null; // Callback when all chunks finished
        this.onInterrupted = null;     // Callback when playback is interrupted by user

        // PCM streaming support
        this.pcmBuffer = [];           // Raw PCM chunks waiting to be played
        this.pcmSourceNode = null;     // ScriptProcessorNode for PCM playback
        this.pcmReadPos = 0;           // Read position in current PCM buffer
        this.pcmCurrentChunk = null;   // Current PCM chunk being read
        this.isPcmMode = false;        // Whether we're in PCM streaming mode
    }

    /**
     * Ensure AudioContext is initialized (must happen after user gesture).
     */
    _ensureContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 24000,  // OpenAI TTS outputs 24kHz
            });
        }
        // Resume if suspended (browser autoplay policy)
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        return this.audioContext;
    }

    /**
     * Pre-initialize AudioContext early (call after user gesture like persona selection).
     * This avoids ~20-50ms lazy creation delay when first audio arrives.
     */
    warmup() {
        this._ensureContext();
        console.log('🔊 AudioContext pre-initialized, state:', this.audioContext.state);
    }

    /**
     * Add an MP3 audio chunk to the queue for gapless playback.
     * @param {string} base64Mp3 - Base64 encoded MP3 data.
     * @param {number} index - Chunk index (0 = first).
     */
    enqueue(base64Mp3, index) {
        const ctx = this._ensureContext();

        // Decode base64 to ArrayBuffer
        const binaryString = atob(base64Mp3);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // Decode MP3 to AudioBuffer, then schedule
        ctx.decodeAudioData(bytes.buffer.slice(0))
            .then(audioBuffer => {
                this._scheduleBuffer(audioBuffer, index);
            })
            .catch(err => {
                console.error('Audio decode error for chunk', index, ':', err);
                // Skip this chunk and continue
                this._checkCompletion();
            });
    }

    /**
     * Add raw PCM audio data for streaming playback.
     * @param {string} base64Pcm - Base64 encoded PCM data (24kHz, 16-bit, mono).
     * @param {number} index - Chunk index.
     */
    enqueuePcm(base64Pcm, index) {
        const ctx = this._ensureContext();

        // Decode base64 to Int16Array
        const binaryString = atob(base64Pcm);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Data = new Int16Array(bytes.buffer);

        // Convert Int16 to Float32 for Web Audio API
        const float32Data = new Float32Array(int16Data.length);
        for (let i = 0; i < int16Data.length; i++) {
            float32Data[i] = int16Data[i] / 32768.0;
        }

        // Create AudioBuffer from PCM data
        const audioBuffer = ctx.createBuffer(1, float32Data.length, 24000);
        audioBuffer.getChannelData(0).set(float32Data);

        this._scheduleBuffer(audioBuffer, index);
    }

    /**
     * Schedule an AudioBuffer for gapless playback.
     * Uses AudioContext's precise timing to chain buffers without gaps.
     * @param {AudioBuffer} audioBuffer - Decoded audio data.
     * @param {number} index - Chunk index (0+ = response audio, -1 = backchannel).
     */
    _scheduleBuffer(audioBuffer, index) {
        const ctx = this._ensureContext();
        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);

        // Calculate when this buffer should start
        const now = ctx.currentTime;
        if (!this.isPlaying || this.nextStartTime < now) {
            // First chunk or we've fallen behind — start immediately
            // Add tiny offset to avoid clicking
            this.nextStartTime = now + 0.005;
        }

        const startTime = this.nextStartTime;
        source.start(startTime);

        // Next buffer starts exactly when this one ends
        this.nextStartTime = startTime + audioBuffer.duration;

        // Track this source for interruption support
        const isBackchannel = (index < 0);
        this.activeSources.push({ source, startTime, endTime: this.nextStartTime, isBackchannel });

        // Notify on first real (non-backchannel) chunk that starts playback
        if (!isBackchannel && !this.isPlaying) {
            this.isPlaying = true;
            this.responseComplete = false;
            if (this.onPlaybackStart) {
                this.onPlaybackStart();
            }
        }

        if (!isBackchannel) {
            this.totalScheduled++;
        }

        // When this source ends, check if we're done
        source.onended = () => {
            // Remove from active sources
            this.activeSources = this.activeSources.filter(s => s.source !== source);
            this._checkCompletion();
        };
    }

    /**
     * Check if all playback is complete.
     */
    _checkCompletion() {
        // Only consider non-backchannel sources for completion
        const realSources = this.activeSources.filter(s => !s.isBackchannel);
        if (this.responseComplete && realSources.length === 0 && this.totalScheduled > 0) {
            this.isPlaying = false;
            this.totalScheduled = 0;
            this.nextStartTime = 0;
            if (this.onPlaybackComplete) {
                this.onPlaybackComplete();
            }
        }
    }

    /**
     * Mark that the server has sent all chunks for this turn.
     * Playback complete callback will fire after last chunk finishes playing.
     */
    markResponseComplete() {
        this.responseComplete = true;
        // If nothing was scheduled (edge case), fire completion immediately
        if (this.activeSources.length === 0 && this.totalScheduled === 0) {
            if (this.onPlaybackComplete) {
                this.onPlaybackComplete();
            }
        }
    }

    /**
     * Stop all playback immediately and clear the queue.
     * Used for interruption support — user starts speaking while AI is talking.
     * @returns {boolean} Whether playback was actually interrupted (was playing).
     */
    stop() {
        const wasPlaying = this.isPlaying;

        // Stop all scheduled sources immediately
        for (const { source } of this.activeSources) {
            try {
                source.stop();
            } catch (e) {
                // Source may have already ended
            }
        }

        this.activeSources = [];
        this.queue = [];
        this.isPlaying = false;
        this.nextStartTime = 0;
        this.responseComplete = false;
        this.totalScheduled = 0;

        // Stop PCM streaming if active
        if (this.pcmSourceNode) {
            this.pcmSourceNode.disconnect();
            this.pcmSourceNode = null;
        }
        this.pcmBuffer = [];
        this.pcmCurrentChunk = null;
        this.pcmReadPos = 0;
        this.isPcmMode = false;

        return wasPlaying;
    }

    /**
     * Get the current playback position relative to scheduled audio.
     * Useful for orb animation sync.
     */
    getPlaybackProgress() {
        if (!this.isPlaying || !this.audioContext) return 0;
        const now = this.audioContext.currentTime;
        const firstStart = this.activeSources.length > 0 ? this.activeSources[0].startTime : now;
        const lastEnd = this.nextStartTime;
        const totalDuration = lastEnd - firstStart;
        if (totalDuration <= 0) return 0;
        return Math.min(1, (now - firstStart) / totalDuration);
    }

    /**
     * Check if audio is currently being played.
     */
    get playing() {
        return this.isPlaying;
    }
}
