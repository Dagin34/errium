# Errium Docs Restyle — Design

**Date:** 2026-09-03
**Status:** Approved (pending implementation)

## Problem

The docs site at https://dagin34.github.io/errium/ is content-complete and auto-deploys, but it
looks like every other mkdocs-material site: stock teal palette, stock Roboto. It carries no
identity connecting it to the author's other work.

The gap is *surface styling*, not structure, content, or tooling. A framework rewrite (SvelteKit)
was considered and rejected: it would break the `docs/*.md` → root-markdown symlinks that keep the
site in sync, add a Node toolchain to a pure-Python package, and require rebuilding search,
navigation, TOC, and syntax highlighting that Material provides for free.

## Approach

Restyle mkdocs-material in place by remapping its CSS design tokens. Material's components all
inherit from a small set of custom properties, so overriding those restyles the entire site
consistently without fighting individual selectors.

## Reference

Visual identity is taken from the author's portfolio, https://dagmawi.et (a SvelteKit +
Tailwind v4 site). Tokens extracted from its compiled CSS bundle:

| Role           | Value                       |
| -------------- | --------------------------- |
| Background     | `#030712`                   |
| Primary text   | `#ffffff`                   |
| Brand accent   | `#ff6900`                   |
| Borders        | `#1d202a`                   |
| Secondary text | `#9ca3af` (gray-400)        |
| Font           | Poppins                     |
| Max radius     | `1rem`                      |

## Scope

Three new files, one edited. **No markdown is touched**, so the symlinks and the README that
renders on GitHub and PyPI are unaffected.

| File                     | Change                                                      |
| ------------------------ | ----------------------------------------------------------- |
| `docs/assets/errium.css` | New. The entire restyle.                                     |
| `overrides/main.html`    | New. Material template override; injects the homepage hero.  |
| `mkdocs.yml`             | Register `custom_dir`, `extra_css`, Poppins, palette toggle. |

## Color

Dark is the default palette; light remains available via Material's toggle, restyled to match
rather than left stock. Docs are read in bright rooms and on projectors, and some readers need
light mode — so dark-only was rejected.

- **Dark** (`slate` scheme): background `#030712`, surfaces `#0b0f19`, text `#ffffff`, secondary
  `#9ca3af`, borders `#1d202a`, accent `#ff6900`.
- **Light** (`default` scheme): warm off-white ground, near-black text, the same `#ff6900` accent
  darkened slightly for contrast against white where it carries text.

Both palettes must clear WCAG AA (4.5:1) for body text and 3:1 for large text. Orange on
near-black passes comfortably; orange as *text on white* does not, so in light mode the accent is
reserved for borders, underlines, and fills rather than small text.

## Typography

Poppins throughout, differentiated by weight rather than paired with a second family. This matches
the portfolio, which also uses Poppins.

| Weight | Use                                    |
| ------ | -------------------------------------- |
| 700    | Page titles (`h1`), tracking `-0.02em` |
| 600    | Section headings (`h2`–`h4`)           |
| 500    | Nav, tabs, table headers, buttons      |
| 400    | Body copy                              |
| 300    | Hero subtitle, large quiet text        |

Poppins is geometric with a modest x-height, making it less comfortable than Inter for long
passages. Rather than swapping the font, compensate with `line-height: 1.75` and `0.95rem` body
text so longer documents (ARCHITECTURE.md) stay readable.

Code keeps a monospace stack; Poppins is not used for code.

## Code blocks

Material's stock Pygments highlighting clashes with a near-black ground and an orange accent, so
the code palette is tuned explicitly: `#0b0f19` block background, `#1d202a` border, orange
keywords, muted gray comments, white default text. Errium's README leads with a before/after JSON
comparison, so JSON and Python must both read well.

## Hero

A homepage-only band above the content: project name, one-line pitch, a copyable
`pip install errium` chip, and links to Quickstart, GitHub, and PyPI.

Implemented through `overrides/main.html`, **not** front-matter. The usual Material approach is a
`template:` key in `docs/index.md`, but that file is a symlink to `README.md`; adding front-matter
there would leak raw YAML onto the GitHub repo page and the PyPI project page. The override
inspects the page URL and renders the hero only when it is empty (the homepage).

## Non-goals

- No changes to documentation content, structure, or navigation.
- No JavaScript framework, build step, or Node dependency.
- No custom domain or hosting change; GitHub Pages deployment stays as-is.
- Not a landing page rebuild — if the homepage still feels flat after restyling, a bespoke landing
  page is a separate, later decision.

## Verification

- `uv run mkdocs build --strict` exits 0.
- Rendered `site/` output is inspected in a browser at both palettes and at mobile width.
- Contrast ratios spot-checked against WCAG AA for body text in both palettes.
- The README, ARCHITECTURE, ROADMAP, CHANGELOG, and CONTRIBUTING pages all render correctly, since
  the restyle is global.
- `git diff` confirms no markdown file was modified.
