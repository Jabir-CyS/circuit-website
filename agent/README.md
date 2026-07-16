# Circuit — Auto-curator agent (powered by Gemini, free)

This agent watches tech news RSS feeds (TechCrunch, The Verge, Ars Technica —
easy to add more), and whenever a new story appears, it asks **Google Gemini**
(free, no credit card, no expiry) to write a genuinely original,
SEO-optimized article on that topic — complete with a relevant image — and
publishes it to your Circuit website automatically.

## Important — read this first

**It does not copy or rewrite the source articles.** It only ever sees the
public RSS headline + short summary (the same thing an RSS reader app
shows you) and is instructed to write something original — its own
wording, its own analysis — with a visible credit line back to the
original source at the end of every generated post. This keeps you on the
right side of copyright law. Do not remove the attribution line or change
the prompt to ask for closer copying — that turns this back into
infringement, and posting infringing content publicly carries real legal
and financial risk (DMCA takedowns, deindexing, account bans).

**Cost: $0, genuinely.** RSS feeds are free. Hosting is free (GitHub
Pages). GitHub Actions to run the schedule is free for reasonable use.
Unsplash images are free. Gemini's free tier (used here) has no credit
card requirement and doesn't expire — it's just rate-limited (see below),
which is why the schedule in this project is deliberately paced to stay
comfortably inside those limits.

### Gemini free tier limits (why the schedule is set the way it is)
`gemini-2.5-pro` free tier: roughly 5 requests/minute, ~50-100
requests/day. This project runs every 3 hours (8 runs/day) generating up
to 3 articles per run — max ~24 requests/day, safely under the limit.
If you want more volume, either raise the request budget by switching
`config.json`'s `"model"` to `"gemini-2.5-flash"` (much higher free daily
limit, slightly less polished writing), or just run more often — check
current limits at https://ai.google.dev/gemini-api/docs/rate-limits
since Google updates these periodically.

## What's in this folder

```
agent/
  agent.py                  the agent itself (writing + image search)
  build_posts_js.py         regenerates website/posts.js (used by admin.html)
  build_static.py           generates real static SEO pages: website/articles/*.html, sitemap.xml, robots.txt
  config.json               which RSS feeds to watch, category rules, model choice
  posts_data.json           source of truth for all posts (site + agent both read/write this)
  state.json                tracks which source articles have already been processed
  requirements.txt          Python dependencies
  .github/workflows/auto-post.yml   makes it run automatically, for free, on GitHub
```

## One-time setup

### 1. Get a free Gemini API key
Go to https://aistudio.google.com/app/apikey, sign in with a Google
account, and click "Create API key". No credit card needed.

### 2. (Recommended) Get a free Unsplash API key for article images
Go to https://unsplash.com/developers, create a free app, and copy the
"Access Key". This lets the agent attach a real, relevant, legally-free
photo to every article it writes (with proper photographer credit, as
required by Unsplash's guidelines). If you skip this, posts just use a
colored gradient placeholder instead — the site still works fine either way.

### 3. Set your real domain before deploying
Open `build_static.py` and change this line near the top to your actual
domain once you have one:
```python
SITE_URL = "https://example.com"
```
This matters for SEO — sitemap and canonical URLs need to point at your
real site, not a placeholder.

### 4. Put your website + agent folder into one GitHub repo
Create a new GitHub repo and upload both the `website/` folder and this
`agent/` folder into it, so the structure looks like:

```
your-repo/
  website/
    index.html
    articles/            <- generated automatically, don't hand-edit
    ...
  agent/
    agent.py
    ...
```

### 5. Add your API keys as GitHub secrets (never put them directly in code)
In your repo: Settings → Secrets and variables → Actions → New repository
secret.
- `GEMINI_API_KEY` — required
- `UNSPLASH_ACCESS_KEY` — optional, for images

### 6. Enable GitHub Pages for the website folder
Settings → Pages → Deploy from branch → choose the `website` folder as the
publish source. You'll get a live URL like
`https://yourusername.github.io/your-repo/`. Ideally connect a real
custom domain here too — it matters both for SEO and for AdSense.

### 7. Fill in the placeholder pages before you launch
- `website/contact.html` — replace the placeholder email
- `website/privacy-policy.html` and `website/terms.html` — fill in the
  `[DATE]` and bracketed placeholders; have an actual lawyer review these
  before you rely on them, especially once ads are live

### 8. Turn on the automation
The workflow in `.github/workflows/auto-post.yml` is already set to run
every 3 hours automatically once it's in your repo — no extra step
needed. You can also trigger it manually any time from the "Actions" tab
→ "Auto-post new articles" → "Run workflow" (good for your first test).

That's it. From here, whenever TechCrunch, The Verge, or Ars Technica
publish something new, within a few hours your site will have an original
Circuit article on the same topic — SEO-tagged, with a relevant image,
and credited back to the source. All for $0.

## Running it yourself, locally, without GitHub Actions

```bash
cd agent
pip install -r requirements.txt --break-system-packages
export GEMINI_API_KEY=your-key-here
export UNSPLASH_ACCESS_KEY=your-key-here   # optional
python3 agent.py
python3 build_static.py
```

You'd then need to re-upload/re-deploy the website folder yourself each
time (this is what the GitHub Actions workflow automates for you).

## Customizing

- **Add or remove sources**: edit the `feeds` list in `config.json`. Any
  site with a public RSS feed works — look for a `/feed/` or `/rss` URL
  on the site you want to follow.
- **Change how many posts per run / model**: `max_new_posts_per_run` and
  `model` in `config.json`. `gemini-2.5-pro` = better writing, tighter
  free daily limit. `gemini-2.5-flash` = more requests/day, slightly
  more generic writing.
- **Change the writing style or rules**: edit `WRITER_SYSTEM_PROMPT`
  inside `agent.py`.
- **Change how often it runs**: edit the `cron` line in
  `.github/workflows/auto-post.yml` (current: every 3 hours). Keep an
  eye on the free-tier limit math above if you increase frequency.

## If you'd rather review before publishing

Right now the agent auto-publishes immediately. If you want a review
step instead (recommended while you're getting comfortable with it),
the simplest change is: have `agent.py` write new posts into a separate
`drafts.json` file instead of `posts_data.json`, and manually copy
approved drafts over using `admin.html`. Ask if you'd like this version
built instead — it's a small change.

---

## About AdSense approval — an honest checklist

You mentioned wanting AdSense approved within a month. I can't promise a
timeline — that decision is entirely Google's, based on factors outside
anyone's control (their review queue, how they currently assess your
specific site and country, etc). What I *can* do is make sure this site
meets every requirement that's within your control:

**Already handled by this build:**
- ✅ Original content (not copied/spun — see the copyright note above)
- ✅ Clean, professional, easy-to-navigate design
- ✅ Working mobile + desktop navigation
- ✅ About, Contact, Privacy Policy, and Terms pages
- ✅ Fast-loading static pages, proper HTML structure, SEO meta tags

**Still on you before applying:**
- ⏳ **Enough content.** One article isn't enough — most successful
  applicants have 20-30+ solid, original posts before applying. At ~8-24
  posts/day capacity this builds up fast, but don't apply on day one.
- ⏳ **Some real traffic.** Share your articles, get real readers, submit
  `sitemap.xml` to Google Search Console so Google indexes the site.
- ⏳ **A real custom domain**, not just a raw `github.io` subdomain —
  strongly recommended, domains are cheap (~$10-15/year).
- ⏳ **Fill in the real contact email and finish the privacy/terms pages**
  with your actual business details.
- ⏳ **Apply via https://www.google.com/adsense** once the above is in
  place, and expect anywhere from a few days to several weeks for a
  decision — it varies.

A realistic, honest plan: spend the first 2-3 weeks letting the agent
build up a real archive of articles and getting a bit of organic traffic,
finish the legal pages, get a custom domain, then apply. That gives you
the best realistic shot within a month — but the final decision and
timing is Google's, not something any tool can guarantee.
