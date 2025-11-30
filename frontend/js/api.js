// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

class API {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    async requestWithFormData(endpoint, formData, method = 'POST') {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            method: method,
            credentials: 'include',
            body: formData,
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    // Auth endpoints
    async login(username, password) {
        return this.request('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    }

    async logout() {
        return this.request('/auth/logout/', {
            method: 'POST',
        });
    }

    // Customer endpoints
    async registerCustomer(formData) {
        return this.requestWithFormData('/customers/register/', formData);
    }

    async getCurrentCustomer() {
        return this.request('/customers/me/');
    }

    // Loan endpoints
    async getLoanTypes() {
        return this.request('/loan-types/');
    }

    async getLoanApplications() {
        return this.request('/loan-applications/');
    }

    async submitLoanApplication(data) {
        return this.request('/loan-applications/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }
}

// Create global API instance
const api = new API();