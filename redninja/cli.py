"""
CLI for Red Ninja YouTube channel management.

Usage:
    python -m digital_empire_tv.redninja.cli info
    python -m digital_empire_tv.redninja.cli dashboard --days 28
    python -m digital_empire_tv.redninja.cli videos --top 20
    python -m digital_empire_tv.redninja.cli deleted
    python -m digital_empire_tv.redninja.cli check VIDEO_ID
    python -m digital_empire_tv.redninja.cli analytics --days 28
    python -m digital_empire_tv.redninja.cli video-analytics VIDEO_ID --days 90
    python -m digital_empire_tv.redninja.cli update VIDEO_ID --title "New Title"
"""

import argparse
import json
import sys
import os
import logging
from datetime import datetime, timedelta

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def _date_range(days: int):
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return start, end


def _print_json(data):
    print(json.dumps(data, indent=2, default=str))


def _print_table(rows, columns):
    """Simple table printer."""
    if not rows:
        print("  (no data)")
        return

    # Calculate column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, ''))
            widths[col] = max(widths[col], len(val))

    # Header
    header = '  '.join(col.ljust(widths[col]) for col in columns)
    print(header)
    print('-' * len(header))

    # Rows
    for row in rows:
        line = '  '.join(str(row.get(col, '')).ljust(widths[col]) for col in columns)
        print(line)


def cmd_info(rn, args):
    info = rn.channel_info()
    print(f"\n  Red Ninja (@{info['custom_url']})")
    print(f"  {'=' * 40}")
    print(f"  Subscribers:  {info['subscriber_count']:,}")
    print(f"  Total Views:  {info['view_count']:,}")
    print(f"  Videos:       {info['video_count']:,}")
    print(f"  Country:      {info['country']}")
    print(f"  Created:      {info['published_at'][:10]}")
    print()


def cmd_dashboard(rn, args):
    print(f"\n  Fetching dashboard ({args.days} days)...")
    dash = rn.studio_dashboard(days=args.days)

    ov = dash['overview']
    imp = dash['impressions']

    print(f"\n  Red Ninja Studio Dashboard ({dash['period']})")
    print(f"  {'=' * 50}")

    print(f"\n  OVERVIEW")
    print(f"  Views:             {ov.get('views', 0):,}")
    watch_hrs = round(ov.get('estimatedMinutesWatched', 0) / 60, 1)
    print(f"  Watch Time:        {watch_hrs:,} hours")
    avg_dur = ov.get('averageViewDuration', 0)
    print(f"  Avg View Duration: {int(avg_dur // 60)}:{int(avg_dur % 60):02d}")
    print(f"  Subs Gained:       +{ov.get('subscribersGained', 0):,}")
    print(f"  Subs Lost:         -{ov.get('subscribersLost', 0):,}")
    print(f"  Likes:             {ov.get('likes', 0):,}")
    print(f"  Comments:          {ov.get('comments', 0):,}")
    print(f"  Shares:            {ov.get('shares', 0):,}")

    print(f"\n  REACH")
    print(f"  Impressions:       {imp.get('impressions', 0):,}")
    ctr = imp.get('impressionClickThroughRate', 0)
    print(f"  Click-Through:     {ctr * 100 if isinstance(ctr, float) and ctr < 1 else ctr:.1f}%")

    print(f"\n  TOP VIDEOS")
    for i, v in enumerate(dash['top_videos'][:10], 1):
        title = v.get('title', v.get('video', ''))[:50]
        views = v.get('views', 0)
        print(f"  {i:2d}. {title:<50s}  {views:>10,} views")

    print(f"\n  TRAFFIC SOURCES")
    for src in dash['traffic_sources'][:8]:
        source = src.get('insightTrafficSourceType', '')
        views = src.get('views', 0)
        print(f"  {source:<30s}  {views:>10,} views")

    print(f"\n  TOP COUNTRIES")
    for geo in dash['geography'][:10]:
        country = geo.get('country', '')
        views = geo.get('views', 0)
        print(f"  {country:<10s}  {views:>10,} views")

    print(f"\n  DEMOGRAPHICS")
    for demo in dash['demographics']:
        age = demo.get('ageGroup', '')
        gender = demo.get('gender', '')
        pct = demo.get('viewerPercentage', 0)
        print(f"  {gender:<10s} {age:<15s}  {pct:.1f}%")

    print()


def cmd_videos(rn, args):
    print(f"\n  Fetching all videos...")
    videos = rn.videos.get_all_videos_summary()
    print(f"  Found {len(videos)} videos total\n")

    if args.sort == 'date':
        videos.sort(key=lambda x: x['published_at'], reverse=True)
    elif args.sort == 'likes':
        videos.sort(key=lambda x: x['likes'], reverse=True)

    for i, v in enumerate(videos[:args.top], 1):
        print(f"  {i:3d}. {v['title'][:60]:<60s}")
        print(f"       {v['views_formatted']:>8s} views  {v['likes_formatted']:>6s} likes  "
              f"{v['comments_formatted']:>6s} comments  {v['engagement_rate']:.1f}% eng  "
              f"{v['duration']:>8s}  {v['published_at'][:10]}")
        print(f"       {v['url']}")
    print()


def cmd_deleted(rn, args):
    print(f"\n  Scanning for deleted videos...")
    result = rn.videos.find_deleted_videos()

    print(f"\n  Playlist videos: {result['playlist_count']}")
    print(f"  Existing videos: {result['existing_count']}")
    print(f"  Cached videos:   {result['cache_count']}")
    print(f"  Deleted found:   {result['total_deleted']}")

    if result['deleted']:
        print(f"\n  DELETED VIDEOS:")
        for v in result['deleted']:
            print(f"  - {v['title']}")
            print(f"    ID: {v['video_id']}  ({v['detected_via']})")
            print(f"    {v['url']}")
    else:
        print(f"\n  No deleted videos detected.")
    print()


def cmd_check(rn, args):
    status = rn.check_video(args.video_id)
    print(f"\n  Video: {args.video_id}")
    if status['exists']:
        print(f"  Status:  EXISTS")
        print(f"  Title:   {status['title']}")
        print(f"  Privacy: {status['privacy']}")
        print(f"  Views:   {status['views']:,}")
    else:
        print(f"  Status:  DELETED or PRIVATE")
    print()


def cmd_analytics(rn, args):
    start, end = _date_range(args.days)
    print(f"\n  Analytics: {start} to {end}")

    overview = rn.analytics.get_overview(start, end)
    print(f"\n  OVERVIEW")
    for k, v in overview.items():
        print(f"  {k:<35s}  {v}")

    print(f"\n  DAILY VIEWS")
    daily = rn.analytics.get_daily_views(start, end)
    for day in daily[-14:]:  # Last 14 days
        d = day.get('day', '')
        views = day.get('views', 0)
        bar = '#' * max(1, int(views / max(max(r.get('views', 1) for r in daily), 1) * 40))
        print(f"  {d}  {views:>8,}  {bar}")
    print()


def cmd_video_analytics(rn, args):
    start, end = _date_range(args.days)
    print(f"\n  Video Analytics: {args.video_id} ({start} to {end})")

    va = rn.analytics.get_video_analytics(args.video_id, start, end)
    title = va.pop('title', args.video_id)
    vid = va.pop('video_id', '')
    print(f"  Title: {title}\n")

    for k, v in va.items():
        print(f"  {k:<35s}  {v}")

    if args.daily:
        print(f"\n  DAILY BREAKDOWN")
        daily = rn.analytics.get_video_daily(args.video_id, start, end)
        for day in daily:
            d = day.get('day', '')
            views = day.get('views', 0)
            print(f"  {d}  {views:>8,}")

    if args.traffic:
        print(f"\n  TRAFFIC SOURCES")
        sources = rn.analytics.get_video_traffic_sources(args.video_id, start, end)
        for src in sources:
            source = src.get('insightTrafficSourceType', '')
            views = src.get('views', 0)
            print(f"  {source:<30s}  {views:>10,}")

    print()


def cmd_update(rn, args):
    changes = {}
    if args.title:
        changes['title'] = args.title
    if args.description:
        changes['description'] = args.description
    if args.tags:
        changes['tags'] = args.tags

    if not changes:
        print("No changes specified. Use --title, --description, or --tags.")
        return

    print(f"\n  Updating video {args.video_id}...")
    print(f"  Changes: {json.dumps(changes, indent=4)}")

    # Confirm before updating
    confirm = input("\n  Proceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return

    result = rn.videos.update_video(args.video_id, **changes)
    print(f"  Updated: {result['snippet']['title']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Red Ninja YouTube Channel Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')

    sub = parser.add_subparsers(dest='command')

    sub.add_parser('info', help='Channel info')

    dash_p = sub.add_parser('dashboard', help='Full Studio-like dashboard')
    dash_p.add_argument('--days', type=int, default=28)

    vid_p = sub.add_parser('videos', help='List videos')
    vid_p.add_argument('--top', type=int, default=20)
    vid_p.add_argument('--sort', choices=['views', 'date', 'likes'], default='views')

    sub.add_parser('deleted', help='Find deleted/removed videos')

    check_p = sub.add_parser('check', help='Check if a video exists')
    check_p.add_argument('video_id', help='Video ID to check')

    ana_p = sub.add_parser('analytics', help='Channel analytics overview')
    ana_p.add_argument('--days', type=int, default=28)

    va_p = sub.add_parser('video-analytics', help='Analytics for a specific video')
    va_p.add_argument('video_id', help='Video ID')
    va_p.add_argument('--days', type=int, default=28)
    va_p.add_argument('--daily', action='store_true', help='Include daily breakdown')
    va_p.add_argument('--traffic', action='store_true', help='Include traffic sources')

    up_p = sub.add_parser('update', help='Update video metadata')
    up_p.add_argument('video_id', help='Video ID')
    up_p.add_argument('--title', help='New title')
    up_p.add_argument('--description', help='New description')
    up_p.add_argument('--tags', nargs='+', help='New tags')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

    from .client import RedNinjaYT
    rn = RedNinjaYT()

    commands = {
        'info': cmd_info,
        'dashboard': cmd_dashboard,
        'videos': cmd_videos,
        'deleted': cmd_deleted,
        'check': cmd_check,
        'analytics': cmd_analytics,
        'video-analytics': cmd_video_analytics,
        'update': cmd_update,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(rn, args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
