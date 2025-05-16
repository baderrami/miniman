/**
 * Notification system for providing user feedback
 */

// Store for notification settings
const notificationSettings = {
    autoHide: true,
    displayDuration: 5000, // 5 seconds
    position: 'top-right'
};

/**
 * Show a notification to the user
 * 
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 * @param {Object} options - Additional options
 * @param {boolean} options.autoHide - Whether to automatically hide the notification
 * @param {number} options.duration - How long to display the notification in ms
 * @param {string} options.position - Position of the notification (top-right, top-left, bottom-right, bottom-left)
 */
function showNotification(message, type = 'info', options = {}) {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
        
        // Add styles if not already present
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                .notification-container {
                    position: fixed;
                    z-index: 9999;
                    max-width: 350px;
                    width: 100%;
                }
                .notification-container.top-right {
                    top: 20px;
                    right: 20px;
                }
                .notification-container.top-left {
                    top: 20px;
                    left: 20px;
                }
                .notification-container.bottom-right {
                    bottom: 20px;
                    right: 20px;
                }
                .notification-container.bottom-left {
                    bottom: 20px;
                    left: 20px;
                }
                .notification {
                    margin-bottom: 10px;
                    padding: 15px;
                    border-radius: 4px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    animation: notification-fade-in 0.3s ease-out;
                    position: relative;
                }
                .notification.hiding {
                    animation: notification-fade-out 0.3s ease-in forwards;
                }
                .notification-success {
                    background-color: #d4edda;
                    border-color: #c3e6cb;
                    color: #155724;
                }
                .notification-error {
                    background-color: #f8d7da;
                    border-color: #f5c6cb;
                    color: #721c24;
                }
                .notification-warning {
                    background-color: #fff3cd;
                    border-color: #ffeeba;
                    color: #856404;
                }
                .notification-info {
                    background-color: #d1ecf1;
                    border-color: #bee5eb;
                    color: #0c5460;
                }
                .notification-close {
                    position: absolute;
                    top: 5px;
                    right: 10px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 16px;
                }
                @keyframes notification-fade-in {
                    from { opacity: 0; transform: translateY(-20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes notification-fade-out {
                    from { opacity: 1; transform: translateY(0); }
                    to { opacity: 0; transform: translateY(-20px); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Set container position
    const position = options.position || notificationSettings.position;
    container.className = `notification-container ${position}`;
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Add close button
    const closeBtn = document.createElement('span');
    closeBtn.className = 'notification-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => {
        hideNotification(notification);
    });
    
    // Add message
    const messageEl = document.createElement('div');
    messageEl.className = 'notification-message';
    messageEl.textContent = message;
    
    // Assemble notification
    notification.appendChild(closeBtn);
    notification.appendChild(messageEl);
    
    // Add to container
    container.appendChild(notification);
    
    // Auto-hide if enabled
    const autoHide = 'autoHide' in options ? options.autoHide : notificationSettings.autoHide;
    if (autoHide) {
        const duration = options.duration || notificationSettings.displayDuration;
        setTimeout(() => {
            hideNotification(notification);
        }, duration);
    }
    
    return notification;
}

/**
 * Hide a notification with animation
 * 
 * @param {HTMLElement} notification - The notification element to hide
 */
function hideNotification(notification) {
    notification.classList.add('hiding');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300); // Match the animation duration
}

/**
 * Show a success notification
 * 
 * @param {string} message - The message to display
 * @param {Object} options - Additional options
 */
function showSuccess(message, options = {}) {
    return showNotification(message, 'success', options);
}

/**
 * Show an error notification
 * 
 * @param {string} message - The message to display
 * @param {Object} options - Additional options
 */
function showError(message, options = {}) {
    return showNotification(message, 'error', options);
}

/**
 * Show a warning notification
 * 
 * @param {string} message - The message to display
 * @param {Object} options - Additional options
 */
function showWarning(message, options = {}) {
    return showNotification(message, 'warning', options);
}

/**
 * Show an info notification
 * 
 * @param {string} message - The message to display
 * @param {Object} options - Additional options
 */
function showInfo(message, options = {}) {
    return showNotification(message, 'info', options);
}

/**
 * Update notification settings
 * 
 * @param {Object} settings - New settings to apply
 */
function updateNotificationSettings(settings = {}) {
    Object.assign(notificationSettings, settings);
}