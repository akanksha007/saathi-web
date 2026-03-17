/**
 * Saathi Web Sandbox — Voice Activity Detection.
 * Uses Silero VAD (@ricky0123/vad-web) for accurate speech detection.
 */

class SaathiVAD {
    constructor() {
        this.vad = null;
        this.isListening = false;
        this.onSpeechEnd = null;  // Callback: receives base64 WAV audio
        this.onSpeechStart = null;  // Callback: user started speaking
    }

    /**
     * Initialize the VAD. Must be called after a user gesture (e.g., button tap).
     */
    async initialize() {
        if (this.vad) {
            return;  // Already initialized
        }

        console.log('🎤 Initializing VAD...');

        try {
            this.vad = await vad.MicVAD.new({
                // Callback when speech starts
                onSpeechStart: () => {
                    console.log('🟢 Speech detected');
                    if (this.onSpeechStart) this.onSpeechStart();
                },

                // Callback when speech ends — receives Float32Array audio
                onSpeechEnd: (audio) => {
                    console.log('🔴 Speech ended, audio length:', audio.length);
                    if (this.onSpeechEnd) {
                        const wavBase64 = this._float32ToWavBase64(audio);
                        this.onSpeechEnd(wavBase64);
                    }
                },

                // Model settings — tuned for Hindi/Hinglish conversational speech
                positiveSpeechThreshold: 0.6,   // Lower threshold to catch softer speech (was 0.8)
                negativeSpeechThreshold: 0.35,   // Slightly lower to avoid premature cutoff (was 0.4)
                minSpeechFrames: 8,              // More frames required to avoid false triggers (was 5)
                redemptionFrames: 35,            // More patience during pauses within a sentence (was 20)
            });

            console.log('✅ VAD initialized');
        } catch (error) {
            console.error('❌ VAD initialization failed:', error);
            throw error;
        }
    }

    /**
     * Start listening for speech.
     */
    async start() {
        if (!this.vad) {
            await this.initialize();
        }
        this.vad.start();
        this.isListening = true;
        console.log('🎤 VAD listening');
    }

    /**
     * Pause listening (while AI is speaking).
     */
    pause() {
        if (this.vad) {
            this.vad.pause();
            this.isListening = false;
            console.log('⏸️ VAD paused');
        }
    }

    /**
     * Stop and destroy VAD.
     */
    destroy() {
        if (this.vad) {
            this.vad.destroy();
            this.vad = null;
            this.isListening = false;
        }
    }

    /**
     * Convert Float32Array audio to base64-encoded WAV.
     * WAV format: 16kHz, 16-bit, mono.
     */
    _float32ToWavBase64(float32Array) {
        const sampleRate = 16000;
        const numChannels = 1;
        const bitsPerSample = 16;

        // Resample if needed (Silero VAD outputs at 16kHz by default)
        const samples = float32Array;
        const numSamples = samples.length;

        // Create WAV buffer
        const bufferLength = 44 + numSamples * 2;  // 44 byte header + 16-bit samples
        const buffer = new ArrayBuffer(bufferLength);
        const view = new DataView(buffer);

        // WAV header
        this._writeString(view, 0, 'RIFF');
        view.setUint32(4, bufferLength - 8, true);
        this._writeString(view, 8, 'WAVE');
        this._writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);  // PCM format chunk size
        view.setUint16(20, 1, true);   // PCM format
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true);
        view.setUint16(32, numChannels * bitsPerSample / 8, true);
        view.setUint16(34, bitsPerSample, true);
        this._writeString(view, 36, 'data');
        view.setUint32(40, numSamples * 2, true);

        // Convert float32 samples to int16
        let offset = 44;
        for (let i = 0; i < numSamples; i++) {
            let sample = samples[i];
            // Clamp to [-1, 1]
            sample = Math.max(-1, Math.min(1, sample));
            // Convert to int16
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }

        // Convert to base64
        const uint8Array = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < uint8Array.length; i++) {
            binary += String.fromCharCode(uint8Array[i]);
        }
        return btoa(binary);
    }

    /**
     * Write a string to a DataView at the given offset.
     */
    _writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }
}
