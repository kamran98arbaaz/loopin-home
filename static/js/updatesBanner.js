// Updates Banner System - Shows recent updates from past 24hrs when bell icon is clicked

class UpdatesBanner {
    constructor() {
        this.banner = null;
        this.bannerList = null;
        this.isVisible = false;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.banner = document.getElementById('updates-banner');
        this.bannerList = document.getElementById('updates-banner-list');
        
        // Close banner when clicking outside
        document.addEventListener('click', (event) => {
            const bellContainer = document.querySelector('.notification-container');
            if (this.isVisible && bellContainer && !bellContainer.contains(event.target)) {
                this.closeBanner();
            }
        });

        // Check for recent updates and show badge
        this.checkForRecentUpdatesAndShowBadge();
        
        // Set up periodic checking (every 5 minutes)
        setInterval(() => this.checkForRecentUpdatesAndShowBadge(), 5 * 60 * 1000);
    }

    async toggleBanner() {
        if (this.isVisible) {
            this.closeBanner();
        } else {
            await this.showBanner();
        }
    }

    async showBanner() {
        if (!this.banner || !this.bannerList) return;

        try {
            // Fetch recent updates from the past 24 hours
            const response = await fetch('/api/recent-updates');
            const data = await response.json();

            if (data.success && data.updates) {
                this.populateBanner(data.updates);
                this.banner.style.display = 'block';
                this.isVisible = true;
            } else {
                this.showEmptyBanner();
            }
        } catch (error) {
            console.error('Error fetching recent updates:', error);
            this.showEmptyBanner();
        }
    }

    populateBanner(updates) {
        if (!this.bannerList) return;

        if (updates.length === 0) {
            this.bannerList.innerHTML = `
                <div class="banner-empty-state">
                    <p style="text-align: center; color: var(--gray-500); padding: var(--space-4);">
                        No updates in the past 24 hours
                    </p>
                </div>
            `;
            return;
        }

        // Limit to 3 most recent updates to prevent clutter
        const limitedUpdates = updates.slice(0, 3);

        this.bannerList.innerHTML = limitedUpdates.map(update => `
            <div class="banner-update-item" onclick="goToUpdate('${update.id}')">
                <div class="banner-update-title">${this.truncateText(update.message, 60)}</div>
                <div class="banner-update-meta">
                    <span>${update.name}</span>
                    <span class="banner-update-process">${update.process}</span>
                </div>
            </div>
        `).join('');

        // Add "View All Updates" link if there are more than 3 updates
        if (updates.length > 3) {
            this.bannerList.innerHTML += `
                <div class="banner-view-all" onclick="goToAllUpdates()" style="
                    text-align: center;
                    padding: var(--space-3);
                    border-top: 1px solid var(--gray-200);
                    color: var(--primary-600);
                    cursor: pointer;
                    font-weight: 500;
                    font-size: 0.9rem;
                ">
                    View All Updates (${updates.length} total)
                </div>
            `;
        }
    }

    showEmptyBanner() {
        if (!this.banner || !this.bannerList) return;

        this.bannerList.innerHTML = `
            <div class="banner-empty-state">
                <p style="text-align: center; color: var(--gray-500); padding: var(--space-4);">
                    No recent updates available
                </p>
            </div>
        `;
        this.banner.style.display = 'block';
        this.isVisible = true;
    }

    closeBanner() {
        if (this.banner) {
            this.banner.style.display = 'none';
            this.isVisible = false;
        }
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    async checkForRecentUpdatesAndShowBadge() {
        try {
            const response = await fetch('/api/latest-update-time');
            const data = await response.json();
            
            if (data.success && data.latest_timestamp) {
                const latestTime = new Date(data.latest_timestamp);
                const now = new Date();
                const diffHours = (now - latestTime) / (1000 * 60 * 60);
                
                const badge = document.getElementById('bell-badge');
                
                if (badge) {
                    if (diffHours <= 24) {
                        badge.style.display = 'block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            } else {
                const badge = document.getElementById('bell-badge');
                if (badge) {
                    badge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error checking for recent updates:', error);
            const badge = document.getElementById('bell-badge');
            if (badge) {
                badge.style.display = 'none';
            }
        }
    }
}

// Global functions for HTML onclick handlers
function toggleUpdatesBanner() {
    if (window.updatesBanner) {
        window.updatesBanner.toggleBanner();
    }
}

function closeUpdatesBanner() {
    if (window.updatesBanner) {
        window.updatesBanner.closeBanner();
    }
}

function goToUpdate(updateId) {
    // Close banner first
    if (window.updatesBanner) {
        window.updatesBanner.closeBanner();
    }

    // Navigate to the updates page with highlight
    window.location.href = `/updates?highlight_update=${updateId}`;
}

function goToAllUpdates() {
    // Close banner first
    if (window.updatesBanner) {
        window.updatesBanner.closeBanner();
    }

    // Navigate to the updates page
    window.location.href = '/updates';
}

// Initialize the updates banner
window.updatesBanner = new UpdatesBanner();
