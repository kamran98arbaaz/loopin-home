// Enhanced Notifications System with Socket.IO integration
let socket;
let notifications = [];
let unreadCount = 0;

// Initialize Socket.IO connection
function initializeSocketIO() {
    console.log('🔌 Initializing Socket.IO connection...');

    if (typeof io !== 'undefined') {
        console.log('✅ Socket.IO library available, creating connection...');

        // Get the current host for Socket.IO connection
        const protocol = window.location.protocol;
        const host = window.location.host;
        const socketUrl = `${protocol}//${host}`;

        console.log('🔗 Connecting to Socket.IO at:', socketUrl);

        socket = io(socketUrl, {
            transports: ['polling', 'websocket'], // Try polling first, then websocket
            timeout: 20000, // Increased timeout
            forceNew: false, // Don't force new connection
            reconnection: true,
            reconnectionAttempts: 10, // More reconnection attempts
            reconnectionDelay: 1000,
            maxReconnectionAttempts: 10,
            upgrade: true, // Allow transport upgrade
            rememberUpgrade: true, // Remember transport upgrade
            secure: window.location.protocol === 'https:', // Match protocol
            rejectUnauthorized: false, // For development
            // Additional options for better compatibility
            path: '/socket.io', // Explicit Socket.IO path
            query: {}, // No additional query parameters
            extraHeaders: {} // No extra headers
        });
        console.log('🔧 Socket.IO connection options set');

        // Connection events
        socket.on('connect', function() {
            console.log('✅ Connected to real-time updates - Socket ID:', socket.id);
            console.log('🔗 Connection details:', {
                connected: socket.connected,
                disconnected: socket.disconnected,
                transport: socket.io.engine.transport.name
            });
            // Request initial unread count
            console.log('📊 Requesting initial unread count...');
            socket.emit('get_unread_count');
        });

        socket.on('disconnect', function() {
            console.log('❌ Disconnected from real-time updates');
        });

        socket.on('connect_error', function(error) {
            console.error('🚫 Socket.IO connection error:', error);
            console.error('Error details:', {
                type: error.type,
                description: error.description,
                context: error.context
            });
        });

        socket.on('connect_timeout', function() {
            console.error('⏰ Socket.IO connection timeout');
        });

        socket.on('reconnect', function(attemptNumber) {
            console.log('🔄 Socket.IO reconnected after', attemptNumber, 'attempts');
        });

        socket.on('reconnect_attempt', function(attemptNumber) {
            console.log('🔄 Socket.IO reconnection attempt', attemptNumber);
        });

        socket.on('reconnect_error', function(error) {
            console.error('🚫 Socket.IO reconnection error:', error);
        });

        socket.on('reconnect_failed', function() {
            console.error('❌ Socket.IO reconnection failed permanently');
        });
        
        // Handle real-time updates
        socket.on('new_update', function(data) {
            console.log('🔔 New update received via Socket.IO:', data);
            console.log('📦 Update details - ID:', data.id, 'Name:', data.name, 'Process:', data.process);

            addNotification({
                type: 'new_update',
                title: 'New Update',
                message: `New update from ${data.name || 'Unknown'}`,
                update_id: data.id,
                timestamp: new Date().toISOString(),
                unread: true
            });

            console.log('🔊 Playing notification sound...');
            playNotificationSound();

            // Enhanced toast with process details and permanent display
            const processInfo = data.process ? ` in **${data.process}**` : '';
            const message = `🔔 **NEW UPDATE POSTED!**${processInfo} by ${data.name || 'Unknown'}. Check it out now!`;
            console.log('🍞 Showing toast notification:', message);
            showToast(message, 'permanent'); // Permanent notification with close button
        });
        
        // Handle unread count updates
        socket.on('unread_count', function(data) {
            updateUnreadCounterEnhanced(data.count);
        });
        
        // Handle notifications
        socket.on('notification', function(data) {
            console.log('📬 Notification received via Socket.IO:', data);
            console.log('📋 Notification type:', data.type, 'Message:', data.message);

            addNotification({
                ...data,
                timestamp: data.timestamp || new Date().toISOString(),
                unread: true
            });

            console.log('🔊 Playing notification sound for notification...');
            playNotificationSound();

            // Show enhanced toast for different types
            if (data.type === 'new_sop') {
                console.log('📋 Showing SOP notification toast');
                showToast('📋 ' + data.message, 'permanent');
            } else if (data.type === 'new_lesson') {
                console.log('🎓 Showing lesson notification toast');
                showToast('🎓 ' + data.message, 'permanent');
            } else {
                console.log('🔔 Showing generic notification toast');
                showToast('🔔 ' + data.message, 'permanent');
            }
        });
        
        // Handle successful operations
        socket.on('success', function(data) {
            showToast(`✅ ${data.message}`);
        });
        
        // Handle errors
        socket.on('error', function(data) {
            showToast(`❌ ${data.message}`);
        });
        
        // Handle info messages
        socket.on('info', function(data) {
            showToast(`ℹ️ ${data.message}`);
        });
        
        // Subscribe to updates
        console.log('📡 Subscribing to real-time updates...');
        socket.emit('subscribe_to_updates');

        // Handle subscription confirmation
        socket.on('subscribed', function(data) {
            console.log('✅ Successfully subscribed to updates:', data);
        });

        socket.on('connected', function(data) {
            console.log('🔗 Socket.IO connection confirmed:', data);
        });
    } else {
        console.error('❌ Socket.IO library not available! Check if CDN is loading properly.');
    }
}

// Add a new notification
function addNotification(notification) {
    notifications.unshift(notification);
    
    // Keep only last 50 notifications
    if (notifications.length > 50) {
        notifications = notifications.slice(0, 50);
    }
    
    // Update unread count
    if (notification.unread) {
        unreadCount++;
        updateUnreadCounterEnhanced(unreadCount);
    }
    
    // Update notifications panel
    updateNotificationsPanel();
    
    // Store in localStorage
    localStorage.setItem('notifications', JSON.stringify(notifications));
}

// Update the unread counter display
function updateUnreadCounter(count) {
    unreadCount = count;
    const counter = document.getElementById('unread-counter');

    if (counter) {
        if (count > 0) {
            counter.textContent = count > 99 ? '99+' : count.toString();
            counter.style.display = 'flex';
        } else {
            counter.style.display = 'none';
        }
    }
}

// Check for recent updates and show badge
function checkForRecentUpdatesAndShowBadge() {
    fetch('/api/latest-update-time')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.latest_timestamp) {
                const latestTime = new Date(data.latest_timestamp);
                const now = new Date();
                const diffHours = (now - latestTime) / (1000 * 60 * 60);

                const counter = document.getElementById('unread-counter');

                if (counter) {
                    if (diffHours <= 24) {
                        // Show red dot for recent updates (within 24 hours)
                        counter.textContent = '•';
                        counter.style.display = 'flex';
                        counter.style.fontSize = '20px';
                        counter.style.lineHeight = '1';
                        counter.classList.add('recent-update-badge');
                    } else if (unreadCount === 0) {
                        // Hide badge if no recent updates and no unread notifications
                        counter.style.display = 'none';
                        counter.classList.remove('recent-update-badge');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error checking for recent updates:', error);
        });
}

// Enhanced updateUnreadCounter to work with recent updates badge
function updateUnreadCounterEnhanced(count) {
    unreadCount = count;
    const counter = document.getElementById('unread-counter');

    if (counter) {
        if (count > 0) {
            // Show notification count
            counter.textContent = count > 99 ? '99+' : count.toString();
            counter.style.display = 'flex';
            counter.style.fontSize = '11px';
            counter.style.lineHeight = 'normal';
            counter.classList.remove('recent-update-badge');
        } else {
            // Check for recent updates when no unread notifications
            checkForRecentUpdatesAndShowBadge();
        }
    }
}

// Update the notifications panel
function updateNotificationsPanel() {
    const notificationsList = document.getElementById('notifications-list');
    if (!notificationsList) return;
    
    notificationsList.innerHTML = '';
    
    if (notifications.length === 0) {
        notificationsList.innerHTML = '<div class="notification-item"><em>No notifications yet</em></div>';
        return;
    }
    
    notifications.forEach((notification, index) => {
        const notificationElement = createNotificationElement(notification, index);
        notificationsList.appendChild(notificationElement);
    });
}

// Create a notification element
function createNotificationElement(notification, index) {
    const div = document.createElement('div');
    div.className = `notification-item ${notification.unread ? 'unread' : ''}`;
    div.onclick = () => handleNotificationClick(notification, index);
    
    const time = new Date(notification.timestamp).toLocaleTimeString();
    
    div.innerHTML = `
        <div class="notification-title">${notification.title}</div>
        <div class="notification-message">${notification.message}</div>
        <div class="notification-time">${time}</div>
    `;
    
    return div;
}

// Handle notification click
function handleNotificationClick(notification, index) {
    // Mark as read
    if (notification.unread) {
        notification.unread = false;
        unreadCount = Math.max(0, unreadCount - 1);
        updateUnreadCounterEnhanced(unreadCount);
        updateNotificationsPanel();
        
        // If it's an update, mark it as read on the server
        if (notification.update_id && socket) {
            socket.emit('mark_as_read', { update_id: notification.update_id });
        }
        
        // Store updated notifications
        localStorage.setItem('notifications', JSON.stringify(notifications));
    }
    
    // Handle navigation if needed
    if (notification.type === 'new_update' && notification.update_id) {
        // Could navigate to the update or scroll to it
        console.log('Navigate to update:', notification.update_id);
    }
}

// Toggle notifications panel
function toggleNotifications() {
    const panel = document.getElementById('notifications-panel');
    if (panel) {
        const isVisible = panel.classList.contains('show');

        if (isVisible) {
            panel.classList.remove('show');
        } else {
            panel.classList.add('show');
            // Load notifications from localStorage
            loadNotificationsFromStorage();
            updateNotificationsPanel();
        }
    }
}

// Mark all notifications as read
function markAllAsRead() {
    notifications.forEach(notification => {
        notification.unread = false;
    });
    
    unreadCount = 0;
    updateUnreadCounterEnhanced(unreadCount);
    updateNotificationsPanel();
    
    // Store updated notifications
    localStorage.setItem('notifications', JSON.stringify(notifications));
}

// Load notifications from localStorage
function loadNotificationsFromStorage() {
    try {
        const stored = localStorage.getItem('notifications');
        if (stored) {
            notifications = JSON.parse(stored);
            // Count unread notifications
            unreadCount = notifications.filter(n => n.unread).length;
            updateUnreadCounterEnhanced(unreadCount);
        }
    } catch (error) {
        console.error('Error loading notifications from storage:', error);
        notifications = [];
        unreadCount = 0;
    }
}

// Play notification sound
function playNotificationSound() {
    // Check if user has enabled sound notifications
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    if (!soundEnabled) return;

    try {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5; // Set volume to 50%

        // Add error handling for audio loading
        audio.addEventListener('error', function(e) {
            console.log('Error loading notification sound:', e);
        });

        audio.play().catch(error => {
            console.log('Could not play notification sound:', error);
            // Fallback: try to create a simple beep sound
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.3);
            } catch (fallbackError) {
                console.log('Fallback sound also failed:', fallbackError);
            }
        });
    } catch (error) {
        console.log('Error creating notification sound:', error);
    }
}

// Show toast message
function showToast(message, duration = 6000) {
    const toast = document.createElement('div');
    toast.className = 'toast';

    // Support for bold text using **text** syntax
    const formattedMessage = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Create toast content container
    const toastContent = document.createElement('div');
    toastContent.className = 'toast-content';
    toastContent.innerHTML = formattedMessage;

    // Create close button for permanent notifications
    const isPermanent = duration === 'permanent';
    if (isPermanent) {
        toast.classList.add('toast-permanent');

        const closeButton = document.createElement('button');
        closeButton.className = 'toast-close';
        closeButton.innerHTML = '×';
        closeButton.setAttribute('aria-label', 'Close notification');
        closeButton.onclick = function() {
            closeToast(toast);
        };

        toast.appendChild(toastContent);
        toast.appendChild(closeButton);
    } else {
        toast.innerHTML = formattedMessage;
    }

    document.body.appendChild(toast);

    // Add unique ID to prevent conflicts
    toast.id = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    // Auto-close only for non-permanent notifications
    if (!isPermanent) {
        setTimeout(() => {
            closeToast(toast);
        }, duration);
    }
}

// Close toast function
function closeToast(toast) {
    toast.classList.remove('show');
    setTimeout(() => {
        if (document.body.contains(toast)) {
            document.body.removeChild(toast);
        }
    }, 500);
}

// Close notifications panel when clicking outside
document.addEventListener('click', function(event) {
    const panel = document.getElementById('notifications-panel');
    const bell = document.getElementById('notification-bell');

    if (panel && bell && !panel.contains(event.target) && !bell.contains(event.target)) {
        panel.classList.remove('show');
    }
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Load existing notifications
    loadNotificationsFromStorage();

    // Initialize Socket.IO
    initializeSocketIO();

    // Update unread counter display
    updateUnreadCounterEnhanced(unreadCount);

    // Check for recent updates and show badge periodically
    checkForRecentUpdatesAndShowBadge();
    setInterval(checkForRecentUpdatesAndShowBadge, 300000); // Check every 5 minutes to reduce server load

    // Update notifications panel
    updateNotificationsPanel();

    // Initialize sound toggle state
    initializeSoundToggle();
});

// Toggle notification sound
function toggleNotificationSound() {
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    const newState = !soundEnabled;

    localStorage.setItem('notificationSoundEnabled', newState.toString());

    // Update UI
    const soundToggle = document.getElementById('soundToggle');
    const soundIcon = document.getElementById('soundIcon');

    if (soundToggle && soundIcon) {
        if (newState) {
            soundToggle.classList.remove('disabled');
            soundIcon.className = 'fas fa-volume-up';
            soundToggle.title = 'Disable notification sounds';
        } else {
            soundToggle.classList.add('disabled');
            soundIcon.className = 'fas fa-volume-mute';
            soundToggle.title = 'Enable notification sounds';
        }
    }

    // Play a test sound if enabling
    if (newState) {
        playNotificationSound();
    }
}

// Initialize sound toggle state
function initializeSoundToggle() {
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    const soundToggle = document.getElementById('soundToggle');
    const soundIcon = document.getElementById('soundIcon');

    if (soundToggle && soundIcon) {
        if (soundEnabled) {
            soundToggle.classList.remove('disabled');
            soundIcon.className = 'fas fa-volume-up';
            soundToggle.title = 'Disable notification sounds';
        } else {
            soundToggle.classList.add('disabled');
            soundIcon.className = 'fas fa-volume-mute';
            soundToggle.title = 'Enable notification sounds';
        }
    }
}

// Test Socket.IO connection
function testSocketConnection() {
    console.log('🧪 Testing Socket.IO connection...');

    if (!socket) {
        console.error('❌ Socket.IO not initialized');
        return;
    }

    if (!socket.connected) {
        console.error('❌ Socket.IO not connected');
        return;
    }

    console.log('📡 Sending test message...');
    socket.emit('test_connection', {
        message: 'Test from browser',
        timestamp: new Date().toISOString()
    });

    // Listen for test response
    socket.once('test_response', function(data) {
        console.log('✅ Test response received:', data);
        if (data.error) {
            console.error('❌ Test failed:', data.error);
        } else {
            console.log('🎉 Socket.IO connection test successful!');
        }
    });

    // Timeout for test
    setTimeout(() => {
        console.log('⏰ Test timeout - no response received');
    }, 5000);
}

// Export functions for global access
window.notifications = {
    toggle: toggleNotifications,
    markAllAsRead: markAllAsRead,
    add: addNotification,
    getUnreadCount: () => unreadCount,
    testConnection: testSocketConnection
};

// Make functions globally available
window.toggleNotifications = toggleNotifications;
window.markAllAsRead = markAllAsRead;
window.toggleNotificationSound = toggleNotificationSound;
window.testSocketConnection = testSocketConnection;


