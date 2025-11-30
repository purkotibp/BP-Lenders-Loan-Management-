// Authentication management
class Auth {
    constructor() {
        this.currentUser = null;
        this.checkLoginStatus();
    }

    async login(username, password) {
        try {
            const response = await api.login(username, password);
            this.currentUser = response.user;
            localStorage.setItem('currentUser', JSON.stringify(this.currentUser));
            return { success: true, user: this.currentUser };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async logout() {
        try {
            await api.logout();
            this.currentUser = null;
            localStorage.removeItem('currentUser');
            window.location.href = 'login.html';
        } catch (error) {
            console.error('Logout failed:', error);
        }
    }

    async register(formData) {
        try {
            const response = await api.registerCustomer(formData);
            return { success: true, message: response.message };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    checkLoginStatus() {
        const storedUser = localStorage.getItem('currentUser');
        if (storedUser) {
            this.currentUser = JSON.parse(storedUser);
            return true;
        }
        return false;
    }

    isAuthenticated() {
        return this.currentUser !== null;
    }

    isAdmin() {
        return this.currentUser && this.currentUser.is_admin;
    }

    getCurrentUser() {
        return this.currentUser;
    }
}

// Create global Auth instance
const auth = new Auth();