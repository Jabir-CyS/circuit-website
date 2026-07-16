#!/usr/bin/env python3
"""
build_posts_js.py
------------------
Regenerates website/posts.js from posts_data.json.

posts_data.json is the single source of truth for all articles.
Run this script any time posts_data.json changes (manually, or by
the agent.py automation) to update the live site's data file.

Usage:
    python3 build_posts_js.py
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "posts_data.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "posts.js")

STORAGE_LAYER = '''
/* ---------- Storage layer ---------- */
const STORAGE_KEY = "circuit_posts_v1";

function loadPosts() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    console.warn("Could not read stored posts, falling back to defaults.", e);
  }
  savePosts(DEFAULT_POSTS);
  return DEFAULT_POSTS;
}

function savePosts(posts) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(posts));
    return true;
  } catch (e) {
    console.error("Could not save posts", e);
    return false;
  }
}

function getPostBySlug(slug) {
  return loadPosts().find(p => p.slug === slug) || null;
}

function slugify(str) {
  return str.toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 60);
}

function formatDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

function initials(name) {
  return name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase();
}

// Renders the structured body ([{type:"p"|"h2", text:"..."}]) as HTML
function renderBody(body) {
  return body.map(block => {
    if (block.type === "h2") return `<h2>${block.text}</h2>`;
    return `<p>${block.text}</p>`;
  }).join("");
}

// Returns HTML for a card/hero image: a real photo if present, else the gradient fallback
function imageBlockHtml(post, className) {
  if (post.image) {
    return `<img src="${post.image}" alt="${post.imageAlt || post.title}" class="${className}" loading="lazy">`;
  }
  return `<div class="${className} card-image ${post.category}"></div>`;
}
'''

HEADER = '''/* ============================================================
   Circuit — Posts data layer
   ------------------------------------------------------------
   AUTO-GENERATED FILE — do not hand-edit.
   Source of truth is posts_data.json — edit that file (or use
   admin.html, or let agent.py add posts to it), then run
   build_posts_js.py to regenerate this file.
   ============================================================ */

'''


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    js = HEADER + "const DEFAULT_POSTS = " + json.dumps(posts, indent=2, ensure_ascii=False) + ";\n" + STORAGE_LAYER

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(js)

    print(f"Wrote {len(posts)} posts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
