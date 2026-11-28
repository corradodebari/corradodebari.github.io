# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Corrado De Bari's personal GitHub Pages site (https://corradodebari.github.io/). It is a static site: no build step, no package manager, no tests and no linter. Pushing to `main` publishes it, so check before pushing.

Preview locally with:

```
python3 -m http.server 8000   # then open http://localhost:8000/index.html
```

## Page architecture

- `index.html` is the hand-written home page. It has a header, an "About Me" section, and link lists (Papers, Contributions, Training, Events). New articles are added to the **Papers** list as absolute `https://corradodebari.github.io/<page>.html` links. Watch out for doubled prefixes like `https://corradodebari.github.io/https://...`.
- Every other `*.html` is an **article shell** built from the same template. The `<head>` holds the SEO block: gtag `G-FKZH5GRJXL`, description/keywords, canonical, Open Graph/Twitter tags and a JSON-LD `TechArticle`. It also holds a page-local `<style>` block. The body is a single `#content` element (`<div>` or `<article>`). At runtime, marked.js (from the jsdelivr CDN) fetches a Markdown file into `#content`, and `addCopyButtons()` adds a Copy button to every `<pre>`.
- **Markdown comes from GitHub, not from local files.** Each shell's `mdUrl` points at `raw.githubusercontent.com/.../main/<file>.md`. Edits to a local `.md` don't show, even in a local preview, until they are pushed. The shell name often differs from the Markdown name (e.g. `spring_ai_paper.html` → `AI_SpringAI_RAG_Paper_final.md`, `selectai.html` → `selectai_local_db.md`, `graphtutorial1.html` → `GraphTutorial1.md`). Three shells (`basic_agent.html`, `basic_agent_nl2sql.html`, `automated_nl2sql_testing.html`) load Markdown from a different repo, `corradodebari/wayflow_samples`.
- Some shells contain static fallback/SEO text inside `#content` (e.g. `microtx-workflows-skill.html`). It is replaced once the Markdown loads.
- Images live under `images/` and are referenced from the Markdown by relative path.
- Loose `.py`, `.json`, `.sql` and `.sh` files at the root (e.g. `llm_chat_human_in_loop*.py/json`, `GraphTutorial.sql`, `workers_collection.py`) are sample code downloaded or linked from the articles, not site tooling.

## Light/dark theme

`theme.js` and `theme.css` at the root are shared by **every** page. Each page includes them right before `</head>`:

```html
<link rel="stylesheet" href="theme.css">
<script src="theme.js"></script>
```

- `theme.js` sets `html[data-theme]` before the page is drawn. It uses the saved `localStorage.theme` or the OS preference, and follows OS changes until the user picks a theme. It also injects the fixed `.theme-toggle` sun/moon button in the top-right corner.
- `theme.css` contains all dark-mode overrides as `html[data-theme="dark"] …` rules. They redefine the `index.html` CSS variables and override the hard-coded colors in the article template (code, `pre`, `.copy-btn`, tables, images). Dark-mode zebra striping only applies to pages with `<body class="zebra">`, i.e. the pages that stripe tables in light mode.
- **New pages** must include both lines, or they get no toggle. If a page's own `<style>` adds new hard-coded colors, add matching dark overrides to `theme.css`.

## Adding a new article

1. Copy an existing shell (e.g. `vllm.html`). Update `<title>`, the meta/OG/Twitter/JSON-LD fields, the canonical URL and `mdUrl`. Keep the `theme.css`/`theme.js` includes.
2. Add the `.md` file (and images under `images/`).
3. Link it at the top of the Papers list in `index.html`. Also add it to `sitemap.xml`, and to `llms.txt` if relevant. `llms.txt` is curated, not exhaustive: an entry needs both a page link with a one-line summary under a pages heading and the raw Markdown URL under "Source Markdown". `robots.txt` already allows all crawlers, AI ones included.
