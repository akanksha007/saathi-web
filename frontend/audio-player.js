/**
 * Saathi Web Sandbox — Audio Playback Queue.
 * Receives MP3 audio chunks and plays them sequentially without gaps.
 */

class AudioQueue {
    constructor() {
        this.queue = [];
        this.isPlaying = false;
        this.currentAudio = null;
        this.onPlaybackStart = null;  // Callback when first chunk starts playing
        this.onPlaybackComplete = null;  // Callback when all chunks finished
    }

    /**
     * Add an audio chunk to the queue.
     * @param {string} base64Mp3 - Base64 encoded MP3 data.
     * @param {number} index - Chunk index (0 = first).
     */
    enqueue(base64Mp3, index) {
        // Decode base64 to blob
        const binaryString = atob(base64Mp3);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);

        this.queue.push({ url, index });

        // Start playing if not already
        if (!this.isPlaying) {
            this._playNext();
        }
    }

    /**
     * Play the next chunk in the queue.
     */
    _playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            this.currentAudio = null;
            if (this.onPlaybackComplete) {
                this.onPlaybackComplete();
            }
            return;
        }

        this.isPlaying = true;
        const { url, index } = this.queue.shift();

        // Notify on first chunk
        if (index === 0 && this.onPlaybackStart) {
            this.onPlaybackStart();
        }

        const audio = new Audio(url);
        this.currentAudio = audio;

        audio.onended = () => {
            URL.revokeObjectURL(url);
            this._playNext();
        };

        audio.onerror = (e) => {
            console.error('Audio playback error:', e);
            URL.revokeObjectURL(url);
            this._playNext();
        };

        audio.play().catch(err => {
            console.error('Audio play failed:', err);
            URL.revokeObjectURL(url);
            this._playNext();
        });
    }

    /**
     * Stop all playback and clear the queue.
     */
    stop() {
        this.queue = [];
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.src = '';
            this.currentAudio = null;
        }
        this.isPlaying = false;
    }
}
