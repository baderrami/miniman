/**
 * Main JavaScript file for Device Manager application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize alerts auto-dismiss
    initializeAlerts();
    
    // Initialize progress bars
    initializeProgressBars();
    
    // Add active class to current nav item
    highlightCurrentNavItem();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize auto-dismiss for alert messages
 */
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000); // Auto-dismiss after 5 seconds
    });
}

/**
 * Initialize progress bars with animation
 */
function initializeProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(function(bar) {
        // Get the target width from data attribute or current style
        const targetWidth = bar.getAttribute('data-percent') || 
                           bar.style.width || 
                           bar.getAttribute('aria-valuenow') + '%';
        
        // Set initial width to 0
        bar.style.width = '0%';
        
        // Animate to target width
        setTimeout(function() {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.width = targetWidth;
        }, 100);
    });
}

/**
 * Highlight current navigation item
 */
function highlightCurrentNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && currentPath.includes(href) && href !== '/') {
            link.classList.add('active');
        }
    });
}

/**
 * Format bytes to human-readable format
 * @param {number} bytes - The bytes to format
 * @param {number} decimals - The number of decimal places
 * @returns {string} - Formatted string
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Show confirmation dialog
 * @param {string} message - The confirmation message
 * @param {function} callback - The callback function to execute if confirmed
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Show loading spinner
 * @param {string} targetSelector - The selector for the target element
 * @param {string} message - The loading message
 */
function showLoading(targetSelector, message = 'Loading...') {
    const target = document.querySelector(targetSelector);
    if (target) {
        const spinner = `
            <div class="text-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">${message}</p>
            </div>
        `;
        target.innerHTML = spinner;
    }
}

/**
 * Handle AJAX errors
 * @param {Error} error - The error object
 */
function handleAjaxError(error) {
    console.error('AJAX Error:', error);
    alert('An error occurred while communicating with the server. Please try again later.');
}