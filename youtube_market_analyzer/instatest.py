import requests
import json
import time
from collections import Counter
from datetime import datetime
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv('APIFY_TOKEN')

def create_instagram_folder():
    """Create instagram folder if it doesn't exist"""
    folder_path = "instagram"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def analyze_trending_content():
    """Analyze trending content to find patterns and insights"""
    
    trending_hashtags = ["viral", "trending", "reels", "fyp", "explore"]
    all_posts = []
    hashtag_trends = {}
    
    for hashtag in trending_hashtags:
        print(f"\n🔍 Analyzing #{hashtag}...")
        
        # Start the scraper
        start_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs?token={APIFY_TOKEN}"
        
        payload = {
            "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag}/"],
            "resultsType": "posts",
            "resultsLimit": 15
        }
        
        try:
            # Start the run
            response = requests.post(start_url, json=payload, headers={"Content-Type": "application/json"})
            
            if response.status_code == 201:
                run_data = response.json()
                run_id = run_data["data"]["id"]
                print(f"   ⏳ Started run {run_id}, waiting for completion...")
                
                # Wait for completion (check status every 5 seconds)
                max_wait = 60  # Maximum 60 seconds
                wait_time = 0
                
                while wait_time < max_wait:
                    time.sleep(5)
                    wait_time += 5
                    
                    # Check run status
                    status_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs/{run_id}?token={APIFY_TOKEN}"
                    status_response = requests.get(status_url)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data["data"]["status"]
                        
                        if status == "SUCCEEDED":
                            print(f"   ✅ Run completed successfully")
                            
                            # Get the results
                            results_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs/{run_id}/dataset/items?token={APIFY_TOKEN}"
                            results_response = requests.get(results_url)
                            
                            if results_response.status_code == 200:
                                posts = results_response.json()
                                if posts:
                                    all_posts.extend(posts)
                                    hashtag_trends[hashtag] = posts
                                    print(f"   📊 Got {len(posts)} posts")
                                else:
                                    print(f"   ❌ No posts returned")
                            break
                            
                        elif status == "FAILED":
                            print(f"   ❌ Run failed")
                            break
                        else:
                            print(f"   ⏳ Status: {status}, waiting...")
                    
                else:
                    print(f"   ⏰ Timeout waiting for #{hashtag}")
                    
            else:
                print(f"   ❌ Error starting run: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(2)  # Brief pause between hashtags
    
    if not all_posts:
        print("\n❌ No posts collected from any hashtag. Check your API token and try again.")
        return [], {'total_posts': 0, 'top_hashtags': [], 'top_posts': [], 'content_types': {}, 'trending_words': []}
    
    # Analyze the collected posts
    analysis_results = analyze_posts(all_posts, hashtag_trends)
    
    return all_posts, analysis_results

def analyze_posts(all_posts, hashtag_trends):
    """Extract trending insights from the posts"""
    
    print("\n" + "="*60)
    print("📊 TRENDING ANALYSIS RESULTS")
    print("="*60)
    
    # 1. Most popular hashtags across all posts
    all_hashtags = []
    for post in all_posts:
        all_hashtags.extend(post.get('hashtags', []))
    
    hashtag_counter = Counter(all_hashtags)
    print("\n🔥 TOP TRENDING HASHTAGS:")
    for hashtag, count in hashtag_counter.most_common(10):
        print(f"   #{hashtag}: {count} posts")
    
    # 2. Engagement analysis
    print("\n💫 ENGAGEMENT LEADERS:")
    sorted_posts = sorted(all_posts, key=lambda x: x.get('likesCount', 0) + x.get('commentsCount', 0), reverse=True)
    
    for i, post in enumerate(sorted_posts[:5], 1):
        likes = post.get('likesCount', 0)
        comments = post.get('commentsCount', 0)
        total_engagement = likes + comments
        caption = post.get('caption', '')[:80]
        username = post.get('ownerUsername', 'unknown')
        
        print(f"   {i}. @{username}")
        print(f"      {likes:,} likes + {comments:,} comments = {total_engagement:,} total")
        print(f"      \"{caption}...\"")
        print(f"      instagram.com/p/{post.get('shortCode', '')}")
        print()
    
    # 3. Content type analysis
    content_types = Counter()
    for post in all_posts:
        post_type = post.get('type', 'Unknown')
        content_types[post_type] += 1
    
    if len(all_posts) > 0:
        print("📱 CONTENT TYPE TRENDS:")
        for content_type, count in content_types.items():
            percentage = (count / len(all_posts)) * 100
            print(f"   {content_type}: {count} posts ({percentage:.1f}%)")
    else:
        print("📱 CONTENT TYPE TRENDS: No posts to analyze")
    
    # 4. Language/Caption analysis
    print("\n🌍 TRENDING TOPICS IN CAPTIONS:")
    all_captions = " ".join([post.get('caption', '') for post in all_posts])
    # Extract common words (basic analysis)
    words = re.findall(r'\b\w+\b', all_captions.lower())
    # Filter out common words and short words
    filtered_words = [word for word in words if len(word) > 4 and word not in ['instagram', 'reels', 'follow', 'like']]
    word_counter = Counter(filtered_words)
    
    for word, count in word_counter.most_common(8):
        print(f"   '{word}': {count} mentions")
    
    # 5. Timing analysis
    print("\n⏰ POSTING TIME PATTERNS:")
    post_hours = []
    for post in all_posts:
        timestamp = post.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                post_hours.append(dt.hour)
            except:
                pass
    
    if post_hours:
        hour_counter = Counter(post_hours)
        print("   Most active hours (UTC):")
        for hour, count in hour_counter.most_common(5):
            print(f"     {hour:02d}:00 - {count} posts")
    
    # 6. Sponsored content analysis
    if len(all_posts) > 0:
        sponsored_count = sum(1 for post in all_posts if post.get('isSponsored', False))
        print(f"\n💰 SPONSORED CONTENT: {sponsored_count} out of {len(all_posts)} posts ({(sponsored_count/len(all_posts)*100):.1f}%)")
    else:
        print(f"\n💰 SPONSORED CONTENT: No posts to analyze")
    
    return {
        'total_posts': len(all_posts),
        'top_hashtags': hashtag_counter.most_common(10),
        'top_posts': sorted_posts[:5],
        'content_types': dict(content_types),
        'trending_words': word_counter.most_common(10)
    }

def save_results_to_files(all_posts, analysis_results):
    """Save results to multiple JSON files in instagram folder"""
    
    folder_path = create_instagram_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save raw posts data
    raw_data_file = os.path.join(folder_path, f"raw_data_{timestamp}.json")
    with open(raw_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
    print(f"💾 Raw data saved to: {raw_data_file}")
    
    # 2. Save trending analysis
    analysis_file = os.path.join(folder_path, f"trending_analysis_{timestamp}.json")
    
    # Convert Counter objects to regular dicts for JSON serialization
    analysis_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_posts_analyzed': analysis_results['total_posts'],
            'hashtags_analyzed': len(analysis_results['top_hashtags']),
            'content_types': analysis_results['content_types']
        },
        'top_hashtags': [{'hashtag': tag, 'count': count} for tag, count in analysis_results['top_hashtags']],
        'trending_words': [{'word': word, 'mentions': count} for word, count in analysis_results['trending_words']],
        'top_performing_posts': []
    }
    
    # Add top posts with clean data
    for post in analysis_results['top_posts']:
        clean_post = {
            'username': post.get('ownerUsername', ''),
            'full_name': post.get('ownerFullName', ''),
            'shortcode': post.get('shortCode', ''),
            'url': f"https://www.instagram.com/p/{post.get('shortCode', '')}",
            'likes': post.get('likesCount', 0),
            'comments': post.get('commentsCount', 0),
            'total_engagement': post.get('likesCount', 0) + post.get('commentsCount', 0),
            'caption': post.get('caption', '')[:200] + '...' if len(post.get('caption', '')) > 200 else post.get('caption', ''),
            'hashtags': post.get('hashtags', []),
            'timestamp': post.get('timestamp', ''),
            'type': post.get('type', ''),
            'is_sponsored': post.get('isSponsored', False)
        }
        analysis_data['top_performing_posts'].append(clean_post)
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    print(f"📊 Analysis saved to: {analysis_file}")
    
    # 3. Save hashtag breakdown by source hashtag
    hashtag_breakdown_file = os.path.join(folder_path, f"hashtag_breakdown_{timestamp}.json")
    hashtag_breakdown = {}
    
    for hashtag in ["viral", "trending", "reels", "fyp", "explore"]:
        hashtag_posts = [post for post in all_posts if f"tags/{hashtag}/" in post.get('inputUrl', '')]
        if hashtag_posts:
            hashtag_breakdown[hashtag] = {
                'post_count': len(hashtag_posts),
                'avg_likes': sum(post.get('likesCount', 0) for post in hashtag_posts) / len(hashtag_posts),
                'avg_comments': sum(post.get('commentsCount', 0) for post in hashtag_posts) / len(hashtag_posts),
                'top_posts': sorted(hashtag_posts, key=lambda x: x.get('likesCount', 0), reverse=True)[:3],
                'common_hashtags': dict(Counter([tag for post in hashtag_posts for tag in post.get('hashtags', [])]).most_common(10))
            }
    
    with open(hashtag_breakdown_file, 'w', encoding='utf-8') as f:
        json.dump(hashtag_breakdown, f, indent=2, ensure_ascii=False)
    print(f"🏷️  Hashtag breakdown saved to: {hashtag_breakdown_file}")
    
    # 4. Save user insights (top performers)
    user_insights_file = os.path.join(folder_path, f"user_insights_{timestamp}.json")
    user_insights = {}
    
    for post in analysis_results['top_posts'][:10]:  # Top 10 users
        username = post.get('ownerUsername', '')
        if username and username not in user_insights:
            user_posts = [p for p in all_posts if p.get('ownerUsername') == username]
            if user_posts:
                user_insights[username] = {
                    'full_name': post.get('ownerFullName', ''),
                    'user_id': post.get('ownerId', ''),
                    'post_count_in_trending': len(user_posts),
                    'avg_likes': sum(p.get('likesCount', 0) for p in user_posts) / len(user_posts),
                    'avg_comments': sum(p.get('commentsCount', 0) for p in user_posts) / len(user_posts),
                    'total_engagement': sum(p.get('likesCount', 0) + p.get('commentsCount', 0) for p in user_posts),
                    'most_used_hashtags': dict(Counter([tag for p in user_posts for tag in p.get('hashtags', [])]).most_common(5)),
                    'recent_posts': [
                        {
                            'shortcode': p.get('shortCode', ''),
                            'likes': p.get('likesCount', 0),
                            'comments': p.get('commentsCount', 0),
                            'caption': p.get('caption', '')[:100] + '...' if len(p.get('caption', '')) > 100 else p.get('caption', ''),
                            'timestamp': p.get('timestamp', '')
                        } for p in user_posts
                    ]
                }
    
    with open(user_insights_file, 'w', encoding='utf-8') as f:
        json.dump(user_insights, f, indent=2, ensure_ascii=False)
    print(f"👤 User insights saved to: {user_insights_file}")
    
    return {
        'raw_data': raw_data_file,
        'analysis': analysis_file,
        'hashtag_breakdown': hashtag_breakdown_file,
        'user_insights': user_insights_file
    }

def get_user_profile_insights(username):
    """Get insights about a specific trending user"""
    
    print(f"\n👤 Getting profile insights for @{username}...")
    
    url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "usernames": [username],
        "resultsType": "posts",
        "resultsLimit": 10
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        
        if response.status_code == 200:
            posts = response.json()
            
            if posts:
                print(f"   ✅ Found {len(posts)} recent posts")
                
                # Analyze their content strategy
                avg_likes = sum(post.get('likesCount', 0) for post in posts) / len(posts)
                avg_comments = sum(post.get('commentsCount', 0) for post in posts) / len(posts)
                
                print(f"   📊 Average engagement: {avg_likes:.0f} likes, {avg_comments:.0f} comments")
                
                # Their most used hashtags
                user_hashtags = []
                for post in posts:
                    user_hashtags.extend(post.get('hashtags', []))
                
                if user_hashtags:
                    hashtag_counter = Counter(user_hashtags)
                    print("   🏷️ Their top hashtags:")
                    for hashtag, count in hashtag_counter.most_common(5):
                        print(f"      #{hashtag} ({count} times)")
                
                return posts
            else:
                print("   ❌ No posts found")
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return []

if __name__ == "__main__":
    if not APIFY_TOKEN:
        print("⚠️  APIFY_TOKEN not found in .env file")
        print("   Make sure your .env file contains: APIFY_TOKEN=your_token_here")
    else:
        print("🚀 Starting Instagram Trending Analysis...")
        
        # Main trending analysis
        all_posts, analysis_results = analyze_trending_content()
        
        # Save all results to JSON files in instagram folder
        saved_files = save_results_to_files(all_posts, analysis_results)
        
        # Optional: Analyze a specific trending user
        if analysis_results['top_posts']:
            top_user = analysis_results['top_posts'][0].get('ownerUsername')
            if top_user:
                get_user_profile_insights(top_user)
        
        print(f"\n✅ Analysis complete! Processed {analysis_results['total_posts']} posts.")
        print(f"\n📁 All files saved in 'instagram/' folder:")
        for file_type, filename in saved_files.items():
            print(f"   {file_type}: {os.path.basename(filename)}")