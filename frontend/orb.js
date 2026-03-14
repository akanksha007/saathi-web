/**
 * Saathi Web Sandbox — Living Orb Animation.
 * A fluid, reactive orb that responds to conversation state.
 * Inspired by ChatGPT's voice mode visualization.
 */

class LivingOrb {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.state = 'listening';  // listening | processing | speaking
        this.time = 0;
        this.animationId = null;
        this.audioLevel = 0;  // 0-1, driven by mic/playback volume
        this.targetAudioLevel = 0;

        // Persona color
        this.color = { r: 34, g: 197, b: 94 };  // Default: empathy green
        this.targetColor = { ...this.color };

        // High DPI support
        this._setupCanvas();

        // Blob shape parameters
        this.blobPoints = 6;
        this.blobRadii = new Array(this.blobPoints).fill(0).map(() => Math.random() * 0.5);
        this.blobSpeeds = new Array(this.blobPoints).fill(0).map(() => 0.5 + Math.random() * 1.5);
    }

    _setupCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.w = rect.width;
        this.h = rect.height;
        this.cx = this.w / 2;
        this.cy = this.h / 2;
    }

    /**
     * Set the orb state.
     */
    setState(state) {
        this.state = state;
        switch (state) {
            case 'listening':
                this.targetColor = this._personaColor || { r: 34, g: 197, b: 94 };
                break;
            case 'processing':
                this.targetColor = { r: 245, g: 158, b: 11 };
                break;
            case 'speaking':
                this.targetColor = { r: 59, g: 130, b: 246 };
                break;
        }
    }

    /**
     * Set persona color (used for listening state).
     */
    setPersonaColor(persona) {
        const colors = {
            empathy: { r: 34, g: 197, b: 94 },
            funny: { r: 245, g: 158, b: 11 },
            angry: { r: 239, g: 68, b: 68 },
            happy: { r: 168, g: 85, b: 247 },
            loving: { r: 236, g: 72, b: 153 },
        };
        this._personaColor = colors[persona] || colors.empathy;
        if (this.state === 'listening') {
            this.targetColor = this._personaColor;
        }
    }

    /**
     * Set audio level (0-1) from mic or speaker.
     */
    setAudioLevel(level) {
        this.targetAudioLevel = Math.min(1, Math.max(0, level));
    }

    /**
     * Start animation loop.
     */
    start() {
        if (this.animationId) return;
        this._animate();
    }

    /**
     * Stop animation loop.
     */
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    /**
     * Main animation loop.
     */
    _animate() {
        this.time += 0.016;

        // Smooth transitions
        this.audioLevel += (this.targetAudioLevel - this.audioLevel) * 0.15;
        this.color.r += (this.targetColor.r - this.color.r) * 0.05;
        this.color.g += (this.targetColor.g - this.color.g) * 0.05;
        this.color.b += (this.targetColor.b - this.color.b) * 0.05;

        // Clear
        this.ctx.clearRect(0, 0, this.w, this.h);

        // Draw layers
        this._drawGlow();
        this._drawBlob();
        this._drawCore();

        this.animationId = requestAnimationFrame(() => this._animate());
    }

    /**
     * Outer glow — soft ambient light.
     */
    _drawGlow() {
        const { r, g, b } = this.color;
        const glowSize = 80 + this.audioLevel * 30;
        const baseAlpha = this.state === 'speaking' ? 0.15 : 0.08;
        const alpha = baseAlpha + this.audioLevel * 0.1;

        const gradient = this.ctx.createRadialGradient(
            this.cx, this.cy, 0,
            this.cx, this.cy, glowSize + 40
        );
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha})`);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.w, this.h);
    }

    /**
     * Middle blob layer — organic, fluid shape.
     */
    _drawBlob() {
        const { r, g, b } = this.color;
        const baseRadius = 55 + this.audioLevel * 15;

        // Speed varies by state
        let speed = 1;
        if (this.state === 'processing') speed = 2.5;
        if (this.state === 'speaking') speed = 1.8;

        this.ctx.beginPath();

        const points = this.blobPoints;
        const angleStep = (Math.PI * 2) / points;

        for (let i = 0; i <= points; i++) {
            const angle = i * angleStep;
            const noiseVal = this.blobRadii[i % points];
            const timeOffset = this.blobSpeeds[i % points] * speed;

            const radiusNoise = Math.sin(this.time * timeOffset + noiseVal * 10) * (8 + this.audioLevel * 12);
            const radius = baseRadius + radiusNoise;

            const x = this.cx + Math.cos(angle) * radius;
            const y = this.cy + Math.sin(angle) * radius;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                // Smooth curve through points
                const prevAngle = (i - 1) * angleStep;
                const prevNoise = Math.sin(this.time * this.blobSpeeds[(i - 1) % points] * speed + this.blobRadii[(i - 1) % points] * 10) * (8 + this.audioLevel * 12);
                const prevRadius = baseRadius + prevNoise;
                const prevX = this.cx + Math.cos(prevAngle) * prevRadius;
                const prevY = this.cy + Math.sin(prevAngle) * prevRadius;

                const cpX = (prevX + x) / 2;
                const cpY = (prevY + y) / 2;
                this.ctx.quadraticCurveTo(prevX, prevY, cpX, cpY);
            }
        }

        this.ctx.closePath();

        // Fill with gradient
        const blobAlpha = 0.15 + this.audioLevel * 0.1;
        const gradient = this.ctx.createRadialGradient(
            this.cx, this.cy, 0,
            this.cx, this.cy, baseRadius + 20
        );
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${blobAlpha + 0.1})`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, ${blobAlpha * 0.3})`);

        this.ctx.fillStyle = gradient;
        this.ctx.fill();
    }

    /**
     * Inner core — bright, solid center.
     */
    _drawCore() {
        const { r, g, b } = this.color;

        // Core size reacts to state + audio
        let coreRadius = 28;
        if (this.state === 'listening') {
            coreRadius = 28 + Math.sin(this.time * 1.5) * 3 + this.audioLevel * 8;
        } else if (this.state === 'processing') {
            coreRadius = 24 + Math.sin(this.time * 3) * 5;
        } else if (this.state === 'speaking') {
            coreRadius = 30 + this.audioLevel * 14;
        }

        // Draw core
        const gradient = this.ctx.createRadialGradient(
            this.cx, this.cy, 0,
            this.cx, this.cy, coreRadius
        );
        gradient.addColorStop(0, `rgba(${Math.min(255, r + 80)}, ${Math.min(255, g + 80)}, ${Math.min(255, b + 80)}, 0.95)`);
        gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.8)`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.4)`);

        this.ctx.beginPath();
        this.ctx.arc(this.cx, this.cy, coreRadius, 0, Math.PI * 2);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();

        // Inner highlight
        const hlGrad = this.ctx.createRadialGradient(
            this.cx - coreRadius * 0.25, this.cy - coreRadius * 0.25, 0,
            this.cx, this.cy, coreRadius * 0.8
        );
        hlGrad.addColorStop(0, 'rgba(255, 255, 255, 0.25)');
        hlGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

        this.ctx.beginPath();
        this.ctx.arc(this.cx, this.cy, coreRadius * 0.9, 0, Math.PI * 2);
        this.ctx.fillStyle = hlGrad;
        this.ctx.fill();
    }
}
