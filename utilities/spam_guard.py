"""Shared contact form spam guard, used across all kumori-hosted sites.

Layers:
1. Honeypot check (already on most sites, but centralized here)
2. Timing check with server-side verification
3. Content pattern blocklist (catches SEO pitches, marketing spam)
4. Email domain blocklist (disposable/known-spam domains)
5. IP rate limiting (in-memory, resets on deploy)
"""

import logging
import re
import time
from collections import defaultdict

logger = logging.getLogger('spam_guard')

# ── Content patterns that indicate spam ──────────────────────────────────
# Each is (compiled_regex, description), case-insensitive match against
# concatenated form fields (name + company + subject + message).
SPAM_PATTERNS = [
    (re.compile(r'(SEO|search engine).{0,30}(rank|result|optimiz|appear|visib|first page)', re.I),
     'SEO pitch'),
    (re.compile(r'(digital marketing|web design|web development).{0,20}(agency|firm|company|service)', re.I),
     'marketing agency pitch'),
    (re.compile(r'review(ed)?\s+(of\s+)?your\s+(web)?site', re.I),
     'site review pitch'),
    (re.compile(r'(boost|improve|increase).{0,20}(traffic|ranking|visib|lead|conversion)', re.I),
     'traffic/ranking pitch'),
    (re.compile(r'(backlink|link.?building|guest.?post|article.?placement)', re.I),
     'backlink/guest-post spam'),
    (re.compile(r'(white.?label|outsourc).{0,20}(develop|design|market|SEO)', re.I),
     'outsourcing pitch'),
    (re.compile(r'(struggl|fail|poor|lacking).{0,30}(search|google|rank|traffic|online presence)', re.I),
     'negative SEO pitch'),
    (re.compile(r'(free|complimentary).{0,20}(audit|analysis|review|consultation|quote)', re.I),
     'free audit offer'),
    (re.compile(r'(get|drive|attract)\s+more\s+(client|customer|visitor|lead|traffic)', re.I),
     'lead generation pitch'),
    (re.compile(r'(first page|page one|top\s+(of\s+)?google)', re.I),
     'Google ranking promise'),
]

# ── Disposable / known-spam email domains ────────────────────────────────
BLOCKED_DOMAINS = {
    # Disposable email services
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.de', 'tempmail.com',
    'throwaway.email', 'temp-mail.org', 'fakeinbox.com', 'sharklasers.com',
    'guerrillamailblock.com', 'grr.la', 'dispostable.com', 'yopmail.com',
    'trashmail.com', 'trashmail.me', 'mailnesia.com', 'maildrop.cc',
    'discard.email', 'tempail.com', 'emailondeck.com', 'getnada.com',
    'mohmal.com', '10minutemail.com', 'minutemail.com', 'tempr.email',
    'binkmail.com', 'safetymail.info', 'filzmail.com',
}

# ── Rate limiting ────────────────────────────────────────────────────────
# {ip: [timestamp, timestamp, ...]}
_submissions: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 3          # max submissions
RATE_WINDOW = 3600      # per this many seconds (1 hour)


def _clean_old(ip: str):
    """Remove timestamps older than the rate window."""
    cutoff = time.time() - RATE_WINDOW
    _submissions[ip] = [t for t in _submissions[ip] if t > cutoff]


def check_spam(data: dict, ip: str, fields: list[str] | None = None) -> str | None:
    """Run all spam checks against a contact form submission.

    Args:
        data: form data dict (expects keys like name, email, message, etc.)
        ip: requester IP address
        fields: which keys to concatenate for content scanning
                (default: name, company, subject, message)

    Returns:
        None if clean, or a short reason string if spam.
        The reason is for logging only; never expose to the submitter.
    """
    # 1. Honeypot: check both common field names
    for hp_field in ('website', 'honeypot', 'url', 'fax'):
        if data.get(hp_field, '').strip():
            return f'honeypot:{hp_field}'

    # 2. Timing: client sends time_open in ms; reject if under 3s
    time_open = data.get('time_open', 0)
    try:
        time_open = int(time_open)
    except (TypeError, ValueError):
        time_open = 0
    if time_open < 3000:
        return f'too_fast:{time_open}ms'

    # 3. Rate limit by IP
    _clean_old(ip)
    if len(_submissions[ip]) >= RATE_LIMIT:
        return f'rate_limit:{ip}'
    # Don't record yet; record after we confirm it's not spam

    # 4. Email domain check
    email = data.get('email', '')
    if '@' in email:
        domain = email.rsplit('@', 1)[1].strip().lower()
        if domain in BLOCKED_DOMAINS:
            return f'blocked_domain:{domain}'

    # 5. Content pattern scan
    if fields is None:
        fields = ['name', 'company', 'subject', 'message']
    blob = ' '.join(str(data.get(f, '')) for f in fields)
    for pattern, desc in SPAM_PATTERNS:
        if pattern.search(blob):
            return f'content:{desc}'

    # All clear: record this submission for rate limiting
    _submissions[ip].append(time.time())
    return None
