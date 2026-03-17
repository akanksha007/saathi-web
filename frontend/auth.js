/**
 * Saathi — Authentication Module.
 * Handles phone OTP login, Google Sign-In, onboarding, and JWT token management.
 */

class SaathiAuth {
    constructor() {
        this.token = localStorage.getItem('saathi_token') || null;
        this.user = null;

        // Try to parse stored user info
        const storedUser = localStorage.getItem('saathi_user');
        if (storedUser) {
            try { this.user = JSON.parse(storedUser); } catch (e) {}
        }
    }

    /**
     * Check if the user is authenticated.
     */
    get isAuthenticated() {
        return !!this.token;
    }

    /**
     * Get the user's display name.
     */
    get userName() {
        return this.user?.name || '';
    }

    /**
     * Get the API base URL.
     */
    _apiUrl(path) {
        return `${window.location.origin}${path}`;
    }

    /**
     * Send OTP to a phone number.
     */
    async sendOtp(phone) {
        try {
            const response = await fetch(this._apiUrl('/auth/send-otp'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone }),
            });
            return await response.json();
        } catch (e) {
            return { success: false, message: 'Network error. Please try again.' };
        }
    }

    /**
     * Verify OTP and get JWT token.
     */
    async verifyOtp(phone, code) {
        try {
            const response = await fetch(this._apiUrl('/auth/verify-otp'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone, code }),
            });
            const data = await response.json();
            if (data.success && data.token) {
                this.token = data.token;
                this.user = data.user || {};
                localStorage.setItem('saathi_token', this.token);
                localStorage.setItem('saathi_user', JSON.stringify(this.user));
            }
            return data;
        } catch (e) {
            return { success: false, message: 'Network error. Please try again.' };
        }
    }

    /**
     * Google Sign-In — verify the ID token with our backend.
     */
    async googleSignIn(idToken) {
        try {
            const response = await fetch(this._apiUrl('/auth/google'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: idToken }),
            });
            const data = await response.json();
            if (data.success && data.token) {
                this.token = data.token;
                this.user = data.user || {};
                localStorage.setItem('saathi_token', this.token);
                localStorage.setItem('saathi_user', JSON.stringify(this.user));
            }
            return data;
        } catch (e) {
            return { success: false, message: 'Network error. Please try again.' };
        }
    }

    /**
     * Complete onboarding — save name, age range, reason.
     */
    async completeOnboarding(name, ageRange, reason) {
        try {
            const response = await fetch(this._apiUrl('/auth/onboard'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`,
                },
                body: JSON.stringify({ name, age_range: ageRange, reason }),
            });
            const data = await response.json();
            if (data.success && data.user) {
                this.user = data.user;
                localStorage.setItem('saathi_user', JSON.stringify(this.user));
            }
            return data;
        } catch (e) {
            return { success: false, message: 'Network error.' };
        }
    }

    /**
     * Get current user profile from server (validates token).
     */
    async getProfile() {
        if (!this.token) return null;
        try {
            const response = await fetch(this._apiUrl('/auth/me'), {
                headers: { 'Authorization': `Bearer ${this.token}` },
            });
            if (response.ok) {
                const data = await response.json();
                this.user = data.user;
                localStorage.setItem('saathi_user', JSON.stringify(this.user));
                return data.user;
            } else {
                // Token expired or invalid
                this.logout();
                return null;
            }
        } catch (e) {
            return null;
        }
    }

    /**
     * Logout — clear all auth state.
     */
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('saathi_token');
        localStorage.removeItem('saathi_user');
    }

    /**
     * Check if onboarding is needed (user has no name set).
     */
    get needsOnboarding() {
        return this.isAuthenticated && (!this.user || !this.user.name);
    }
}

// Global auth instance
const auth = new SaathiAuth();
