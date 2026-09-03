# Errium Docs Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the Errium mkdocs-material docs site to match the visual identity of
https://dagmawi.et — near-black ground, orange accent, Poppins throughout — without touching any
documentation content.

**Architecture:** mkdocs-material exposes its entire design system through CSS custom properties.
Overriding those properties in one appended stylesheet restyles every component (nav, tabs,
search, admonitions, tables, footer) consistently, with no need to fight individual selectors. The
homepage hero is injected through Material's `{% block hero %}` template hook rather than page
front-matter, because `docs/index.md` is a symlink to `README.md`.

**Tech Stack:** mkdocs 1.6+, mkdocs-material 9.7.6, Jinja2 templates, plain CSS custom properties,
Google Fonts (Poppins). No JavaScript, no build step, no Node.

## Global Constraints

- **Never modify any `.md` file.** `docs/*.md` are symlinks to root markdown that renders on
  GitHub and PyPI. Every task must end with `git diff --stat -- '*.md'` empty.
- **mkdocs-material version is 9.7.6.** Template block names and CSS variable names in this plan
  were verified against that exact version.
- Brand tokens, copied verbatim from the spec: background `#030712`, primary text `#ffffff`,
  brand accent `#ff6900`, borders `#1d202a`, secondary text `#9ca3af`, max radius `1rem`.
- **Light-mode accent is `#c2410c`, not `#ff6900`.** `#ff6900` on white measures 2.89:1, which
  fails WCAG AA (4.5:1) and even the 3:1 large-text floor. `#c2410c` measures 5.18:1.
- Font is Poppins for all UI and prose; code keeps a monospace stack. Weights: 700 titles, 600
  headings, 500 UI, 400 body, 300 hero subtitle.
- **Material only requests Poppins `300,400,700` from Google Fonts.** Weights 500 and 600 are not
  loaded by default and would be synthesized by the browser (faux-bold, visibly muddy). Task 1
  overrides `{% block fonts %}` to request `300;400;500;600;700`. Verified: the CSS2 endpoint
  returns all five.
- `uv run mkdocs build --strict` must exit 0 after every task.
- Commit after every task.

---

### Task 1: Wire up theming scaffolding

Registers the custom stylesheet, the template override, Poppins at every weight the design uses,
and the two-palette toggle. Produces no visual identity yet beyond the font — that lands in Task 2. This task is
separate because a reviewer can reject the *wiring* (wrong config keys, broken build) independently
of the *design*.

**Files:**
- Create: `docs/assets/errium.css`
- Create: `overrides/main.html`
- Modify: `mkdocs.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: `docs/assets/errium.css` loaded on every page as the last stylesheet (so its
  declarations win over Material's); `overrides/main.html` extending `base.html`, which Task 5
  adds the `hero` block to; `[data-md-color-scheme=slate]` active by default and
  `[data-md-color-scheme=default]` reachable via the header toggle.

- [ ] **Step 1: Create the (initially near-empty) stylesheet**

```bash
mkdir -p docs/assets overrides
```

Write `docs/assets/errium.css`:

```css
/* Errium docs theme — visual identity from https://dagmawi.et
   Loaded after Material's own stylesheets, so these declarations win. */

:root {
  --errium-radius: 0.75rem;
}
```

- [ ] **Step 2: Rewrite the `theme` block and add `extra_css` in `mkdocs.yml`**

Replace the existing `theme:` block (which currently starts `name: material` and contains the
`palette`, `features` keys) with the following. Note `custom_dir`, the added `font` key, and that
both palette entries now carry an explicit `scheme`, `primary`, and `accent`:

```yaml
theme:
  name: material
  custom_dir: overrides
  font:
    text: Poppins
    code: Roboto Mono
  palette:
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: black
      accent: deep orange
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: black
      accent: deep orange
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
  features:
    - navigation.tabs
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
```

Then add this top-level key immediately after the `theme:` block:

```yaml
extra_css:
  - assets/errium.css
```

Note the dark entry is listed **first**, making it the default.

- [ ] **Step 3: Override the fonts block to load every weight the design uses**

Material's `base.html` hardcodes its Google Fonts request to `300,300i,400,400i,700,700i`. The
type scale in Task 2 uses **500** (nav, tabs, table headers) and **600** (headings), neither of
which that request loads — browsers would synthesize them as faux-bold, which looks visibly muddy.

Create `overrides/main.html`. It reads the family names from `mkdocs.yml` so there is a single
source of truth, and only the weight list is hardcoded:

```html
{% extends "base.html" %}

{#- Material requests only 300/400/700. The Errium type scale also uses 500 and 600,
    so the font request is widened here to avoid synthesized (faux-bold) weights. -#}
{% block fonts %}
  {% set text = config.theme.font.text | d("Poppins", true) %}
  {% set code = config.theme.font.code | d("Roboto Mono", true) %}
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={{
      text | replace(' ', '+') }}:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family={{
      code | replace(' ', '+') }}:wght@400;700&display=swap">
  <style>:root{--md-text-font:"{{ text }}";--md-code-font:"{{ code }}"}</style>
{% endblock %}
```

- [ ] **Step 4: Build and confirm the stylesheet, font, and weights are wired**

Run:

```bash
uv run mkdocs build --strict && \
  grep -c "assets/errium.css" site/index.html && \
  grep -o "family=Poppins[^\"&]*" site/index.html
```

Expected: mkdocs exits 0, the `grep -c` prints `>= 1`, and the last line shows the weight list
including `0,500` and `0,600`. If the weights are missing, `custom_dir: overrides` is absent from
`mkdocs.yml` and the override is being ignored.

- [ ] **Step 5: Confirm no markdown was touched**

Run: `git diff --stat -- '*.md'`
Expected: empty output.

- [ ] **Step 6: Commit**

```bash
git add mkdocs.yml docs/assets/errium.css overrides/main.html
git commit -m "Chore - Wire up custom docs theme scaffolding and Poppins."
```

---

### Task 2: Dark palette and typography

The core of the restyle. After this task the site should read as Errium's, not Material's default.

**Files:**
- Modify: `docs/assets/errium.css`

**Interfaces:**
- Consumes: `docs/assets/errium.css` and the `slate` scheme from Task 1.
- Produces: the `--errium-*` brand token set on `:root`, consumed by Tasks 3, 4, and 5.

- [ ] **Step 1: Append brand tokens and the dark palette**

Append to `docs/assets/errium.css`:

```css
/* ---- Brand tokens ------------------------------------------------------ */

:root {
  --errium-orange: #ff6900;
  --errium-orange-dim: #c2410c;
  --errium-ink: #030712;
  --errium-surface: #0b0f19;
  --errium-border: #1d202a;
  --errium-muted: #9ca3af;
}

/* ---- Dark palette (default) -------------------------------------------- */

[data-md-color-scheme="slate"] {
  --md-default-bg-color: var(--errium-ink);
  --md-default-fg-color: #ffffff;
  --md-default-fg-color--light: var(--errium-muted);
  --md-default-fg-color--lighter: #6b7280;

  --md-primary-fg-color: var(--errium-ink);
  --md-primary-bg-color: #ffffff;
  --md-accent-fg-color: var(--errium-orange);
  --md-typeset-a-color: var(--errium-orange);

  --md-footer-bg-color: var(--errium-surface);
  --md-footer-bg-color--dark: var(--errium-ink);
}

/* Header and footer sit flush against the page with a hairline rule. */
[data-md-color-scheme="slate"] .md-header,
[data-md-color-scheme="slate"] .md-tabs {
  background-color: var(--errium-ink);
  border-bottom: 1px solid var(--errium-border);
  box-shadow: none;
}
```

- [ ] **Step 2: Append the typography scale**

Append to `docs/assets/errium.css`:

```css
/* ---- Typography -------------------------------------------------------- */

.md-typeset {
  font-size: 0.95rem;
  line-height: 1.75;
}

.md-typeset h1 {
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-default-fg-color);
}

.md-typeset h2 {
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-top: 2.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--errium-border);
}

.md-typeset h3,
.md-typeset h4 {
  font-weight: 600;
}

.md-nav,
.md-tabs__link,
.md-typeset table th {
  font-weight: 500;
}

.md-typeset a {
  text-underline-offset: 0.2em;
}

.md-typeset a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 3: Append table and admonition treatment**

Append to `docs/assets/errium.css`:

```css
/* ---- Surfaces ---------------------------------------------------------- */

.md-typeset table:not([class]) {
  border: 1px solid var(--errium-border);
  border-radius: var(--errium-radius);
  overflow: hidden;
}

.md-typeset table:not([class]) th {
  background-color: var(--errium-surface);
}

.md-typeset .admonition,
.md-typeset details {
  border-radius: var(--errium-radius);
  border-width: 1px;
  border-left-width: 3px;
  box-shadow: none;
}
```

- [ ] **Step 4: Build and inspect in a browser**

Run:

```bash
uv run mkdocs build --strict && uv run mkdocs serve
```

Open http://127.0.0.1:8000. Expected: near-black background, white body text, orange links,
Poppins throughout, hairline rules above `h2` headings. Confirm the nav sidebar, the search
overlay (press `/`), and the footer all follow the dark palette with no leftover teal.
Stop the server with Ctrl-C.

- [ ] **Step 5: Confirm no markdown was touched, then commit**

```bash
git diff --stat -- '*.md'
git add docs/assets/errium.css
git commit -m "Chore - Add Errium dark palette and Poppins type scale to docs."
```

Expected: the `git diff --stat` prints nothing.

---

### Task 3: Light palette and a contrast check

Light mode is not left stock — it is restyled to match, with the accent swapped to the accessible
`#c2410c`. This task also adds a runnable contrast check so the AA claim is verified, not asserted.

**Files:**
- Modify: `docs/assets/errium.css`
- Create: `scripts/check_contrast.py`

**Interfaces:**
- Consumes: the `--errium-*` tokens from Task 2.
- Produces: `scripts/check_contrast.py`, runnable as `uv run python scripts/check_contrast.py`,
  exiting `0` when every checked pair meets its WCAG target and `1` otherwise.

- [ ] **Step 1: Write the contrast checker**

Create `scripts/check_contrast.py`:

```python
"""Verify the docs palette meets WCAG AA contrast targets.

Run: uv run python scripts/check_contrast.py
"""

from __future__ import annotations

import sys

# (label, foreground, background, minimum ratio)
PAIRS: list[tuple[str, str, str, float]] = [
    ("dark: body text on ground", "#ffffff", "#030712", 4.5),
    ("dark: muted text on ground", "#9ca3af", "#030712", 4.5),
    ("dark: accent link on ground", "#ff6900", "#030712", 4.5),
    ("dark: body text on surface", "#ffffff", "#0b0f19", 4.5),
    ("light: body text on ground", "#111827", "#faf9f7", 4.5),
    ("light: accent link on ground", "#c2410c", "#faf9f7", 4.5),
]


def _channel(value: int) -> float:
    srgb = value / 255
    if srgb <= 0.03928:
        return srgb / 12.92
    return ((srgb + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(fg: str, bg: str) -> float:
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def main() -> int:
    failures = 0
    for label, fg, bg, minimum in PAIRS:
        value = ratio(fg, bg)
        ok = value >= minimum
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {value:5.2f}:1  (min {minimum})  {label}")
    if failures:
        print(f"\n{failures} pair(s) below target.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it and watch it pass**

Run: `uv run python scripts/check_contrast.py`

Expected: six `PASS` lines, exit code 0. Notable values: the accent-on-ground pair reports
`6.98:1`, and light accent reports about `5.15:1`.

- [ ] **Step 3: Prove the check actually catches a failure**

Temporarily change the light accent pair's foreground from `#c2410c` to `#ff6900`, then rerun.

Run: `uv run python scripts/check_contrast.py; echo "exit=$?"`
Expected: that line reads `FAIL   2.89:1` and `exit=1`.

**Revert the edit back to `#c2410c` before continuing.**

- [ ] **Step 4: Append the light palette**

Append to `docs/assets/errium.css`:

```css
/* ---- Light palette ----------------------------------------------------- */

[data-md-color-scheme="default"] {
  --md-default-bg-color: #faf9f7;
  --md-default-fg-color: #111827;
  --md-default-fg-color--light: #4b5563;

  --md-primary-fg-color: #111827;
  --md-primary-bg-color: #ffffff;
  --md-accent-fg-color: var(--errium-orange-dim);
  --md-typeset-a-color: var(--errium-orange-dim);

  --md-footer-bg-color: #111827;
}

[data-md-color-scheme="default"] {
  --errium-surface: #f3f1ee;
  --errium-border: #e2ddd6;
}

[data-md-color-scheme="default"] .md-header,
[data-md-color-scheme="default"] .md-tabs {
  background-color: #111827;
  border-bottom: 1px solid #111827;
  box-shadow: none;
}
```

Because Task 2's rules reference `var(--errium-surface)` and `var(--errium-border)`, redefining
those two tokens inside the light scheme automatically retunes the tables, admonitions, and `h2`
rules — no duplicated selectors.

- [ ] **Step 5: Build and check both palettes in the browser**

Run: `uv run mkdocs build --strict && uv run mkdocs serve`

Open http://127.0.0.1:8000 and use the header toggle. Expected: light mode shows a warm off-white
ground, dark ink text, and a deeper orange for links; nothing retains Material's teal. Stop with
Ctrl-C.

- [ ] **Step 6: Confirm no markdown was touched, then commit**

```bash
git diff --stat -- '*.md'
git add docs/assets/errium.css scripts/check_contrast.py
git commit -m "Chore - Add tuned light palette and a WCAG contrast check for the docs."
```

---

### Task 4: Code block treatment

Errium's README leads with a before/after JSON comparison, so code blocks are the most important
content on the site. Material's stock highlighting clashes with a near-black ground.

**Files:**
- Modify: `docs/assets/errium.css`

**Interfaces:**
- Consumes: the `--errium-*` tokens from Tasks 2 and 3.
- Produces: no tokens consumed by later tasks.

- [ ] **Step 1: Append code block surfaces and syntax colors**

Append to `docs/assets/errium.css`:

```css
/* ---- Code -------------------------------------------------------------- */

.md-typeset pre > code,
.md-typeset .highlight {
  border-radius: var(--errium-radius);
}

[data-md-color-scheme="slate"] {
  --md-code-bg-color: var(--errium-surface);
  --md-code-fg-color: #e5e7eb;
}

[data-md-color-scheme="slate"] .md-typeset pre > code {
  border: 1px solid var(--errium-border);
}

/* Pygments token colors, dark. */
[data-md-color-scheme="slate"] .md-typeset .highlight .k,   /* keyword */
[data-md-color-scheme="slate"] .md-typeset .highlight .kn,
[data-md-color-scheme="slate"] .md-typeset .highlight .kd,
[data-md-color-scheme="slate"] .md-typeset .highlight .ow {
  color: var(--errium-orange);
  font-weight: 500;
}

[data-md-color-scheme="slate"] .md-typeset .highlight .s,   /* string */
[data-md-color-scheme="slate"] .md-typeset .highlight .s1,
[data-md-color-scheme="slate"] .md-typeset .highlight .s2,
[data-md-color-scheme="slate"] .md-typeset .highlight .sb {
  color: #86efac;
}

[data-md-color-scheme="slate"] .md-typeset .highlight .c,   /* comment */
[data-md-color-scheme="slate"] .md-typeset .highlight .c1,
[data-md-color-scheme="slate"] .md-typeset .highlight .cm {
  color: #6b7280;
  font-style: italic;
}

[data-md-color-scheme="slate"] .md-typeset .highlight .nt,  /* JSON key / tag */
[data-md-color-scheme="slate"] .md-typeset .highlight .nf {
  color: #93c5fd;
}

[data-md-color-scheme="slate"] .md-typeset .highlight .mi,  /* number */
[data-md-color-scheme="slate"] .md-typeset .highlight .mf,
[data-md-color-scheme="slate"] .md-typeset .highlight .kc { /* true/false/null */
  color: #fbbf24;
}

/* Inline code reads as a chip, not a block. */
.md-typeset code:not(pre code) {
  border-radius: 0.35rem;
  padding: 0.1em 0.4em;
  font-size: 0.85em;
}

[data-md-color-scheme="slate"] .md-typeset code:not(pre code) {
  background-color: #171b26;
  color: #fdba74;
}
```

- [ ] **Step 2: Build and inspect the before/after JSON on the homepage**

Run: `uv run mkdocs build --strict && uv run mkdocs serve`

Open http://127.0.0.1:8000 and scroll to the "Before vs. After" section. Expected: JSON keys read
blue, strings green, numbers/booleans amber, on a `#0b0f19` block with a hairline border. Scroll to
a Python example and confirm keywords are orange and comments are muted gray italic. Toggle to
light mode and confirm code blocks are still legible (they inherit Material's light defaults, which
is acceptable — only the dark palette is overridden here). Stop with Ctrl-C.

- [ ] **Step 3: Confirm no markdown was touched, then commit**

```bash
git diff --stat -- '*.md'
git add docs/assets/errium.css
git commit -m "Chore - Tune code block and syntax colors for the dark docs palette."
```

---

### Task 5: Homepage hero

**Files:**
- Modify: `overrides/main.html` (created in Task 1)
- Modify: `docs/assets/errium.css`

**Interfaces:**
- Consumes: `overrides/main.html` and `theme.custom_dir: overrides` from Task 1; `--errium-*`
  tokens from Tasks 2 and 3.
- Produces: a `.errium-hero` band rendered only when `page.is_homepage` is true.

- [ ] **Step 1: Add the hero block to the existing template override**

`overrides/main.html` already exists from Task 1 and already has `{% extends "base.html" %}` at the
top plus a `fonts` block. **Append** the following block to it — do not recreate the file, and do
not add a second `extends` line. The `hero` block in mkdocs-material 9.7.6 sits inside
`.md-container`, directly after the header and before the tabs:

```html
{% block hero %}
  {% if page.is_homepage %}
    <section class="errium-hero">
      <div class="errium-hero__inner">
        <h1 class="errium-hero__title">Errium</h1>
        <p class="errium-hero__tagline">
          One consistent, frontend-safe JSON shape for every API error &mdash;
          across FastAPI, Flask, Django Ninja, and Django REST Framework.
        </p>
        <div class="errium-hero__install">
          <code>pip install errium</code>
        </div>
        <div class="errium-hero__actions">
          <a class="errium-btn errium-btn--primary" href="{{ 'index.html#-installation' | url }}">Quickstart</a>
          <a class="errium-btn" href="https://github.com/Dagin34/errium">GitHub</a>
          <a class="errium-btn" href="https://pypi.org/project/errium/">PyPI</a>
        </div>
      </div>
    </section>
  {% endif %}
{% endblock %}
```

- [ ] **Step 2: Append hero styles**

Append to `docs/assets/errium.css`:

```css
/* ---- Homepage hero ----------------------------------------------------- */

.errium-hero {
  border-bottom: 1px solid var(--errium-border);
  background: radial-gradient(
    ellipse 80% 60% at 50% 0%,
    rgba(255, 105, 0, 0.10),
    transparent 70%
  );
}

.errium-hero__inner {
  max-width: 46rem;
  margin: 0 auto;
  padding: 4rem 1.5rem 3.5rem;
  text-align: center;
}

.errium-hero__title {
  font-size: 3.25rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin: 0;
  color: var(--md-default-fg-color);
}

.errium-hero__tagline {
  font-size: 1.05rem;
  font-weight: 300;
  line-height: 1.65;
  margin: 1rem auto 2rem;
  max-width: 34rem;
  color: var(--md-default-fg-color--light);
}

.errium-hero__install {
  margin-bottom: 2rem;
}

.errium-hero__install code {
  display: inline-block;
  padding: 0.7rem 1.25rem;
  border: 1px solid var(--errium-border);
  border-radius: var(--errium-radius);
  background-color: var(--errium-surface);
  font-size: 0.9rem;
}

.errium-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: center;
}

.errium-btn {
  display: inline-block;
  padding: 0.6rem 1.4rem;
  border: 1px solid var(--errium-border);
  border-radius: var(--errium-radius);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--md-default-fg-color);
  text-decoration: none;
  transition: border-color 120ms ease, transform 120ms ease;
}

.errium-btn:hover {
  border-color: var(--errium-orange);
  transform: translateY(-1px);
}

.errium-btn--primary {
  background-color: var(--errium-orange);
  border-color: var(--errium-orange);
  color: #ffffff;
}

.errium-btn--primary:hover {
  background-color: #e65f00;
  border-color: #e65f00;
}

/* The README's own H1 duplicates the hero title on the homepage. */
.md-content__inner > h1:first-of-type {
  display: none;
}

@media screen and (max-width: 44.9375em) {
  .errium-hero__inner {
    padding: 2.5rem 1.25rem 2.25rem;
  }

  .errium-hero__title {
    font-size: 2.25rem;
  }
}
```

- [ ] **Step 3: Verify the hero renders on the homepage and nowhere else**

Run:

```bash
uv run mkdocs build --strict && \
  echo "home:      $(grep -c 'errium-hero' site/index.html)" && \
  echo "changelog: $(grep -c 'errium-hero' site/changelog/index.html)" && \
  echo "roadmap:   $(grep -c 'errium-hero' site/roadmap/index.html)"
```

Expected: `home:` is `>= 1`; `changelog:` and `roadmap:` are both `0`.

If the hero appears on every page, `page.is_homepage` was omitted from the template.
If it appears nowhere, `custom_dir: overrides` is missing from `mkdocs.yml` (Task 1, Step 2), or a
second `{% extends %}` line was added and Jinja is rendering the wrong template.

- [ ] **Step 4: Inspect the hero in the browser at both widths**

Run: `uv run mkdocs serve`

Open http://127.0.0.1:8000. Expected: a centered hero with a soft orange glow behind the title, the
install chip, and three buttons; the README's own "Errium – Intelligent API Error Normalization for
FastAPI" H1 is hidden so the title is not duplicated. Narrow the window below 720px and confirm the
title drops to 2.25rem and the buttons wrap rather than overflow. Toggle to light mode and confirm
the hero still reads correctly. Stop with Ctrl-C.

- [ ] **Step 5: Confirm no markdown was touched, then commit**

```bash
git diff --stat -- '*.md'
git add overrides/main.html docs/assets/errium.css
git commit -m "Feature - Add a homepage hero to the docs site."
```

---

### Task 6: Final verification

**Files:** none modified.

- [ ] **Step 1: Run the full check suite**

```bash
uv run mkdocs build --strict && \
uv run python scripts/check_contrast.py && \
uv run pytest -q && \
uv run ruff check . && \
uv run mypy src
```

Expected: every command exits 0. `ruff` and `mypy` cover `scripts/check_contrast.py` now that it
exists; if ruff flags it, fix the lint rather than excluding the file.

- [ ] **Step 2: Prove no documentation content changed**

```bash
git diff --stat b856e0a..HEAD -- '*.md' ':!CHANGELOG.md' ':!specs/*' ':!plans/*'
```

Expected: empty. (`CHANGELOG.md`, `specs/`, and `plans/` are excluded because earlier release and
planning work legitimately touched them.)

- [ ] **Step 3: Review every page at both palettes**

Run `uv run mkdocs serve` and visit Home, Architecture, Roadmap, Changelog, and Contributing in
both light and dark. Confirm no page has unstyled or teal leftovers, and that long documents
(Architecture is 294 lines) read comfortably at `0.95rem` Poppins.

- [ ] **Step 4: Push and confirm the deploy**

```bash
git push origin main
gh run watch --exit-status
```

The `Deploy Docs` workflow triggers on `mkdocs.yml` and `docs/**`, both of which changed.
Then confirm https://dagin34.github.io/errium/ serves the restyled site.

---

## Notes

- **`overrides/` is not inside `docs/`.** It is a sibling directory, so its templates are never
  published as documentation pages.
- **Plans and specs live at the repo root, not in `docs/`.** Anything under `docs/` is rendered
  and published to the public site — verified by building with a probe file present.
- If Material is upgraded past 9.7.6, re-check that `{% block hero %}` still exists in
  `base.html`; template blocks are not covered by semver guarantees.
