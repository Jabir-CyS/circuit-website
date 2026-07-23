#!/usr/bin/env python3
"""
agent.py — Circuit's auto-curator agent
-----------------------------------------
What this does, every time it runs:
  1. Reads RSS feeds listed in config.json (TechCrunch, The Verge, etc.)
     RSS is the publication's own public syndication feed — this is not
     scraping, it's the same feed any reader's RSS app would pull.
  2. Looks at only the HEADLINE + short summary each feed provides.
  3. For each new item not seen before (tracked in state.json), asks
     Claude to write a fully original article inspired by the topic —
     with its own analysis, own wording, own structure — never copying
     or closely paraphrasing the source.
  4. Adds a visible attribution line crediting the original source.
  5. Appends the new post to posts_data.json.
  6. Runs build_posts_js.py so the live site picks up the new post.

Run manually:
    python3 agent.py

Run on a schedule (recommended): see the included GitHub Actions
workflow (.github/workflows/auto-post.yml) which runs this automatically
every 30 minutes for free on GitHub.

Requirements:
    pip install feedparser google-genai
    Environment variable GEMINI_API_KEY must be set (free at https://aistudio.google.com/app/apikey).
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import feedparser
except ImportError:
    print("Missing dependency. Run: pip install feedparser google-genai --break-system-packages")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Missing dependency. Run: pip install feedparser google-genai --break-system-packages")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
DATA_FILE = os.path.join(BASE_DIR, "posts_data.json")

CATEGORY_LABELS = {
    "ai": "AI",
    "startup": "Startups",
    "security": "Security",
    "apps": "Apps",
    "reviews": "Reviews",
}

WRITER_SYSTEM_PROMPT = """You are a senior tech journalist and SEO editor writing for "Circuit", an
independent tech news blog. You will be given a headline and short summary from another
publication's RSS feed — this is only a starting point for the TOPIC, not something to rewrite.

Rules you must follow:
- Do NOT reproduce, closely paraphrase, or mirror the structure of the original headline/summary.
- Write a genuinely original article: your own angle, your own analysis, your own examples.
- Add real value beyond the headline — context, implications, a "why this matters" angle.
- Keep it factually grounded in the general topic, but do not invent specific quotes, statistics,
  or claims attributed to named individuals that you cannot verify from the summary provided.
- Tone: clear, direct, professional tech journalism. No hype, no clickbait, no fake urgency.

Writing quality bar (this is what makes an article actually good, not just present):
- Open with a concrete hook in the first 1-2 sentences — a specific detail, tension, or question.
  Never open with a generic throat-clearing sentence like "In today's fast-paced world...".
- Structure the body with 2-4 natural subheadings (short, specific, not clickbaity) that break the
  article into scannable sections — use the "headings" field for this (see JSON shape below).
- Vary sentence length. Short sentences for emphasis. Longer ones for explanation.
- End with a clear takeaway or forward-looking line, not a limp summary restatement.
- Every paragraph should earn its place — cut anything that just pads length.

SEO requirements (fill these honestly based on the actual article you write):
- metaDescription: 140-155 characters, written for a search results snippet, includes the core
  keyword naturally, entices a click without being clickbait.
- keywords: 4-7 specific lowercase keyword phrases a reader might actually search for.
- imageQuery: 2-4 words describing a real, literal, photographable scene that visually represents
  this article's topic (e.g. "smartphone camera lens", "server room data center", "coding laptop
  screen") — used to fetch a relevant stock photo. Keep it concrete and visual, not abstract.
- imageAlt: a descriptive, specific alt-text sentence for that image (accessibility + image SEO).

Respond ONLY with valid JSON, no markdown fences, no preamble, in this exact shape:
{
  "title": "an original, specific, search-friendly headline, different wording from the source",
  "dek": "one or two sentence summary of YOUR article, for display under the headline",
  "metaDescription": "140-155 character search snippet",
  "keywords": ["keyword phrase one", "keyword phrase two"],
  "imageQuery": "2-4 word literal visual search query",
  "imageAlt": "descriptive alt text for the article image",
  "body": [
    {"type": "p", "text": "opening hook paragraph..."},
    {"type": "p", "text": "..."},
    {"type": "h2", "text": "First subheading"},
    {"type": "p", "text": "..."},
    {"type": "h2", "text": "Second subheading"},
    {"type": "p", "text": "..."},
    {"type": "p", "text": "closing takeaway paragraph..."}
  ]
}
"""


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def guess_category(text, category_keywords):
    text_lower = text.lower()
    scores = {cat: 0 for cat in category_keywords}
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ai"


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60]


def fetch_new_items(config, state):
    seen = set(state.get("processed_links", []))
    new_items = []
    for feed_cfg in config["feeds"]:
        print(f"Fetching feed: {feed_cfg['name']} ({feed_cfg['url']})")
        parsed = feedparser.parse(feed_cfg["url"])
        for entry in parsed.entries:
            link = entry.get("link")
            if not link or link in seen:
                continue
            new_items.append({
                "source": feed_cfg["name"],
                "link": link,
                "title": entry.get("title", ""),
                "summary": re.sub("<[^<]+?>", "", entry.get("summary", ""))[:600],
                "default_category": feed_cfg.get("default_category", "ai"),
            })
    return new_items


def find_image(query, unsplash_key):
    """Finds a relevant, freely-licensed photo via Unsplash's API.
    Returns (image_url, photographer_name, photographer_url) or (None, None, None).
    Unsplash photos are free to use; crediting the photographer is required
    by Unsplash's guidelines and is included automatically on the article page.
    """
    if not unsplash_key:
        return None, None, None
    import urllib.request
    import urllib.parse

    url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode({
        "query": query, "per_page": 1, "orientation": "landscape"
    })
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {unsplash_key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("results"):
            photo = data["results"][0]
            return (
                photo["urls"]["regular"],
                photo["user"]["name"],
                photo["user"]["links"]["html"] + "?utm_source=circuit&utm_medium=referral",
            )
    except Exception as e:
        print(f"  ! Image search failed: {e}")
    return None, None, None


def write_article(client, model, item, category_keywords, unsplash_key=None):
    user_prompt = (
        f"Source: {item['source']}\n"
        f"Headline: {item['title']}\n"
        f"Summary: {item['summary']}\n\n"
        f"Write an original Circuit article inspired by this topic."
    )

    # Gemini's free tier can be briefly overloaded (503 UNAVAILABLE) during
    # high-traffic periods. This is transient, not a real failure, so retry
    # a few times with increasing delays before giving up on this item.
    max_attempts = 4
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=WRITER_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    max_output_tokens=2000,
                ),
            )
            break
        except Exception as e:
            is_last = attempt == max_attempts
            print(f"  ! Attempt {attempt}/{max_attempts} failed: {e}")
            if is_last:
                print("  ! Giving up on this item after repeated failures.")
                return None
            wait_seconds = 15 * attempt  # 15s, 30s, 45s
            print(f"  Retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)

    if response is None:
        return None

    raw_text = (response.text or "").strip()
    raw_text = re.sub(r"^```json\s*|\s*```$", "", raw_text)

    try:
        article = json.loads(raw_text)
    except json.JSONDecodeError:
        print("  ! Could not parse model output as JSON, skipping this item.")
        return None

    category = guess_category(item["title"] + " " + item["summary"], category_keywords)

    image_url, photographer, photographer_url = find_image(article.get("imageQuery", item["title"]), unsplash_key)

    body_word_count = sum(len(b.get("text", "").split()) for b in article["body"])

    post = {
        "slug": slugify(article["title"]),
        "title": article["title"],
        "dek": article["dek"],
        "metaDescription": article.get("metaDescription", article["dek"])[:160],
        "keywords": article.get("keywords", []),
        "category": category,
        "categoryLabel": CATEGORY_LABELS[category],
        "author": "Circuit Desk",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "readTime": f"{max(2, body_word_count // 200)} min read",
        "featured": False,
        "body": article["body"],
        "sourceName": item["source"],
        "sourceLink": item["link"],
    }

    if image_url:
        post["image"] = image_url
        post["imageAlt"] = article.get("imageAlt", article["title"])
        post["imageCredit"] = {"name": photographer, "url": photographer_url}

    return post


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set the GEMINI_API_KEY environment variable before running.")
        print("Get a free key at https://aistudio.google.com/app/apikey")
        sys.exit(1)
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not unsplash_key:
        print("Note: UNSPLASH_ACCESS_KEY not set — posts will use a fallback gradient instead of a photo.")

    config = load_json(CONFIG_FILE, {})
    state = load_json(STATE_FILE, {"processed_links": []})
    posts = load_json(DATA_FILE, [])

    new_items = fetch_new_items(config, state)
    if not new_items:
        print("No new items found. Nothing to do.")
        return

    max_new = config.get("max_new_posts_per_run", 3)
    new_items = new_items[:max_new]
    print(f"Found {len(new_items)} new item(s) to process (limit: {max_new} per run).")

    client = genai.Client(api_key=api_key)
    added = 0

    for item in new_items:
        print(f"Writing article for: {item['title'][:70]}...")
        try:
            post = write_article(client, config.get("model", "gemini-2.5-pro"), item, config["category_keywords"], unsplash_key)
        except Exception as e:
            print(f"  ! Error generating article: {e}")
            continue

        if not post:
            continue

        # Avoid slug collisions
        existing_slugs = {p["slug"] for p in posts}
        base_slug = post["slug"]
        n = 2
        while post["slug"] in existing_slugs:
            post["slug"] = f"{base_slug}-{n}"
            n += 1

        posts.append(post)
        state["processed_links"].append(item["link"])
        added += 1
        print(f"  + Added: {post['title']}")

    if added:
        # Newest post becomes featured, unfeature the rest
        posts_sorted = sorted(posts, key=lambda p: p["date"], reverse=True)
        for p in posts:
            p["featured"] = (p["slug"] == posts_sorted[0]["slug"])

        save_json(DATA_FILE, posts)
        save_json(STATE_FILE, state)
        print(f"\nSaved {added} new post(s) to posts_data.json.")

        print("Rebuilding website/posts.js ...")
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_posts_js.py")], check=True)
        print("Done.")
    else:
        print("No posts were successfully generated this run.")


if __name__ == "__main__":
    main()
