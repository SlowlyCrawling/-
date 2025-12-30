const API_BASE_URLS = {
    user: 'http://localhost:5000',
    master: 'http://localhost:5001',
    booking: 'http://localhost:5002',
    confirmation: 'http://localhost:5003',
    history: 'http://localhost:5004'
};

class BarberShopAPI {
    constructor() {
        this.currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;
    }

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : 
                    `${API_BASE_URLS[options.service || 'user']}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        try {
            const response = await fetch(url, defaultOptions);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async register(name, email, password) {
        const data = await this.request('/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password })
        });
        
        if (data.success) {
            this.currentUser = { id: data.user_id, name, email, role: data.role };
            localStorage.setItem('currentUser', JSON.stringify(this.currentUser));
        }
        
        return data;
    }

    async login(email, password) {
        const data = await this.request('/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        if (data.success) {
            this.currentUser = {
                id: data.user_id,
                name: data.name,
                email: email,
                role: data.role
            };
            localStorage.setItem('currentUser', JSON.stringify(this.currentUser));
        }
        
        return data;
    }

    async getMasters() {
        return await this.request('/masters', { service: 'master' });
    }

    async getMasterSchedule(masterId, date) {
        return await this.request(`/schedule/${masterId}/${date}`, { service: 'master' });
    }

    async bookSlot(masterId, date, time, clientId) {
        return await this.request(`/book_slot/${masterId}/${date}/${time}`, {
            service: 'master',
            method: 'POST',
            body: JSON.stringify({ client_id: clientId })
        });
    }

    async freeSlot(masterId, date, time) {
        return await this.request(`/free_slot/${masterId}/${date}/${time}`, {
            service: 'master',
            method: 'DELETE'
        });
    }

    async bookAppointment(masterId, date, time) {
        return await this.request('/book', {
            service: 'booking',
            method: 'POST',
            body: JSON.stringify({
                user_id: this.currentUser.id,
                master_id: masterId,
                date,
                time
            })
        });
    }

    async checkAvailability(masterId, date, time) {
        return await this.request(`/check_availability/${masterId}/${date}/${time}`, {
            service: 'booking'
        });
    }

    async getUserBookings(userId) {
        return await this.request(`/user_bookings/${userId}`, { service: 'confirmation' });
    }

    async getMasterBookings(masterId) {
        return await this.request(`/master_bookings/${masterId}`, { service: 'confirmation' });
    }

    async cancelBooking(bookingId) {
        return await this.request(`/cancel_booking/${bookingId}`, {
            service: 'confirmation',
            method: 'DELETE'
        });
    }

    async getUserSessions(userId) {
        return await this.request(`/user_sessions/${userId}`, { service: 'history' });
    }

    async completeVisit(data) {
        return await this.request('/complete_visit', {
            service: 'history',
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getRecommendation(userId) {
        return await this.request(`/get_recommendation/${userId}`, { service: 'history' });
    }

    async updateSession(sessionId, status) {
        return await this.request(`/update_session/${sessionId}`, {
            service: 'history',
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }

    logout() {
        this.currentUser = null;
        localStorage.removeItem('currentUser');
        localStorage.removeItem('recommendationShown');
    }

    isAuthenticated() {
        return !!this.currentUser;
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isAdmin() {
        return this.currentUser?.role === 'admin';
    }

    isMaster() {
        return this.currentUser?.role === 'master';
    }

    isClient() {
        return this.currentUser?.role === 'client';
    }
}

window.api = new BarberShopAPI();