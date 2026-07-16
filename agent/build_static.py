#!/usr/bin/env python3
"""
build_static.py — professional SEO build step
------------------------------------------------
Client-side (JS-rendered) pages are convenient, but search engines and
AdSense's review crawler get a much stronger signal from real, pre-built
HTML — the title, description, and full article text should already be
in the page source, not injected afterward by JavaScript.

This script reads posts_data.json and generates, for every post:
  website/articles/<slug>.html
    - a real <title> and <meta name="description">
    - Open Graph + Twitter Card tags (for clean link previews when shared)
    - a canonical URL tag
    - JSON-LD Article structured data (helps Google understand the page
      and can enable rich results)
    - the full article content already in the HTML, not loaded via JS

It also generates:
  website/sitemap.xml   — tells search engines every URL that exists
  website/robots.txt    — tells search engines they're allowed to crawl,
                           and points them at the sitemap

Run this after every change to posts_data.json (agent.py already does
this automatically as its last step).

IMPORTANT: set SITE_URL below to your real deployed domain before your
first deploy — sitemap/canonical URLs need to be correct for SEO to work.
"""

import json
import os
import html as html_lib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "posts_data.json")
WEBSITE_DIR = os.path.join(BASE_DIR, "..")
ARTICLES_DIR = os.path.join(WEBSITE_DIR, "articles")

# ⚠️ CHANGE THIS to your real domain before deploying (no trailing slash)
SITE_URL = "https://example.com"
SITE_NAME = "Circuit"

FONT_LINKS = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">'''


def esc(text):
    return html_lib.escape(text or "", quote=True)


def render_body_html(body):
    parts = []
    for block in body:
        if block["type"] == "h2":
            parts.append(f"<h2>{esc(block['text'])}</h2>")
        else:
            parts.append(f"<p>{esc(block['text'])}</p>")
    return "\n        ".join(parts)


def render_image_block(post, css_class):
    if post.get("image"):
        alt = esc(post.get("imageAlt", post["title"]))
        return f'<img src="{post["image"]}" alt="{alt}" class="{css_class}" loading="eager" width="1080" height="742">'
    return f'<div class="{css_class} card-image {post["category"]}"></div>'


def render_card(p, base_path=""):
    img = render_image_block(p, "card-thumb")
    return f'''<article class="card">
        <a href="{base_path}articles/{p['slug']}.html">
          {img}
          <span class="tag {p['category']}">{esc(p['categoryLabel'])}</span>
          <h3>{esc(p['title'])}</h3>
          <p>{esc(p['dek'])}</p>
          <p class="byline">By <strong>{esc(p['author'])}</strong> · {esc(p['readTime'])}</p>
        </a>
      </article>'''


ARTICLE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {site_name}</title>
<meta name="description" content="{meta_description}">
<meta name="keywords" content="{keywords}">
<link rel="canonical" href="{canonical_url}">

<!-- Open Graph -->
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_description}">
<meta property="og:url" content="{canonical_url}">
<meta property="og:site_name" content="{site_name}">
{og_image}
<meta property="article:published_time" content="{date}">
<meta property="article:author" content="{author}">
<meta property="article:section" content="{category_label}">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{meta_description}">
{twitter_image}

<!-- Structured data -->
<script type="application/ld+json">
{json_ld}
</script>

{font_links}
<link rel="stylesheet" href="../style.css">
</head>
<body>

<header>
  <div class="header-inner">
    <a href="../index.html" class="logo">{site_name}</a>
    <nav>
      <ul>
        <li><a href="../category.html?cat=ai">AI</a></li>
        <li><a href="../category.html?cat=startup">Startups</a></li>
        <li><a href="../category.html?cat=security">Security</a></li>
        <li><a href="../category.html?cat=apps">Apps</a></li>
        <li><a href="../category.html?cat=reviews">Reviews</a></li>
      </ul>
    </nav>
    <div class="nav-right">
      <a href="../index.html#newsletter" class="subscribe-btn">Subscribe</a>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>

<div class="nav-overlay"></div>
<nav class="mobile-nav" aria-label="Mobile navigation">
  <ul>
    <li><a href="../category.html?cat=ai">AI</a></li>
    <li><a href="../category.html?cat=startup">Startups</a></li>
    <li><a href="../category.html?cat=security">Security</a></li>
    <li><a href="../category.html?cat=apps">Apps</a></li>
    <li><a href="../category.html?cat=reviews">Reviews</a></li>
  </ul>
  <a href="../index.html#newsletter" class="subscribe-btn">Subscribe</a>
</nav>

<main>
  <section class="article-header">
    <div class="wrap">
      <p class="breadcrumb"><a href="../index.html">{site_name}</a> / <a href="../category.html?cat={category}">{category_label}</a></p>
      <span class="tag {category}">{category_label}</span>
      <h1>{title}</h1>
      <p class="article-dek">{dek}</p>
      <div class="article-meta">
        <span class="avatar">{initials}</span>
        <span><strong style="color:var(--ink-soft); font-weight:600;">{author}</strong> · {display_date} · {read_time}</span>
      </div>
    </div>
    <div class="wrap">
      {hero_image}
      {image_credit}
    </div>
  </section>

  <article class="article-body">
    {body_html}
  </article>

  <div class="article-footer">
    <p class="byline">Written by <strong>{author}</strong></p>
    {source_credit}
    <div class="share-row">
      <a href="https://twitter.com/intent/tweet?url={canonical_url}&text={title_urlsafe}" target="_blank" rel="noopener">Share on X</a>
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={canonical_url}" target="_blank" rel="noopener">Share on LinkedIn</a>
    </div>
  </div>

  {related_section}
</main>

<footer>
  <div class="wrap">
    <div class="footer-inner">
      <a href="../index.html" class="logo">{site_name}</a>
      <ul class="footer-links">
        <li><a href="../about.html">About</a></li>
        <li><a href="../contact.html">Contact</a></li>
        <li><a href="../privacy-policy.html">Privacy</a></li>
        <li><a href="../terms.html">Terms</a></li>
      </ul>
    </div>
    <p class="copyright">© {year} {site_name}. All rights reserved.</p>
  </div>
</footer>

<script src="../script.js"></script>
</body>
</html>
'''


def build_articles(posts):
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    for post in posts:
        canonical_url = f"{SITE_URL}/articles/{post['slug']}.html"
        keywords = ", ".join(post.get("keywords", []))
        og_image = twitter_image = ""
        if post.get("image"):
            og_image = f'<meta property="og:image" content="{esc(post["image"])}">'
            twitter_image = f'<meta name="twitter:image" content="{esc(post["image"])}">'

        image_credit = ""
        if post.get("image") and post.get("imageCredit", {}).get("name"):
            image_credit = (
                f'<p class="image-credit">Photo by '
                f'<a href="{esc(post["imageCredit"]["url"])}" target="_blank" rel="noopener">{esc(post["imageCredit"]["name"])}</a>'
                f' / Unsplash</p>'
            )

        source_credit = ""
        if post.get("sourceName") and post.get("sourceLink"):
            source_credit = (
                f'<p class="byline" style="margin-top:6px;">Inspired by reporting from '
                f'<a href="{esc(post["sourceLink"])}" target="_blank" rel="noopener" style="color:var(--accent);">{esc(post["sourceName"])}</a></p>'
            )

        # Related posts (same category, excluding self) — real HTML links = real internal linking, good for SEO
        related = [p for p in posts if p["category"] == post["category"] and p["slug"] != post["slug"]][:3]
        related_section = ""
        if related:
            cards = "\n      ".join(render_card(p, base_path="") for p in related)
            related_section = f'''<section class="section">
    <div class="wrap">
      <h3 class="related-heading">More in {esc(post['categoryLabel'])}</h3>
      <div class="grid">
      {cards}
      </div>
    </div>
  </section>'''

        json_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": post["title"],
            "description": post.get("metaDescription", post["dek"]),
            "image": [post["image"]] if post.get("image") else [],
            "datePublished": post["date"],
            "author": {"@type": "Person", "name": post["author"]},
            "publisher": {"@type": "Organization", "name": SITE_NAME},
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
        }, indent=2)

        html_out = ARTICLE_TEMPLATE.format(
            title=esc(post["title"]),
            title_urlsafe=esc(post["title"]).replace(" ", "%20"),
            meta_description=esc(post.get("metaDescription", post["dek"])),
            keywords=esc(keywords),
            canonical_url=canonical_url,
            site_name=SITE_NAME,
            og_image=og_image,
            twitter_image=twitter_image,
            date=post["date"],
            author=esc(post["author"]),
            category_label=esc(post["categoryLabel"]),
            category=post["category"],
            json_ld=json_ld,
            font_links=FONT_LINKS,
            dek=esc(post["dek"]),
            initials="".join(w[0] for w in post["author"].split()[:2]).upper(),
            display_date=post["date"],
            read_time=esc(post["readTime"]),
            hero_image=render_image_block(post, "article-hero-image"),
            image_credit=image_credit,
            body_html=render_body_html(post["body"]),
            source_credit=source_credit,
            related_section=related_section,
            year=post["date"][:4],
        )

        out_path = os.path.join(ARTICLES_DIR, f"{post['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_out)

    print(f"Generated {len(posts)} static article pages in {ARTICLES_DIR}")


def build_sitemap(posts):
    urls = [f"{SITE_URL}/index.html", f"{SITE_URL}/about.html", f"{SITE_URL}/contact.html"]
    urls += [f"{SITE_URL}/articles/{p['slug']}.html" for p in posts]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"  <url><loc>{u}</loc></url>")
    xml.append("</urlset>")

    with open(os.path.join(WEBSITE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(xml))
    print(f"Generated sitemap.xml with {len(urls)} URLs")


def build_robots():
    content = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    with open(os.path.join(WEBSITE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(content)
    print("Generated robots.txt")


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    build_articles(posts)
    build_sitemap(posts)
    build_robots()


if __name__ == "__main__":
    main()
