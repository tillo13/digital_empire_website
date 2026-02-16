// Digital Empire Network - Professional Scripts

// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const body = document.body;
    
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
    
    // Prevent body scroll when sidebar is open
    if (sidebar.classList.contains('open')) {
        body.style.overflow = 'hidden';
    } else {
        body.style.overflow = '';
    }
}

// Close sidebar when clicking outside
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const menuButton = document.querySelector('.menu-button');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && sidebar.classList.contains('open') && 
        !sidebar.contains(e.target) && 
        menuButton && !menuButton.contains(e.target)) {
        toggleSidebar();
    }
});

// Keyword pills functionality
let currentFilter = 'all';

function filterContent(filter) {
    currentFilter = filter;
    
    // Update active pill
    document.querySelectorAll('.pill').forEach(pill => {
        pill.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Show notification (in real app, this would filter content)
    showNotification(`Filtering by: ${filter.replace('-', ' ')}`, false);
    
    // You could implement actual filtering here
    // For example, hiding/showing channels based on tags
}

// Scroll pills horizontally
function scrollPills(direction) {
    const pillsContainer = document.querySelector('.keyword-pills');
    const scrollAmount = 200;
    
    if (direction === -1) {
        pillsContainer.scrollLeft -= scrollAmount;
    } else {
        pillsContainer.scrollLeft += scrollAmount;
    }
}

// Check if pills need navigation buttons
function checkPillsScroll() {
    const container = document.querySelector('.keyword-pills');
    const leftButton = document.querySelector('.pills-nav-left');
    const rightButton = document.querySelector('.pills-nav-right');
    
    if (!container) return;
    
    // Show/hide navigation buttons based on scroll position
    if (container.scrollLeft > 0) {
        leftButton.style.opacity = '1';
    } else {
        leftButton.style.opacity = '0';
    }
    
    if (container.scrollLeft < container.scrollWidth - container.clientWidth - 1) {
        rightButton.style.opacity = '1';
    } else {
        rightButton.style.opacity = '0';
    }
}

// Initialize pills scroll check
document.addEventListener('DOMContentLoaded', () => {
    const pillsContainer = document.querySelector('.keyword-pills');
    if (pillsContainer) {
        pillsContainer.addEventListener('scroll', checkPillsScroll);
        checkPillsScroll();
    }
});

// Show notification
function showNotification(message, isError = false) {
    const notification = document.getElementById('notification');
    const textElement = notification.querySelector('.notification-text');
    textElement.textContent = message;
    
    if (isError) {
        notification.classList.add('error');
    } else {
        notification.classList.remove('error');
    }
    
    notification.classList.add('show');
    
    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Enhanced search functionality - redirect to home with filter
function handleSearch(searchQuery) {
    if (!searchQuery.trim()) return;
    
    // Show filtering notification
    showNotification(`Searching for "${searchQuery}"...`, false);
    
    // If not on home page, redirect to home with search query
    const currentPath = window.location.pathname;
    if (currentPath !== '/' && currentPath !== '/index' && currentPath !== '/home') {
        // Store search query and redirect to home
        sessionStorage.setItem('searchQuery', searchQuery);
        setTimeout(() => {
            window.location.href = `/?search=${encodeURIComponent(searchQuery)}`;
        }, 1000);
    } else {
        // Already on home page - simulate filtering and scroll to channels
        setTimeout(() => {
            showNotification(`Showing results for "${searchQuery}"`, false);
            // Highlight matching channels
            highlightSearchResults(searchQuery);
            // Scroll to channel section
            scrollToChannelSection();
        }, 1000);
    }
}

// Scroll to the channel portfolio section
function scrollToChannelSection() {
    const channelSection = document.querySelector('.network-section') || 
                          document.querySelector('.channels-grid') || 
                          document.querySelector('.section-title');
    
    if (channelSection) {
        const headerHeight = 56; // Fixed header height
        const elementPosition = channelSection.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerHeight - 20; // Extra 20px padding
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

// Highlight search results on home page
function highlightSearchResults(query) {
    const channelCards = document.querySelectorAll('.channel-card');
    const searchTerm = query.toLowerCase();
    
    channelCards.forEach(card => {
        const channelTitle = card.querySelector('.channel-title')?.textContent.toLowerCase() || '';
        const channelDescription = card.querySelector('.channel-description')?.textContent.toLowerCase() || '';
        
        // Simple matching - show/highlight relevant channels
        if (channelTitle.includes(searchTerm) || channelDescription.includes(searchTerm)) {
            card.style.border = '2px solid var(--yt-spec-brand-red)';
            card.style.backgroundColor = 'rgba(255, 0, 0, 0.05)';
            
            // Remove highlight after a few seconds
            setTimeout(() => {
                card.style.border = '';
                card.style.backgroundColor = '';
            }, 5000);
        }
    });
}

// Check for search query on page load
function checkForSearchQuery() {
    // Check URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const urlSearch = urlParams.get('search');
    
    // Check session storage
    const sessionSearch = sessionStorage.getItem('searchQuery');
    
    if (urlSearch || sessionSearch) {
        const searchQuery = urlSearch || sessionSearch;
        
        // Clear session storage
        sessionStorage.removeItem('searchQuery');
        
        // Show search results and scroll to channels
        setTimeout(() => {
            showNotification(`Showing results for "${searchQuery}"`, false);
            highlightSearchResults(searchQuery);
            // Scroll to channel section after a brief delay
            setTimeout(() => {
                scrollToChannelSection();
            }, 500);
        }, 500);
        
        // Update search input if present
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.value = searchQuery;
        }
    }
}

// Refresh data function
async function refreshData() {
    // Show notification
    showNotification('Updating channel data...', false);
    
    try {
        // Start refresh
        const response = await fetch('/api/refresh');
        const data = await response.json();
        
        // Poll for completion
        let attempts = 0;
        const maxAttempts = 30; // 30 seconds max
        
        const checkStatus = async () => {
            const statusResponse = await fetch('/api/status');
            const status = await statusResponse.json();
            
            if (status.has_data && !status.update_in_progress) {
                // Refresh complete
                showNotification('Data updated successfully!', false);
                
                // Reload page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else if (attempts < maxAttempts) {
                attempts++;
                setTimeout(checkStatus, 1000); // Check every second
            } else {
                // Timeout
                showNotification('Update is taking longer than expected. Please try again.', true);
            }
        };
        
        // Start checking after 1 second
        setTimeout(checkStatus, 1000);
        
    } catch (error) {
        console.error('Error refreshing data:', error);
        showNotification('Failed to refresh data. Please try again.', true);
    }
}

// Scroll to partnership section
function scrollToPartnership() {
    const element = document.getElementById('partnership');
    if (element) {
        const headerHeight = 56; // Fixed header height
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerHeight;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

// Download media kit (placeholder)
function downloadMediaKit() {
    showNotification('Media kit download starting...', false);
    // In production, this would trigger an actual download
    setTimeout(() => {
        window.location.href = '/contact';
    }, 1000);
}

// Auto-refresh every hour
setInterval(() => {
    refreshData();
}, 3600000); // 1 hour

// Add smooth scrolling for all anchor links
document.addEventListener('DOMContentLoaded', () => {
    // Check for search query on page load
    checkForSearchQuery();
    
    // Handle search form with new functionality
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const searchInput = searchForm.querySelector('.search-input');
            const searchQuery = searchInput.value.trim();
            
            if (searchQuery) {
                handleSearch(searchQuery);
            }
        });
    }
    
    // Smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerHeight = 56;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerHeight;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                entry.target.classList.add('animated');
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.channel-card, .impact-stat, .partnership-card, .video-tile');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    // Add loading animation to images
    document.querySelectorAll('img').forEach(img => {
        if (img.complete) {
            img.style.opacity = '1';
        } else {
            img.style.opacity = '0';
            img.style.transition = 'opacity 0.3s ease';
            img.addEventListener('load', function() {
                this.style.opacity = '1';
            });
            img.addEventListener('error', function() {
                this.style.opacity = '0.5';
                this.style.filter = 'grayscale(1)';
            });
        }
    });
    
    // Add hover effect to channel cards
    const channelCards = document.querySelectorAll('.channel-card');
    channelCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        card.addEventListener('mouseleave', function() {
            if (this.classList.contains('animated')) {
                this.style.transform = 'translateY(0)';
            }
        });
    });
    
    // Handle partner button click
    const partnerButton = document.querySelector('.partner-button');
    if (partnerButton && partnerButton.textContent === 'Partner With Us') {
        partnerButton.addEventListener('click', scrollToPartnership);
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Press 'R' to refresh
        if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
            const activeElement = document.activeElement;
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                e.preventDefault();
                refreshData();
            }
        }
        
        // Press '/' to focus search
        if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
            const activeElement = document.activeElement;
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        }
        
        // Press Enter in search to trigger search
        if (e.key === 'Enter' && e.target.classList.contains('search-input')) {
            e.preventDefault();
            const searchQuery = e.target.value.trim();
            if (searchQuery) {
                handleSearch(searchQuery);
            }
        }
    });
    
    // Format relative time for any timestamps
    function formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        const intervals = {
            year: 31536000,
            month: 2592000,
            week: 604800,
            day: 86400,
            hour: 3600,
            minute: 60
        };
        
        for (const [unit, secondsInUnit] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / secondsInUnit);
            if (interval >= 1) {
                return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
            }
        }
        
        return 'Just now';
    }
    
    // Add click tracking for analytics (placeholder)
    document.querySelectorAll('.channel-link, .video-tile, .cta-primary, .cta-secondary').forEach(link => {
        link.addEventListener('click', function() {
            const action = this.classList.contains('channel-link') ? 'channel_visit' : 
                          this.classList.contains('video-tile') ? 'video_click' :
                          this.classList.contains('cta-primary') ? 'partnership_primary' :
                          'partnership_secondary';
            
            // In production, this would send to analytics
            console.log('Track event:', action, this.href || this.textContent);
        });
    });
    
    // Check for URL parameters (for tracking campaigns)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('ref')) {
        const referrer = urlParams.get('ref');
        console.log('Referrer:', referrer);
        // Track campaign source
    }
    
    // Lazy load images that are below the fold
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Add parallax effect to hero background
    let ticking = false;
    function updateParallax() {
        const scrolled = window.pageYOffset;
        const heroBackground = document.querySelector('.hero-background');
        if (heroBackground) {
            const speed = 0.5;
            heroBackground.style.transform = `translateY(${scrolled * speed}px)`;
        }
        ticking = false;
    }
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(updateParallax);
            ticking = true;
        }
    });
    
    // Initialize tooltips for trust badges
    const trustBadges = document.querySelectorAll('.trust-badge');
    trustBadges.forEach(badge => {
        badge.style.cursor = 'help';
        badge.title = 'Digital Empire Network is a verified YouTube partner with brand-safe content';
    });
    
    // Performance monitoring
    if ('PerformanceObserver' in window) {
        try {
            const perfObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.entryType === 'largest-contentful-paint') {
                        console.log('LCP:', entry.startTime);
                    }
                }
            });
            perfObserver.observe({ entryTypes: ['largest-contentful-paint'] });
        } catch (e) {
            // Fail silently if not supported
        }
    }
});

// Export functions for global use
window.toggleSidebar = toggleSidebar;
window.refreshData = refreshData;
window.scrollToPartnership = scrollToPartnership;
window.downloadMediaKit = downloadMediaKit;
window.showNotification = showNotification;
window.filterContent = filterContent;
window.scrollPills = scrollPills;
window.handleSearch = handleSearch;
window.scrollToChannelSection = scrollToChannelSection;