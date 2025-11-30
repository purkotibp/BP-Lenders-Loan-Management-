// Loan management
class LoanManager {
    constructor() {
        this.loanTypes = [];
        this.applications = [];
    }

    async loadLoanTypes() {
        try {
            this.loanTypes = await api.getLoanTypes();
            this.displayLoanTypes();
            this.populateLoanTypeSelect();
        } catch (error) {
            console.error('Failed to load loan types:', error);
        }
    }

    async loadApplications() {
        try {
            this.applications = await api.getLoanApplications();
            this.displayApplications();
            this.updateStats();
        } catch (error) {
            console.error('Failed to load applications:', error);
        }
    }

    async submitApplication(formData) {
        const data = {
            loan_type: parseInt(formData.get('loan_type')),
            requested_amount: parseFloat(formData.get('requested_amount')),
            purpose: formData.get('purpose'),
            credit_score: parseInt(formData.get('credit_score')),
        };

        try {
            await api.submitLoanApplication(data);
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    displayLoanTypes() {
        const container = document.getElementById('loanTypes');
        if (!container) return;

        container.innerHTML = this.loanTypes.map(loanType => `
            <div class="loan-type-card">
                <h4>${loanType.name}</h4>
                <p><strong>Max Amount:</strong> $${loanType.max_amount}</p>
                <p><strong>Interest Rate:</strong> ${loanType.interest_rate}%</p>
                <p><strong>Duration:</strong> ${loanType.duration_months} months</p>
                <p>${loanType.description}</p>
            </div>
        `).join('');
    }

    populateLoanTypeSelect() {
        const select = document.getElementById('loanTypeSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select Loan Type</option>' +
            this.loanTypes.map(loanType => `
                <option value="${loanType.id}" data-max-amount="${loanType.max_amount}">
                    ${loanType.name} (Max: $${loanType.max_amount})
                </option>
            `).join('');
    }

    displayApplications() {
        const tbody = document.querySelector('#applicationsTable tbody');
        if (!tbody) return;

        tbody.innerHTML = this.applications.map(app => `
            <tr>
                <td>${app.loan_type_name}</td>
                <td>$${app.requested_amount}</td>
                <td class="status-${app.status}">${app.status.charAt(0).toUpperCase() + app.status.slice(1)}</td>
                <td>${new Date(app.application_date).toLocaleDateString()}</td>
                <td>${app.approval_score ? app.approval_score.toFixed(1) : 'N/A'}/100</td>
            </tr>
        `).join('');
    }

    updateStats() {
        const total = this.applications.length;
        const approved = this.applications.filter(app => app.status === 'approved').length;
        const pending = this.applications.filter(app => app.status === 'pending').length;

        document.getElementById('totalApplications').textContent = total;
        document.getElementById('approvedLoans').textContent = approved;
        document.getElementById('pendingApplications').textContent = pending;
    }

    async loadDashboard() {
        try {
            // Load customer info
            const customer = await api.getCurrentCustomer();
            document.getElementById('customerName').textContent = `${customer.first_name} ${customer.surname}`;

            // Load applications
            await this.loadApplications();
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    }
}

// Create global LoanManager instance
const loan = new LoanManager();