import json
import os
import re
import requests
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import parse_qs, quote, urlparse

from .detector import TRUSTED_DOMAINS

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z']+")
SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "will", "with", "you", "your", "lo", "undi",
}
SEARCH_KEYWORDS_LIMIT = 14
HEADERS = {
    "User-Agent": "FakeNewsDetector/1.0 (+https://localhost)",
}
MAX_PAGE_BYTES = 500_000


def _trusted_domain(domain):
    domain = domain.lower().removeprefix("www.")
    return domain in TRUSTED_DOMAINS or any(domain.endswith('.' + t) for t in TRUSTED_DOMAINS)


def _tokens(text):
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if token.lower() not in SEARCH_STOP_WORDS
    }


def _overlap_score(query, text):
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0
    text_tokens = _tokens(text)
    return len(query_tokens & text_tokens) / len(query_tokens)


def _compact_query(query):
    tokens = []
    for token in TOKEN_RE.findall(query or ""):
        lowered = token.lower()
        if lowered in SEARCH_STOP_WORDS or len(lowered) < 3:
            continue
        if lowered not in tokens:
            tokens.append(lowered)
        if len(tokens) >= SEARCH_KEYWORDS_LIMIT:
            break
    return " ".join(tokens) or query


def _strip_html(value):
    return re.sub(r"<[^>]+>", "", unescape(value or "")).strip()


def _meta_content(html, *names):
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return _strip_html(match.group(1))
    return ""


def _title_from_html(html):
    title = _meta_content(html, "og:title", "twitter:title")
    if title:
        return title
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return _strip_html(match.group(1)) if match else ""


def _description_from_html(html):
    return _meta_content(html, "og:description", "twitter:description", "description")


def _clean_social_text(text, domain):
    cleaned = _strip_html(text)
    if "instagram.com" in domain:
        quoted = re.search(r':\s*["“](.+?)["”]\s*$', cleaned, re.DOTALL)
        if quoted:
            cleaned = quoted.group(1)
        cleaned = re.sub(r"\[[^\]]+\]", " ", cleaned)
    if "youtube.com" in domain or domain == "youtu.be":
        cleaned = cleaned.replace(" - YouTube", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _youtube_oembed(url):
    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            headers=HEADERS,
            timeout=6,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None
    title = data.get("title") or ""
    author = data.get("author_name") or "YouTube"
    if not title:
        return None
    return {
        "text": f"{_clean_social_text(title, 'youtube.com')} {author}",
        "title": title,
        "description": "",
        "source": author,
        "items": [{"title": title, "url": url, "source": author, "trusted": False, "snippet": "YouTube metadata"}],
    }


def _youtube_watch_url(url):
    parsed = urlparse(url if "://" in url else "https://" + url)
    domain = parsed.netloc.lower().removeprefix("www.")
    if domain in {"youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else url
    if domain.endswith("youtube.com"):
        if "/shorts/" in parsed.path:
            video_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            return f"https://www.youtube.com/watch?v={video_id}" if video_id else url
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else url
    return url


def extract_claim_from_url(source_url):
    """Extract searchable text from article/social/video URLs without requiring API keys."""
    if not source_url:
        return {"text": "", "items": [], "source": "", "title": "", "description": ""}

    normalized_url = source_url if "://" in source_url else "https://" + source_url
    parsed = urlparse(normalized_url)
    domain = parsed.netloc.lower().removeprefix("www.")

    if "youtube.com" in domain or domain == "youtu.be":
        youtube_url = _youtube_watch_url(normalized_url)
        youtube_result = _youtube_oembed(youtube_url)
        if youtube_result:
            return youtube_result

    try:
        response = requests.get(normalized_url, headers=HEADERS, timeout=8, allow_redirects=True, stream=True)
        response.raise_for_status()
        content = response.raw.read(MAX_PAGE_BYTES, decode_content=True)
        page = content.decode(response.encoding or "utf-8", errors="ignore")
    except Exception:
        fallback_text = " ".join(part for part in [domain, parsed.path.replace("/", " ")] if part).strip()
        return {
            "text": fallback_text,
            "items": [],
            "source": domain,
            "title": fallback_text,
            "description": "",
        }

    title = _title_from_html(page)
    description = _description_from_html(page)
    title = _clean_social_text(title, domain)
    description = _clean_social_text(description, domain)

    ld_titles = []
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.IGNORECASE | re.DOTALL):
        try:
            payload = json.loads(unescape(match.group(1)).strip())
        except Exception:
            continue
        payloads = payload if isinstance(payload, list) else [payload]
        for item in payloads:
            if not isinstance(item, dict):
                continue
            ld_titles.extend(str(item.get(key, "")) for key in ("headline", "name", "description") if item.get(key))

    text = " ".join(part for part in [title, description, *ld_titles] if part)
    if not text:
        text = " ".join(part for part in [domain, parsed.path.replace("/", " ")] if part).strip()

    return {
        "text": text[:1200],
        "title": title,
        "description": description,
        "source": domain,
        "items": [{
            "title": title or normalized_url,
            "url": normalized_url,
            "source": domain,
            "trusted": _trusted_domain(domain),
            "snippet": description,
        }],
    }


def check_wikipedia(query, pagesize=3):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": pagesize,
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=6)
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
    except Exception:
        return {"score": 0, "items": []}

    items = []
    best_overlap = 0
    for result in results:
        title = result.get("title") or ""
        snippet = _strip_html(result.get("snippet") or "")
        combined = f"{title} {snippet}"
        overlap = _overlap_score(query, combined)
        best_overlap = max(best_overlap, overlap)
        if overlap >= 0.45:
            items.append({
                "title": title,
                "url": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")),
                "source": "Wikipedia",
                "trusted": True,
                "snippet": snippet,
            })

    if not items:
        return {"score": 0, "items": []}
    score = int(min(92, 55 + best_overlap * 40))
    return {"score": score, "items": items[:pagesize]}


def check_duckduckgo(query, pagesize=5):
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=8,
        )
        response.raise_for_status()
    except Exception:
        return {"score": 0, "items": []}

    html = response.text
    pattern = re.compile(
        r'<a rel="nofollow" class="result__a" href="(?P<url>[^"]+)".*?>(?P<title>.*?)</a>.*?'
        r'<a class="result__snippet".*?>(?P<snippet>.*?)</a>',
        re.DOTALL,
    )
    items = []
    trusted_count = 0
    best_overlap = 0
    for match in pattern.finditer(html):
        title = _strip_html(match.group("title"))
        snippet = _strip_html(match.group("snippet"))
        link = unescape(match.group("url"))
        domain = urlparse(link).netloc.lower().removeprefix("www.")
        trusted = _trusted_domain(domain) or domain.endswith((".gov", ".gov.in", ".edu", ".ac.in"))
        overlap = _overlap_score(query, f"{title} {snippet}")
        best_overlap = max(best_overlap, overlap)
        if overlap < 0.35:
            continue
        if trusted:
            trusted_count += 1
        items.append({
            "title": title,
            "url": link,
            "source": domain or "DuckDuckGo",
            "trusted": trusted,
            "snippet": snippet,
        })
        if len(items) >= pagesize:
            break

    if not items:
        return {"score": 0, "items": []}

    trusted_bonus = (trusted_count / len(items)) * 25
    score = int(min(95, 45 + best_overlap * 35 + trusted_bonus))
    return {"score": score, "items": items}


def check_google_news(query, pagesize=5):
    url = "https://news.google.com/rss/search"
    params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=8)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return {"score": 0, "items": []}

    items = []
    trusted_count = 0
    best_overlap = 0
    for item in root.findall(".//item"):
        title = _strip_html(item.findtext("title") or "")
        link = item.findtext("link") or ""
        source = item.findtext("source") or "Google News"
        domain = urlparse(link).netloc.lower().removeprefix("www.")
        source_key = source.lower().removeprefix("www.")
        trusted = (
            _trusted_domain(domain)
            or _trusted_domain(source_key)
            or any(name in source_key for name in (
                "india today", "moneycontrol", "indian express", "economic times",
                "ndtv", "hindustan times", "deccan herald",
            ))
        )
        overlap = _overlap_score(query, title)
        best_overlap = max(best_overlap, overlap)
        if overlap < 0.35:
            continue
        if trusted:
            trusted_count += 1
        items.append({
            "title": title,
            "url": link,
            "source": source,
            "trusted": trusted,
            "snippet": title,
        })
        if len(items) >= pagesize:
            break

    if not items:
        return {"score": 0, "items": []}

    trusted_bonus = (trusted_count / len(items)) * 30
    score = int(min(95, 55 + best_overlap * 35 + trusted_bonus))
    return {"score": score, "items": items}


def check_newsapi(query, pagesize=5):
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return {"score": 0, "items": []}
    url = "https://newsapi.org/v2/everything"
    params = {"q": query, "pageSize": pagesize, "language": "en", "sortBy": "relevancy", "apiKey": key}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=6)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles") or []
        items = []
        trusted = 0
        for a in articles:
            src = a.get("source", {}) or {}
            name = src.get("name") or ""
            link = a.get("url") or ""
            parsed = urlparse(link)
            domain = parsed.netloc.lower().removeprefix("www.") if link else ""
            is_trusted = _trusted_domain(domain)
            if is_trusted:
                trusted += 1
            items.append({"title": a.get("title"), "url": link, "source": name, "trusted": is_trusted})
        if not items:
            return {"score": 0, "items": []}
        # score combines number of results and share from trusted domains
        score = int(min(95, 20 + (trusted / len(items)) * 60 + min(len(items), pagesize) / pagesize * 15))
        return {"score": score, "items": items}
    except Exception:
        return {"score": 0, "items": []}


def check_evidence(query, source_url=None):
    """Check live sources for supporting evidence.

    Returns: {score: 0-100, items: [ {title,url,source,trusted} ] }
    """
    q = _compact_query(query)

    checks = [
        check_newsapi(q),
        check_wikipedia(query),
        check_google_news(q),
        check_duckduckgo(q),
    ]
    items = []
    score = 0
    seen_urls = set()
    for result in checks:
        score = max(score, result.get("score", 0))
        for item in result.get("items", []):
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            items.append(item)

    if not items:
        return {"score": 0, "items": []}
    trusted_count = sum(1 for item in items if item.get("trusted"))
    if trusted_count >= 2:
        score = max(score, 88)
    elif trusted_count >= 1 and len(items) >= 3:
        score = max(score, 86)
    items.sort(key=lambda item: (not item.get("trusted"), item.get("source", ""), item.get("title", "")))
    return {"score": min(score, 95), "items": items[:8]}
