import praw, requests, os, time
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class TrendTracker:
    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YT_API_KEY'))
        self.reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'), client_secret=os.getenv('REDDIT_CLIENT_SECRET'), user_agent="trends/1.0")
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self.subs = ["SonicTheHedgehog", "roblox", "gaming", "memes", "funny", "teenagers", "GenZ", "dankmemes", "nextfuckinglevel", "interestingasfuck", "Unexpected", "BeAmazed", "mildlyinfuriating", "WhatCouldGoWrong", "oddlysatisfying", "facepalm"]

    def get_viral_reddit(self):
        all_posts = []
        for sub_name in self.subs[:10]:  # Limit to avoid rate limits
            try:
                for post in self.reddit.subreddit(sub_name).hot(limit=8):
                    age = datetime.now() - datetime.fromtimestamp(post.created_utc)
                    if age.days <= 2:
                        title_lower = post.title.lower()
                        boring = any(x in title_lower for x in ['politics', 'trump', 'biden', 'sports', 'nfl', 'nba', 'news', 'lawsuit'])
                        teen_appeal = any(x in title_lower for x in ['gaming', 'sonic', 'roblox', 'minecraft', 'meme', 'funny', 'wtf', 'amazing', 'cringe', 'tiktok'])
                        
                        if not boring and (post.score > 1000 or teen_appeal or post.is_video):
                            viral_score = post.score * (1 + post.num_comments/max(post.score,1)) / max(age.total_seconds()/3600, 1)
                            all_posts.append({
                                'title': post.title, 'score': post.score, 'comments': post.num_comments,
                                'url': f"https://reddit.com{post.permalink}", 'direct_url': post.url if post.url != f"https://reddit.com{post.permalink}" else None,
                                'age_h': round(age.total_seconds()/3600, 1), 'sub': sub_name, 'viral': round(viral_score, 1),
                                'video': post.is_video, 'author': str(post.author) if post.author else '[deleted]'
                            })
                time.sleep(0.5)
            except: continue
        return sorted(all_posts, key=lambda x: x['viral'], reverse=True)

    def get_youtube_trends(self):
        try:
            videos = []
            for term in ["sonic", "roblox", "minecraft"][:2]:  # Limit API calls
                request = self.youtube.search().list(part="snippet", q=term, type="video", order="relevance", 
                                                   publishedAfter=(datetime.now() - timedelta(days=7)).isoformat() + 'Z', maxResults=3)
                for item in request.execute().get('items', []):
                    stats = self.youtube.videos().list(part="statistics", id=item['id']['videoId']).execute()['items'][0]['statistics']
                    videos.append({'title': item['snippet']['title'], 'channel': item['snippet']['channelTitle'],
                                 'views': int(stats.get('viewCount', 0)), 'url': f"https://youtube.com/watch?v={item['id']['videoId']}"})
                time.sleep(0.5)
            return sorted(videos, key=lambda x: x['views'], reverse=True)
        except: return []

    def analyze_post(self, post):
        title = post['title'].lower()
        reasons = []
        if any(x in title for x in ['wtf', 'amazing', 'insane', 'crazy']): reasons.append('Shocking')
        if any(x in title for x in ['fails', 'wrong', 'disaster']): reasons.append('Fail')
        if any(x in title for x in ['funny', 'meme', 'lol']): reasons.append('Funny')
        if any(x in title for x in ['gaming', 'sonic', 'roblox']): reasons.append('Gaming')
        if post['video']: reasons.append('Video')
        if post['age_h'] < 6: reasons.append('Fresh')
        
        if post['video'] and any(x in title for x in ['rescue', 'helps']): reaction = "REACT: Wholesome content"
        elif post['video'] and any(x in title for x in ['fails', 'wrong']): reaction = "REACT: Fail commentary"
        elif 'meme' in post['sub'] or 'funny' in post['sub']: reaction = "REACT: Meme review"
        else: reaction = "REACT: General commentary"
        
        return reasons, reaction

    def run(self):
        print("🔥 TEEN VIRAL CONTENT TRACKER")
        print("="*50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # YouTube trends
        yt = self.get_youtube_trends()
        if yt:
            print("🎥 TRENDING YOUTUBE\n" + "-"*30)
            for i, v in enumerate(yt[:5], 1):
                print(f"{i}. {v['title'][:60]}...")
                print(f"   📺 {v['channel']} | 👀 {v['views']:,} views")
                print(f"   🔗 {v['url']}\n")
        
        # Reddit viral content
        posts = self.get_viral_reddit()
        print("🔥 VIRAL REDDIT POSTS\n" + "-"*30)
        
        for i, p in enumerate(posts[:15], 1):
            reasons, reaction = self.analyze_post(p)
            fresh = "🔥" if p['age_h'] < 6 else "⏰" if p['age_h'] < 24 else "📅"
            vid = "📹" if p['video'] else ""
            
            print(f"{i:2d}. r/{p['sub']} {vid} {fresh}")
            print(f"    📝 {p['title']}")
            print(f"    📊 {p['score']:,} ⬆ | 💬 {p['comments']} | 🔥 {p['viral']} viral | ⏰ {p['age_h']}h")
            if reasons: print(f"    🎯 {', '.join(reasons)}")
            print(f"    💡 {reaction}")
            print(f"    🔗 {p['url']}")
            if p['direct_url']: print(f"    🌐 {p['direct_url']}")
            print()
        
        # Gaming specific
        gaming = [p for p in posts if any(x in p['title'].lower() for x in ['sonic', 'roblox', 'minecraft', 'gaming'])][:8]
        if gaming:
            print("🎮 GAMING VIRAL\n" + "-"*20)
            for i, p in enumerate(gaming, 1):
                print(f"{i}. r/{p['sub']} - {p['title'][:50]}...")
                print(f"   📊 {p['score']:,} ⬆ | 🔗 {p['url']}\n")

if __name__ == "__main__": TrendTracker().run()