#!/usr/bin/env python3
"""
Digital Empire Network - Main Application (Static Data on Startup)
Uses static channel_data.json on startup, API refresh available when needed
"""

import html as html_mod
import os
import json
import datetime
import threading
import time
import logging
import sys
from typing import Dict, Any, Optional

from flask import Flask, render_template, jsonify, request, Response
from dotenv import load_dotenv

# Add these imports at the top of main.py (if not already present)
from utilities.gmail_utils import send_partnership_inquiry_notification

# Import our utilities
from utilities.youtube_utils import (
    get_all_channels_data,
    calculate_network_totals,
    YouTubeClient,
    CHANNEL_MAPPINGS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('DigitalEmpire')

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global cache for channel data
channel_cache = {
    'data': None,
    'last_updated': None,
    'update_in_progress': False,
    'lock': threading.Lock()
}

# Configuration
CACHE_DURATION = 3600  # 1 hour


def get_api_key() -> Optional[str]:
    """Retrieve API key from various sources"""
    # Try Google Secret Manager first
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/digital-empire-461123/secrets/yt-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8")
        logger.info("Successfully retrieved API key from Secret Manager")
        return api_key
    except Exception as e:
        logger.debug(f"Secret Manager not available: {e}")
    
    # Fall back to environment variables
    load_dotenv()
    
    for env_name in ['YT_API_KEY', 'YOUTUBE_API_KEY', 'API_KEY']:
        api_key = os.getenv(env_name)
        if api_key:
            logger.info(f"API key found in environment variable: {env_name}")
            return api_key
    
    logger.error("No API key found in any source!")
    return None


def load_static_data() -> Optional[Dict[str, Any]]:
    """Load static channel data from JSON file"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'channel_data.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded static data from {json_path}")
                
                # Ensure all expected fields exist
                ensure_data_fields(data)
                return data
    except Exception as e:
        logger.error(f"Error loading static data: {e}")
    return None

def ensure_data_fields(data: Dict[str, Any]) -> None:
    """Ensure all expected fields exist in the data"""
    # Add any missing fields with defaults
    if 'totals' in data:
        totals = data['totals']
        
        # Ensure all expected totals fields exist
        defaults = {
            'monthly_reach_formatted': 'N/A',
            'actual_monthly_views_formatted': 'N/A',
            'viral_videos': 0,
            'million_view_videos': 0,
            'uploads_per_month': 0,
            'avg_views_per_subscriber': 0,
            'audience_quality_score': 0,
            'years_active': 0,
            'active_community': 0,
            'active_community_formatted': '0'
        }
        
        for key, default_value in defaults.items():
            if key not in totals:
                totals[key] = default_value
    
    # Ensure channel fields
    if 'channels' in data:
        for channel in data['channels']:
            channel_defaults = {
                'monthly_reach_formatted': 'N/A',
                'viral_videos': 0,
                'million_view_videos': 0,
                'performance_tier': 'N/A',
                'tier_icon': '—',
                'upload_schedule': 'N/A',
                'upload_icon': '—',
                'loyalty_index': 0,
                'years_active': 0,
                'videos_per_month': 0,
                'videos_per_year': 0,
                'engagement_rate': 0.0,  # ADD THIS
                'comment_rate': 0.0,      # ADD THIS
                'like_rate': 0.0,         # ADD THIS
                'total_comments': 0,      # ADD THIS
                'total_likes': 0,         # ADD THIS
                'total_comments_formatted': '0',  # ADD THIS
                'total_likes_formatted': '0'      # ADD THIS
            }
            
            for key, default_value in channel_defaults.items():
                if key not in channel:
                    channel[key] = default_value


def update_channel_data() -> None:
    """Update all channel data using YouTube utilities (ONLY when manually called)"""
    global channel_cache
    
    with channel_cache['lock']:
        if channel_cache['update_in_progress']:
            logger.warning("Update already in progress, skipping")
            return
        channel_cache['update_in_progress'] = True
    
    logger.info("=" * 60)
    logger.info("Starting Digital Empire Network data update...")
    logger.info("=" * 60)
    
    try:
        # Get API key
        api_key = get_api_key()
        if not api_key:
            raise ValueError("No YouTube API key available")
        
        # Fetch all channel data using utilities
        all_channel_data, errors = get_all_channels_data(api_key)
        
        # Sort by views (descending)
        all_channel_data.sort(key=lambda x: x['view_count'], reverse=True)
        
        # Calculate totals
        totals = calculate_network_totals(all_channel_data)
        
        # Update cache
        with channel_cache['lock']:
            channel_cache['data'] = {
                'channels': all_channel_data,
                'totals': totals,
                'last_updated': datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                'errors': errors if errors else None,
                'update_time': datetime.datetime.now().isoformat()
            }
            channel_cache['last_updated'] = datetime.datetime.now()
        
        # Log summary with REAL metrics
        logger.info("=" * 60)
        logger.info(f"Update completed successfully!")
        logger.info(f"Total channels: {totals['channels']}")
        logger.info(f"Total views: {totals['views_formatted']}")
        logger.info(f"Total subscribers: {totals['subscribers_formatted']}")
        logger.info(f"Network age: {totals['years_active']} years")
        logger.info(f"Monthly reach: {totals.get('monthly_reach_formatted', 'N/A')}")
        logger.info(f"Viral videos: {totals.get('viral_videos', 0)}")
        if errors:
            logger.warning(f"Errors encountered: {len(errors)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error during update: {str(e)}", exc_info=True)
        
        # If API update fails, keep the existing static data
        if not channel_cache['data']:
            static_data = load_static_data()
            if static_data:
                with channel_cache['lock']:
                    channel_cache['data'] = static_data
                    channel_cache['last_updated'] = datetime.datetime.now()
            else:
                with channel_cache['lock']:
                    channel_cache['data'] = {
                        'channels': [],
                        'totals': {
                            'subscribers_formatted': '0',
                            'views_formatted': '0',
                            'videos_formatted': '0',
                            'channels': 0,
                            'years_active': 0,
                            'monthly_reach_formatted': 'N/A',
                            'viral_videos': 0,
                            'audience_quality_score': 0
                        },
                        'last_updated': f'Error: {str(e)}',
                        'errors': [str(e)]
                    }
    
    finally:
        with channel_cache['lock']:
            channel_cache['update_in_progress'] = False


def get_cache_data() -> Dict[str, Any]:
    """Get cached data or return static/default structure"""
    with channel_cache['lock']:
        if channel_cache['data']:
            return channel_cache['data']
    
    # Try static data
    static_data = load_static_data()
    if static_data:
        return static_data
    
    # Return default with real structure
    return {
        'channels': [],
        'totals': {
            'subscribers_formatted': '0',
            'views_formatted': '0',
            'videos_formatted': '0',
            'channels': 0,
            'years_active': 0,
            'monthly_reach_formatted': 'N/A',
            'actual_monthly_views_formatted': 'N/A',
            'viral_videos': 0,
            'million_view_videos': 0,
            'uploads_per_month': 0,
            'avg_views_per_subscriber': 0,
            'audience_quality_score': 0
        },
        'last_updated': 'Loading...',
        'errors': None
    }


def should_update_cache() -> bool:
    """Check if cache needs updating (DISABLED for startup - only manual refresh)"""
    # CHANGED: Always return False so we never auto-update on startup
    # The cache will only update when manually refreshed via /api/refresh
    return False


# Flask Routes
@app.route('/sitemap.xml')
def sitemap():
    host = request.host_url.rstrip('/')
    skip = {'api', 'admin', 'auth', 'login', 'logout', 'callback', 'health', 'sitemap', 'robots', 'tasks', 'cron', 'debug'}
    urls = []
    for rule in app.url_map.iter_rules():
        if 'GET' not in rule.methods or rule.arguments:
            continue
        path = rule.rule
        parts = path.strip('/').split('/')
        if any(p in skip for p in parts):
            continue
        if path.startswith('/api/') or path.startswith('/admin') or path.startswith('/static'):
            continue
        priority = '1.0' if path == '/' else '0.6'
        urls.append(f'  <url><loc>{host}{path}</loc><priority>{priority}</priority></url>')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(sorted(urls)) + '\n</urlset>'
    return Response(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    host = request.host_url.rstrip('/')
    content = f'User-agent: *\nAllow: /\nSitemap: {host}/sitemap.xml\n'
    return Response(content, mimetype='text/plain')

@app.route('/')
def index():
    """Main page - Always use static data, no background updates"""
    logger.info(f"Index page requested from {request.remote_addr}")
    
    # CHANGED: Simply load static data, no background refresh on startup
    data = get_cache_data()
    logger.info(f"Rendering page with {len(data.get('channels', []))} channels (using static data)")
    return render_template('index.html', data=data)


@app.route('/api/refresh')
def refresh_data():
    """Force refresh of channel data (ONLY way to update data)"""
    logger.info("Manual refresh requested via API")
    
    thread = threading.Thread(target=update_channel_data)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'refresh_started',
        'message': 'Channel data refresh initiated',
        'timestamp': datetime.datetime.now().isoformat()
    })


@app.route('/api/status')
def api_status():
    """Get current system status"""
    with channel_cache['lock']:
        status = {
            'has_data': channel_cache['data'] is not None,
            'last_updated': channel_cache['last_updated'].isoformat() if channel_cache['last_updated'] else None,
            'update_in_progress': channel_cache['update_in_progress'],
            'cache_age_seconds': (datetime.datetime.now() - channel_cache['last_updated']).seconds if channel_cache['last_updated'] else None,
            'channel_count': len(channel_cache['data']['channels']) if channel_cache['data'] else 0,
            'using_static_data': channel_cache['data'] is None  # True if using static file
        }
    return jsonify(status)


@app.route('/api/channels')
def api_channels():
    """Get all channel data as JSON"""
    data = get_cache_data()
    return jsonify({
        'channels': data['channels'],
        'totals': data['totals'],
        'last_updated': data['last_updated']
    })


@app.route('/api/analytics/<channel_name>')
def channel_analytics(channel_name: str):
    """Get detailed analytics for a specific channel"""
    data = get_cache_data()
    
    # Find channel
    channel = next((ch for ch in data['channels'] if ch['display_name'].lower() == channel_name.lower()), None)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    # Return real analytics
    analytics = {
        'channel': channel,
        'performance': {
            'views_per_video': channel.get('avg_views_per_video', 0),
            'monthly_reach': channel.get('monthly_reach', 0),
            'viral_videos': channel.get('viral_videos', 0),
            'performance_tier': channel.get('performance_tier', 'N/A'),
            'upload_frequency': channel.get('upload_schedule', 'N/A'),
            'years_active': channel.get('years_active', 0)
        },
        'engagement': {
            'total_comments': channel.get('total_comments', 0),
            'total_likes': channel.get('total_likes', 0),
            'comment_rate': channel.get('comment_rate', 0),
            'like_rate': channel.get('like_rate', 0),
            'loyalty_index': channel.get('loyalty_index', 0)
        },
        'growth_metrics': {
            'videos_per_month': channel.get('videos_per_month', 0),
            'videos_per_year': channel.get('videos_per_year', 0),
            'subscriber_velocity': 'Calculate based on historical data'
        }
    }
    
    return jsonify(analytics)


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'digital-empire-network',
        'timestamp': datetime.datetime.now().isoformat(),
        'channels_configured': len(CHANNEL_MAPPINGS),
        'using_static_data': True  # Always true on startup now
    })


# Background scheduler (DISABLED for auto-refresh)
def schedule_updates():
    """Schedule periodic updates (DISABLED - only manual refresh allowed)"""
    # CHANGED: Removed auto-refresh. Only manual refresh via /api/refresh
    while True:
        time.sleep(CACHE_DURATION * 24)  # Sleep for 24 hours instead of refreshing
        logger.debug("Auto-refresh disabled - use /api/refresh to update data manually")


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/contact')
def contact():
    """Contact page"""
    data = get_cache_data()
    return render_template('contact.html', data=data)


@app.route('/api/contact', methods=['POST'])
def api_contact():
    """Handle contact form submission with spam protection."""
    try:
        data = request.json

        # Spam guard (shared across all kumori sites)
        from utilities.spam_guard import check_spam
        spam_reason = check_spam(data, request.remote_addr)
        if spam_reason:
            logger.warning(f"Spam blocked: {spam_reason} from {request.remote_addr}")
            return jsonify({'status': 'error', 'message': 'Invalid submission'}), 400

        # Validate required fields
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Create formatted message (escape user input to prevent XSS)
        esc = html_mod.escape
        formatted_message = f"""
        <h3>Contact Form Submission</h3>
        <p><strong>Name:</strong> {esc(data.get('name'))}</p>
        <p><strong>Company:</strong> {esc(data.get('company', 'Not provided'))}</p>
        <p><strong>Email:</strong> {esc(data.get('email'))}</p>
        <p><strong>Subject:</strong> {esc(data.get('subject'))}</p>
        <p><strong>Message:</strong></p>
        <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px;">
            {esc(data.get('message')).replace(chr(10), '<br>')}
        </div>
        """
        
        # Send notification email
        success = send_partnership_inquiry_notification(
            company_name=data.get('company', data.get('name')),
            contact_email=data.get('email'),
            message=formatted_message
        )
        
        if success:
            logger.info(f"Contact form submitted successfully from {data.get('email')}")
            return jsonify({
                'status': 'success',
                'message': 'Thank you for your message! We\'ll respond within 24 hours.'
            })
        else:
            raise Exception("Failed to send email")
            
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Sorry, there was an error sending your message. Please try again later.'
        }), 500


@app.route('/about')
def about():
    """About page"""
    data = get_cache_data()
    return render_template('about.html', data=data)

@app.route('/media_kit')
def media_kit():
    """Media Kit page"""
    data = get_cache_data()
    return render_template('media_kit.html', data=data)

# Main entry point
if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Digital Empire Network Server Starting (Static Data Mode)")
    logger.info("=" * 60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Configured channels: {list(CHANNEL_MAPPINGS.keys())}")
    
    # CHANGED: Always load static data, no background API calls
    logger.info("Loading static channel data from channel_data.json...")
    static_data = load_static_data()
    if static_data:
        with channel_cache['lock']:
            channel_cache['data'] = static_data
            # Set last_updated to file modification time or current time
            try:
                json_path = os.path.join(os.path.dirname(__file__), 'channel_data.json')
                file_mtime = os.path.getmtime(json_path)
                channel_cache['last_updated'] = datetime.datetime.fromtimestamp(file_mtime)
            except:
                channel_cache['last_updated'] = datetime.datetime.now()
        
        logger.info("✓ Static data loaded successfully")
        logger.info(f"Network stats: {static_data['totals']['views_formatted']} views, "
                   f"{static_data['totals']['years_active']} years active")
    else:
        logger.warning("⚠ No static data found - using empty defaults")
    
    # Start scheduler (disabled auto-refresh)
    scheduler_thread = threading.Thread(target=schedule_updates)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Start Flask
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.getenv('GAE_ENV') != 'standard'
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info("API refresh available at /api/refresh when quota allows")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)