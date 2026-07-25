// Main JavaScript File

// Flash Message Handler
function showFlashMessage(message, category = 'info') {
    const container = document.getElementById('flash-messages');
    if (!container) return;

    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[category] || 'alert-info';

    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show shadow-sm" role="alert">
            <i class="bi ${category === 'success' ? 'bi-check-circle' : 'bi-info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', alertHtml);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = container.lastElementChild;
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

// Global Auth Check (Placeholder for now)
function checkAuth() {
    // In a full CSR app, we would fetch /api/me to check session.
    // For now, we rely on the backend redirects, but we can toggle UI elements here.
    const navbar = document.getElementById('mainNavbar');
    // Simple logic: If we are not on login/register page, show nav
    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
        if (navbar) navbar.classList.remove('d-none');
    }
}

// ============================================
// UI Animations & Micro-interactions
// ============================================

/**
 * Card Hover Lift Effects
 */
function initCardAnimations() {
    const cards = document.querySelectorAll('.card-hover-lift');

    cards.forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.transform = 'translateY(-4px) scale(1.01)';
            this.style.boxShadow = '0 20px 40px -10px rgba(0, 0, 0, 0.15)';
        });

        card.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0) scale(1)';
            this.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
        });
    });
}

/**
 * Button Press Effects
 */
function initButtonEffects() {
    const buttons = document.querySelectorAll('button:not([disabled]), .btn:not([disabled])');

    buttons.forEach(btn => {
        btn.addEventListener('mousedown', function (e) {
            if (!this.disabled) {
                this.style.transform = 'scale(0.95)';
            }
        });

        btn.addEventListener('mouseup', function () {
            if (!this.disabled) {
                this.style.transform = 'scale(1)';
            }
        });

        btn.addEventListener('mouseleave', function () {
            this.style.transform = 'scale(1)';
        });
    });
}

/**
 * Scroll-based Animations
 */
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

/**
 * Form Input Enhancements
 */
function initFormEnhancements() {
    const inputs = document.querySelectorAll('input, select, textarea');

    inputs.forEach(input => {
        input.addEventListener('focus', function () {
            this.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            this.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.1)';
        });

        input.addEventListener('blur', function () {
            this.style.boxShadow = 'none';
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();

    // Initialize UI enhancements
    initCardAnimations();
    initButtonEffects();
    initScrollAnimations();
    initFormEnhancements();

    // Global Logout Handler
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/auth/logout';
        });
    }
});
