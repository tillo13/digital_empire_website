// Fast Friends Analytics Dashboard - Enhanced JavaScript Functions

// Chart.js configuration
Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
Chart.defaults.color = '#4A5568';

let analyticsData = null;

// Tab switching function
function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Add active class to clicked tab
    event.target.classList.add('active');
    
    // Refresh charts if needed
    if (analyticsData) {
        setTimeout(() => {
            if (tabName === 'subscribers') {
                createSubscriberCharts(analyticsData);
            } else if (tabName === 'engagement') {
                createEngagementCharts(analyticsData);
            } else {
                createVideoCharts(analyticsData);
            }
        }, 100);
    }
}

// Load analytics data
async function loadAnalyticsData() {
    try {
        // Try different possible paths for the JSON file
        let response;
        const possiblePaths = [
            'analytics_data.json',
            './analytics_data.json',
            'fastfriends_data/analytics_data.json'
        ];
        
        for (const path of possiblePaths) {
            try {
                response = await fetch(path);
                if (response.ok) {
                    console.log(`Successfully loaded data from: ${path}`);
                    break;
                }
            } catch (e) {
                console.log(`Failed to load from: ${path}`);
            }
        }
        
        if (!response || !response.ok) {
            throw new Error(`Could not find analytics_data.json in any expected location`);
        }
        
        analyticsData = await response.json();
        
        // Validate that we have the required data structure
        if (!analyticsData.summary || !analyticsData.top_videos) {
            throw new Error('Invalid data structure in analytics_data.json');
        }
        
        populateDashboard(analyticsData);
        createVideoCharts(analyticsData);
        
        // Create other charts based on active tab
        const activeTab = document.querySelector('.tab.active').textContent;
        if (activeTab.includes('Subscriber')) {
            createSubscriberCharts(analyticsData);
        } else if (activeTab.includes('Engagement')) {
            createEngagementCharts(analyticsData);
        }
        
        console.log('Enhanced analytics data loaded successfully:', analyticsData.summary);
        
    } catch (error) {
        console.error('Error loading analytics data:', error);
        document.querySelector('.last-updated').textContent = 'Error loading data - Run the enhanced Python script first!';
        
        // Show error message in main content with more details
        document.getElementById('video-stats-grid').innerHTML = `
            <div class="error-message">
                ❌ Cannot load enhanced analytics data.<br>
                <strong>Details:</strong> ${error.message}<br><br>
                <strong>Solutions:</strong><br>
                1. Make sure you ran the enhanced Python script first<br>
                2. Check that analytics_data.json exists in the same folder<br>
                3. Try refreshing the page
            </div>`;
    }
}

// Populate dashboard with data
function populateDashboard(data) {
    // Update header
    document.querySelector('.last-updated').textContent = `Last updated: ${data.summary.last_updated}`;
    
    // Populate channel info
    const channelInfo = document.getElementById('channel-info');
    if (data.channel_info && data.channel_info.channel_title) {
        channelInfo.innerHTML = `
            <img src="${data.channel_info.channel_thumbnail || ''}" alt="Channel Avatar" class="channel-avatar" onerror="this.style.display='none'">
            <div class="channel-details">
                <div class="channel-name">${data.channel_info.channel_title}</div>
                <div class="channel-stats">${data.channel_info.subscriber_count_formatted} subscribers • ${data.channel_info.video_count_formatted} videos</div>
            </div>
        `;
    }
    
    // Populate enhanced video stats
    const videoStatsGrid = document.getElementById('video-stats-grid');
    videoStatsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.summary.total_videos}</div>
            <div class="stat-label">Videos</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.total_views_formatted}</div>
            <div class="stat-label">Total Views</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_views_per_hour}</div>
            <div class="stat-label">Avg Views/Hour</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_engagement_rate}%</div>
            <div class="stat-label">Engagement Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.viral_videos_10k}</div>
            <div class="stat-label">Viral (10K+)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.viral_rate_10k}%</div>
            <div class="stat-label">Viral Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_like_rate}%</div>
            <div class="stat-label">Like Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_comment_rate}%</div>
            <div class="stat-label">Comment Rate</div>
        </div>
    `;
    
    // Populate subscriber stats
    const subscriberStatsGrid = document.getElementById('subscriber-stats-grid');
    if (data.subscriber_analytics) {
        subscriberStatsGrid.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${data.channel_info.subscriber_count_formatted}</div>
                <div class="stat-label">Current Subscribers</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.subscriber_analytics.total_growth}</div>
                <div class="stat-label">Total Growth</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.subscriber_analytics.avg_growth_per_hour}</div>
                <div class="stat-label">Avg Growth/Hour</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.subscriber_analytics.tracking_duration_hours}h</div>
                <div class="stat-label">Tracking Duration</div>
            </div>
        `;
    }
    
    // Populate engagement stats
    const engagementStatsGrid = document.getElementById('engagement-stats-grid');
    const avgMomentum = data.top_videos.reduce((sum, v) => sum + v.momentum_score, 0) / data.top_videos.length;
    const avgEngagementVelocity = data.top_videos.reduce((sum, v) => sum + v.engagement_per_hour, 0) / data.top_videos.length;
    
    engagementStatsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_engagement_rate}%</div>
            <div class="stat-label">Avg Engagement Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_like_rate}%</div>
            <div class="stat-label">Avg Like Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.summary.avg_comment_rate}%</div>
            <div class="stat-label">Avg Comment Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${avgMomentum.toFixed(1)}</div>
            <div class="stat-label">Avg Momentum Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${avgEngagementVelocity.toFixed(1)}</div>
            <div class="stat-label">Engagement/Hour</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.top_videos.filter(v => v.engagement_rate > data.summary.avg_engagement_rate).length}</div>
            <div class="stat-label">High Engagement Videos</div>
        </div>
    `;
    
    // Populate videos with enhanced metrics
    const videoGrid = document.getElementById('video-grid');
    const maxViewsPerHour = Math.max(...data.top_videos.map(v => v.views_per_hour));
    
    videoGrid.innerHTML = data.top_videos.map((video, index) => `
        <div class="video-card">
            <div class="video-header">
                <div class="video-rank">${index + 1}</div>
                <div class="video-title">${video.title.length > 60 ? video.title.substring(0, 60) + '...' : video.title}</div>
            </div>
            
            <div class="performance-chart">
                <div class="performance-title">Performance Rate</div>
                <div class="performance-value">${video.views_per_hour}</div>
                <div style="font-size: 0.8em; color: #6c757d; margin-bottom: 10px;">views per hour</div>
                <div class="performance-bar">
                    <div class="performance-fill" style="width: ${(video.views_per_hour / maxViewsPerHour) * 100}%"></div>
                </div>
            </div>
            
            <div class="video-metrics">
                <div class="metric">
                    <div class="metric-value">${video.views_formatted}</div>
                    <div class="metric-label">Views</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${video.engagement_rate}%</div>
                    <div class="metric-label">Engagement</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${video.momentum_score}</div>
                    <div class="metric-label">Momentum</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${video.days_since_published}d</div>
                    <div class="metric-label">Age</div>
                </div>
            </div>
        </div>
    `).join('');
    
    // Populate enhanced insights
    const videoInsightsGrid = document.getElementById('video-insights-grid');
    videoInsightsGrid.innerHTML = `
        <div class="insight-card">
            <h3>🎯 Best Posting Times</h3>
            ${data.best_posting_times.map(time => `
                <div class="time-slot">
                    <span>${time.hour_formatted}</span>
                    <span>${time.avg_views_per_hour} v/h</span>
                </div>
            `).join('')}
        </div>
        
        <div class="insight-card">
            <h3>📈 Enhanced Insights</h3>
            <ul class="insights-list">
                ${data.insights.map(insight => `<li>${insight}</li>`).join('')}
                ${data.best_performer ? `<li>🏆 Best performer: ${data.best_performer.title.substring(0, 40)}...</li>` : ''}
            </ul>
        </div>
        
        <div class="insight-card">
            <h3>⏱️ Hourly Performance Insights</h3>
            <ul class="insights-list" id="hourly-performance-insights">
                ${data.hourly_performance_analytics && data.hourly_performance_analytics.insights ? 
                    data.hourly_performance_analytics.insights.map(insight => `<li>${insight}</li>`).join('') : 
                    '<li>📊 Need more historical data - run script multiple times!</li>'
                }
            </ul>
        </div>
    `;
    
    // Populate subscriber insights and timeline
    if (data.subscriber_analytics) {
        const subscriberInsightsGrid = document.getElementById('subscriber-insights-grid');
        subscriberInsightsGrid.innerHTML = `
            <div class="insight-card">
                <h3>📈 Growth Insights</h3>
                <ul class="insights-list">
                    ${data.subscriber_analytics.insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>
        `;
        
        const growthTimeline = document.getElementById('growth-timeline');
        if (data.subscriber_analytics.growth_data && data.subscriber_analytics.growth_data.length > 0) {
            const sortedGrowthData = data.subscriber_analytics.growth_data
                .sort((a, b) => new Date(b.period_end) - new Date(a.period_end))
                .slice(0, 10);
            
            growthTimeline.innerHTML = sortedGrowthData.map(growth => `
                <div class="timeline-item">
                    <div class="timeline-time">${new Date(growth.period_end).toLocaleString()}</div>
                    <div class="timeline-growth ${growth.subscriber_growth < 0 ? 'negative' : ''}">
                        ${growth.subscriber_growth > 0 ? '+' : ''}${growth.subscriber_growth} subscribers
                        (${growth.subs_per_hour}/hour)
                    </div>
                </div>
            `).join('');
        } else {
            growthTimeline.innerHTML = '<p style="text-align: center; color: #718096;">No growth data available yet. Run the script multiple times to build historical data.</p>';
        }
    }
    
    // Populate engagement insights
    const engagementInsightsGrid = document.getElementById('engagement-insights-grid');
    const highEngagementVideos = data.top_videos.filter(v => v.engagement_rate > data.summary.avg_engagement_rate);
    const highMomentumVideos = data.top_videos.filter(v => v.momentum_score > avgMomentum);
    
    engagementInsightsGrid.innerHTML = `
        <div class="insight-card">
            <h3>🔥 High Engagement Content</h3>
            <ul class="insights-list">
                ${highEngagementVideos.slice(0, 3).map(video => 
                    `<li>📹 "${video.title.substring(0, 30)}..." - ${video.engagement_rate}% engagement</li>`
                ).join('')}
            </ul>
        </div>
        
        <div class="insight-card">
            <h3>⚡ Momentum Leaders</h3>
            <ul class="insights-list">
                ${highMomentumVideos.slice(0, 3).map(video => 
                    `<li>🚀 "${video.title.substring(0, 30)}..." - Score: ${video.momentum_score}</li>`
                ).join('')}
            </ul>
        </div>
        
        <div class="insight-card">
            <h3>💡 Engagement Tips</h3>
            <ul class="insights-list">
                <li>🎯 Target ${data.summary.avg_engagement_rate + 1}%+ engagement rate</li>
                <li>👍 Like rate benchmark: ${data.summary.avg_like_rate}%</li>
                <li>💬 Comment rate benchmark: ${data.summary.avg_comment_rate}%</li>
                <li>⚡ Focus on momentum score for new videos</li>
            </ul>
        </div>
    `;
}

// Hourly Performance Insights
function populateHourlyPerformanceInsights(data) {
    const hourlyInsightsContainer = document.getElementById('hourly-performance-insights');
    
    if (!data.hourly_performance_analytics) {
        hourlyInsightsContainer.innerHTML = '<li>📊 Need more historical data - run script multiple times!</li>';
        return;
    }
    
    const insights = data.hourly_performance_analytics.insights;
    hourlyInsightsContainer.innerHTML = insights.map(insight => `<li>${insight}</li>`).join('');
}

// Create video performance charts
function createVideoCharts(data) {
    // Destroy existing charts
    Chart.getChart('topVideosChart')?.destroy();
    Chart.getChart('momentumChart')?.destroy();
    Chart.getChart('postingHoursChart')?.destroy();
    Chart.getChart('dayOfWeekChart')?.destroy();
    
    // Color scheme matching Fast Friends
    const primaryColors = ['#1e3c72', '#2a5298', '#4caf50', '#45a049', '#388e3c'];
    const gradientColors = primaryColors.map(color => color + '80'); // Add transparency
    
    // Top Videos Chart
    const ctx1 = document.getElementById('topVideosChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: data.chart_data.top_videos_chart.labels,
            datasets: [{
                label: 'Views/Hour',
                data: data.chart_data.top_videos_chart.data,
                backgroundColor: gradientColors,
                borderColor: primaryColors,
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f3f4' } },
                x: { ticks: { maxRotation: 45 }, grid: { display: false } }
            }
        }
    });
    
    // Momentum Chart
    const ctx2 = document.getElementById('momentumChart').getContext('2d');
    new Chart(ctx2, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Video Momentum',
                data: data.chart_data.momentum_chart.data.map((momentum, index) => ({
                    x: data.chart_data.momentum_chart.ages[index],
                    y: momentum,
                    title: data.chart_data.momentum_chart.labels[index]
                })),
                backgroundColor: function(context) {
                    const age = context.parsed.x;
                    if (age <= 7) return 'rgba(76, 175, 80, 0.8)';  // Green for recent
                    if (age <= 30) return 'rgba(42, 82, 152, 0.8)'; // Blue for medium
                    return 'rgba(158, 158, 158, 0.8)';               // Gray for old
                },
                pointRadius: 8,
                pointHoverRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].raw.title;
                        },
                        label: function(context) {
                            return `Momentum: ${context.parsed.y.toFixed(1)} | Age: ${context.parsed.x.toFixed(1)} days`;
                        }
                    }
                }
            },
            scales: {
                x: { 
                    title: { display: true, text: 'Days Since Published' },
                    grid: { color: '#f1f3f4' }
                },
                y: { 
                    title: { display: true, text: 'Momentum Score' },
                    grid: { color: '#f1f3f4' }
                }
            }
        }
    });
    
    // Posting Hours Chart
    const ctx3 = document.getElementById('postingHoursChart').getContext('2d');
    new Chart(ctx3, {
        type: 'bar',
        data: {
            labels: data.chart_data.hourly_chart.labels,
            datasets: [{
                label: 'Avg Views/Hour',
                data: data.chart_data.hourly_chart.data,
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    if (value >= 100) return '#4caf50';
                    if (value >= 50) return '#2a5298';
                    return '#e0e0e0';
                },
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Views/Hour' }, grid: { color: '#f1f3f4' } },
                x: { title: { display: true, text: 'Hour of Day' }, grid: { display: false } }
            }
        }
    });
    
    // Day of Week Chart
    const ctx4 = document.getElementById('dayOfWeekChart').getContext('2d');
    new Chart(ctx4, {
        type: 'line',
        data: {
            labels: data.chart_data.daily_chart.labels,
            datasets: [{
                label: 'Avg Views/Hour',
                data: data.chart_data.daily_chart.data,
                borderColor: '#2a5298',
                backgroundColor: 'rgba(42, 82, 152, 0.1)',
                borderWidth: 4,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#2a5298',
                pointBorderColor: '#fff',
                pointBorderWidth: 3,
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Views/Hour' }, grid: { color: '#f1f3f4' } },
                x: { grid: { display: false } }
            }
        }
    });
    
    // Create hourly performance chart
    createHourlyPerformanceChart(data);
}

// Add hourly performance insights to dashboard population
function populateHourlyPerformanceInsights(data) {
    const hourlyInsightsContainer = document.getElementById('hourly-performance-insights');
    
    if (!data.hourly_performance_analytics) {
        hourlyInsightsContainer.innerHTML = '<li>📊 Need more historical data - run script multiple times!</li>';
        return;
    }
    
    const insights = data.hourly_performance_analytics.insights;
    hourlyInsightsContainer.innerHTML = insights.map(insight => `<li>${insight}</li>`).join('');
}

// Create hourly performance chart
function createHourlyPerformanceChart(data) {
    Chart.getChart('hourlyPerformanceChart')?.destroy();
    
    if (!data.hourly_performance_analytics || data.hourly_performance_analytics.data_quality === 'insufficient') {
        const canvas = document.getElementById('hourlyPerformanceChart');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Segoe UI';
        ctx.textAlign = 'center';
        ctx.fillText('Need more data - run script multiple times!', canvas.width/2, canvas.height/2);
        
        document.getElementById('hourlyPerformanceInfo').textContent = 
            `Need ${20 - (data.hourly_performance_analytics?.total_gain_records || 0)} more snapshots for reliable data`;
        return;
    }
    
    const hourlyData = data.hourly_performance_analytics.hourly_averages;
    const ctx = document.getElementById('hourlyPerformanceChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hourlyData.map(h => h.hour_formatted),
            datasets: [{
                label: 'Avg Views Gained/Hour',
                data: hourlyData.map(h => h.avg_views_per_hour),
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    const measurements = hourlyData[context.dataIndex].measurement_count;
                    
                    if (measurements === 0) return '#f5f5f5';
                    if (measurements < 3) return '#ffeb3b';
                    if (value >= 50) return '#4caf50';
                    if (value >= 20) return '#2a5298';
                    return '#e0e0e0';
                },
                borderColor: function(context) {
                    const measurements = hourlyData[context.dataIndex].measurement_count;
                    return measurements >= 3 ? '#333' : '#999';
                },
                borderWidth: function(context) {
                    const measurements = hourlyData[context.dataIndex].measurement_count;
                    return measurements >= 3 ? 2 : 1;
                },
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const hourData = hourlyData[context.dataIndex];
                            return [
                                `Avg Views/Hour: ${hourData.avg_views_per_hour}`,
                                `Measurements: ${hourData.measurement_count}`,
                                `Total Views Gained: ${hourData.total_views_gained}`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: true, 
                    title: { display: true, text: 'Views Gained/Hour' },
                    grid: { color: '#f1f3f4' }
                },
                x: { 
                    title: { display: true, text: 'Hour of Day' },
                    grid: { display: false }
                }
            }
        }
    });
    
    // Update info
    const totalSnapshots = data.hourly_performance_analytics.total_snapshots;
    const totalRecords = data.hourly_performance_analytics.total_gain_records;
    document.getElementById('hourlyPerformanceInfo').textContent = 
        `Based on ${totalRecords} measurements from ${totalSnapshots} snapshots`;
}

// Create engagement charts
function createEngagementCharts(data) {
    // Destroy existing charts
    Chart.getChart('engagementChart')?.destroy();
    Chart.getChart('likeCommentChart')?.destroy();
    Chart.getChart('engagementVelocityChart')?.destroy();
    Chart.getChart('freshnessChart')?.destroy();
    
    // Engagement Rate Chart
    const ctx1 = document.getElementById('engagementChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: data.chart_data.engagement_chart.labels,
            datasets: [{
                label: 'Engagement Rate (%)',
                data: data.chart_data.engagement_chart.data,
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    if (value >= 5) return '#4caf50';
                    if (value >= 2) return '#2a5298';
                    return '#e0e0e0';
                },
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { 
                    beginAtZero: true, 
                    title: { display: true, text: 'Engagement Rate (%)' },
                    grid: { color: '#f1f3f4' }
                },
                x: { 
                    ticks: { maxRotation: 45 }, 
                    grid: { display: false } 
                }
            }
        }
    });
    
    // Like vs Comment Chart
    const ctx2 = document.getElementById('likeCommentChart').getContext('2d');
    new Chart(ctx2, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Videos',
                data: data.top_videos.map(v => ({
                    x: v.like_rate,
                    y: v.comment_rate,
                    title: v.title.substring(0, 30)
                })),
                backgroundColor: 'rgba(42, 82, 152, 0.6)',
                borderColor: '#2a5298',
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].raw.title;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Like Rate (%)' } },
                y: { title: { display: true, text: 'Comment Rate (%)' } }
            }
        }
    });
    
    // Engagement Velocity Chart
    const ctx3 = document.getElementById('engagementVelocityChart').getContext('2d');
    new Chart(ctx3, {
        type: 'line',
        data: {
            labels: data.top_videos.slice(0, 8).map(v => v.title.substring(0, 15) + '...'),
            datasets: [{
                label: 'Engagement/Hour',
                data: data.top_videos.slice(0, 8).map(v => v.engagement_per_hour),
                borderColor: '#4caf50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Engagement/Hour' } }
            }
        }
    });
    
    // Freshness Chart
    const ctx4 = document.getElementById('freshnessChart').getContext('2d');
    new Chart(ctx4, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Content Freshness',
                data: data.top_videos.map(v => ({
                    x: v.days_since_published,
                    y: v.freshness_factor,
                    title: v.title.substring(0, 30)
                })),
                backgroundColor: function(context) {
                    const freshness = context.parsed.y;
                    if (freshness > 0.5) return 'rgba(76, 175, 80, 0.8)';
                    if (freshness > 0.2) return 'rgba(42, 82, 152, 0.8)';
                    return 'rgba(158, 158, 158, 0.8)';
                },
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].raw.title;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Days Since Published' } },
                y: { title: { display: true, text: 'Freshness Factor' } }
            }
        }
    });
}

// Create subscriber charts
function createSubscriberCharts(data) {
    if (!data.subscriber_analytics) return;
    
    // Destroy existing charts
    Chart.getChart('subscriberGrowthChart')?.destroy();
    Chart.getChart('subscriberDayChart')?.destroy();
    Chart.getChart('subscriberTimelineChart')?.destroy();
    
    // Subscriber Growth by Hour Chart
    const ctx1 = document.getElementById('subscriberGrowthChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: data.chart_data.subscriber_growth_chart.labels,
            datasets: [{
                label: 'Avg Subs/Hour',
                data: data.chart_data.subscriber_growth_chart.data,
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    if (value > 0) return 'rgba(76, 175, 80, 0.8)';
                    if (value < 0) return 'rgba(244, 67, 54, 0.8)';
                    return 'rgba(224, 224, 224, 0.8)';
                },
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { 
                    beginAtZero: true, 
                    title: { display: true, text: 'Subscribers/Hour' },
                    grid: { color: '#f1f3f4' }
                },
                x: { title: { display: true, text: 'Hour of Day' }, grid: { display: false } }
            }
        }
    });
    
    // Subscriber Growth by Day Chart
    const ctx2 = document.getElementById('subscriberDayChart').getContext('2d');
    new Chart(ctx2, {
        type: 'line',
        data: {
            labels: data.subscriber_analytics.daily_growth.day_names,
            datasets: [{
                label: 'Avg Subs/Hour',
                data: data.subscriber_analytics.daily_growth.averages,
                borderColor: '#4caf50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 4,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#4caf50',
                pointBorderColor: '#fff',
                pointBorderWidth: 3,
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { 
                    beginAtZero: true, 
                    title: { display: true, text: 'Subscribers/Hour' },
                    grid: { color: '#f1f3f4' }
                },
                x: { grid: { display: false } }
            }
        }
    });
    
    // Subscriber Timeline Chart
    const ctx3 = document.getElementById('subscriberTimelineChart').getContext('2d');
    if (data.chart_data.subscriber_timeline && data.chart_data.subscriber_timeline.length > 0) {
        new Chart(ctx3, {
            type: 'line',
            data: {
                labels: data.chart_data.subscriber_timeline.map(item => 
                    new Date(item.period_end).toLocaleDateString()
                ),
                datasets: [{
                    label: 'Subscriber Count',
                    data: data.chart_data.subscriber_timeline.map(item => item.end_subs),
                    borderColor: '#2a5298',
                    backgroundColor: 'rgba(42, 82, 152, 0.1)',
                    borderWidth: 4,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#2a5298',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 3,
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { 
                        title: { display: true, text: 'Subscriber Count' },
                        grid: { color: '#f1f3f4' }
                    },
                    x: { 
                        title: { display: true, text: 'Date' },
                        grid: { display: false }
                    }
                }
            }
        });
    }
}

// Initialize when page loads
window.addEventListener('load', loadAnalyticsData);

// Auto-refresh every 5 minutes
setInterval(loadAnalyticsData, 5 * 60 * 1000);