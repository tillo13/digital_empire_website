# YouTube Network Dashboard on GCP

> **Live Example:** [digitalempiretv.com](https://digitalempiretv.com) - A production dashboard for a YouTube gaming network

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![GCP](https://img.shields.io/badge/GCP-App%20Engine-orange.svg)](https://cloud.google.com/appengine)

## What is this?

This repo shows the **core Flask application** that powers a YouTube network dashboard. A friend runs a gaming network with 7 channels and asked me to build a public-facing site to showcase their stats.

**⚠️ Note:** This repo contains only the public-facing Flask app code to demonstrate the pattern. The production site has additional operational components (deployment automation, testing scripts, monitoring tools) that aren't included here. I'm sharing the Flask/Python/GCP implementation, not the operational tooling.

**The Challenge:** YouTube's API has strict rate limits and quota costs. Fetching stats for 7 channels on every page load would hit limits fast and cost money. The solution needed to cache data intelligently while keeping stats reasonably fresh.

**Tech Stack:**
- **Backend:** Python 3.12, Flask
- **APIs:** YouTube Data API v3
- **Hosting:** Google Cloud Platform (App Engine Standard)
- **Caching:** JSON-based data caching with TTL
- **Frontend:** Responsive HTML/CSS

## Key Features

### Smart Data Caching
- Fetches YouTube stats once per hour max
- Stores in `channel_data.json` with timestamps
- Validates cache freshness before API calls
- Reduces API quota usage by ~95%

### Real-Time YouTube Integration
- Pulls subscriber counts, view counts, video stats
- Calculates monthly reach and engagement metrics
- Identifies viral videos (10K+ views)
- Aggregates network-wide statistics

### Auto-Scaling Infrastructure
- Google App Engine Standard (Python 3.12 runtime)
- Scales to zero when idle ($0 cost)
- Auto-scales on traffic spikes
- Custom domain support (digitalempiretv.com)

## Project Structure

```
digital_empire_tv/
├── main.py                    # Flask app and routing
├── app.yaml                   # GCP App Engine config
├── requirements.txt           # Python dependencies
├── utilities/
│   ├── youtube_utils.py       # YouTube API integration
│   └── gmail_utils.py         # Email notification helpers
├── templates/
│   ├── base.html             # Base template with nav
│   ├── index.html            # Homepage with channel grid
│   ├── about.html            # About/history page
│   └── contact.html          # Contact form
├── static/
│   ├── css/                  # Stylesheets
│   └── js/                   # Client-side scripts
├── channel_data.json         # Cached API responses
└── gcloud_deploy.py          # Deployment automation
```

## How It Works

### 1. YouTube API Integration

The `youtube_utils.py` module handles all YouTube Data API interactions:

```python
# Fetch channel statistics with smart caching
def get_channel_stats(channel_ids):
    # Check cache freshness
    if cache_valid() and cache_exists():
        return load_from_cache()

    # Fetch from YouTube API
    stats = youtube_api.channels().list(
        part="statistics,snippet",
        id=",".join(channel_ids)
    ).execute()

    # Cache for 1 hour
    save_to_cache(stats)
    return stats
```

### 2. Data Caching Strategy

**Problem:** YouTube API quota is limited (10,000 units/day)
**Solution:** Cache responses locally with TTL

- Each API call costs ~3 units
- 7 channels = 21 units per fetch
- Without caching: 476 requests/day = out of quota
- With caching: 24 requests/day (hourly refresh) = 504 units

### 3. Flask Application

Routes handle both human visitors and API consumers:

```python
@app.route('/')
def index():
    channels = get_all_channel_data()
    return render_template('index.html', channels=channels)

@app.route('/api/channels')
def api_channels():
    return jsonify(get_all_channel_data())

@app.route('/api/refresh')
def force_refresh():
    invalidate_cache()
    return redirect('/')
```

### 4. Google App Engine Deployment

The `app.yaml` configures the serverless environment:

```yaml
runtime: python312
instance_class: F1
automatic_scaling:
  min_instances: 0      # Scale to zero when idle
  max_instances: 5      # Limit to control costs
```

## Setup & Deployment

### Prerequisites

- Python 3.12+
- Google Cloud SDK ([install guide](https://cloud.google.com/sdk/docs/install))
- YouTube Data API key ([get one here](https://console.cloud.google.com/apis/credentials))

### Local Development

```bash
# Clone and setup
git clone https://github.com/tillo13/digital_empire_website.git
cd digital_empire_website

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
# Store in GCP Secret Manager or use env var for local dev
export YT_API_KEY="your_youtube_api_key_here"

# Run locally
python main.py
# Visit http://localhost:8080
```

### Deploy to GCP

```bash
# Initialize GCP project (first time only)
gcloud init
gcloud app create --region=us-central1

# Deploy
gcloud app deploy

# View live
gcloud app browse
```

## Design Decisions

### Why App Engine?

- **No server management** - Focus on code, not infrastructure
- **Auto-scaling** - Handles traffic spikes automatically
- **Cost-effective** - Scales to zero when idle
- **Simple deployment** - Single command to update production

### Why JSON Caching?

- **Fast reads** - No database queries needed
- **Simple** - Single file, easy to debug
- **Portable** - Works locally and in production
- **Good enough** - 7 channels = tiny dataset, no DB overhead needed

### Why Flask?

- **Lightweight** - Perfect for simple dashboards
- **Python** - Easy YouTube API integration
- **Flexible** - Can add features incrementally

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage with channel grid |
| `/about` | GET | About page |
| `/contact` | GET/POST | Contact form |
| `/api/channels` | GET | JSON data for all channels |
| `/api/refresh` | GET | Force cache refresh |
| `/health` | GET | Health check |

## Lessons Learned

1. **API quota management is critical** - Always cache external API calls
2. **App Engine is great for side projects** - $0 when idle, scales on demand
3. **JSON caching works for small datasets** - Don't over-engineer with Redis/DB
4. **YouTube API is straightforward** - Well-documented, easy to integrate
5. **Custom domains are easy on App Engine** - Point DNS, done

## Live Example

Check out the live site at **[digitalempiretv.com](https://digitalempiretv.com)** to see it in action.

The dashboard displays:
- 7 YouTube channels with 278M+ total views
- Real-time subscriber counts
- Monthly reach statistics
- Viral video identification
- Network performance metrics

## Future Enhancements

- [ ] Add chart visualizations (views over time)
- [ ] Implement Redis caching for higher scale
- [ ] Add email alerts for milestone achievements (e.g., 1M subs)
- [ ] Build admin panel for managing channel list
- [ ] Add video search functionality

## Code Quality

- Type hints throughout for better IDE support
- Modular design (utilities, templates, static assets)
- Error handling for API failures
- Logging for debugging in production
- Configurable via environment variables

## Contributing

Feel free to fork this and adapt it for your own YouTube channel or network. The patterns here work well for any multi-channel YouTube dashboard.

---

Built to help a friend showcase their YouTube network. Open-sourced so others can learn from it.
