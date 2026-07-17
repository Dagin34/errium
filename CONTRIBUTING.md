# Contributing to Errium

Thank you for your interest in contributing to Errium! As an open-source project, we welcome community feedback, feature requests, bug reports, and pull requests.

---

## 🛠️ Development Setup

Errium utilizes the high-performance Python package manager `uv` to manage virtual environments and lockfiles.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Dagin34/errium.git
   cd errium
   ```

2. **Sync development dependencies**:
   ```bash
   uv sync
   ```

3. **Install the package in editable mode**:
   ```bash
   uv pip install -e .
   ```

---

## 🧪 Testing

We mandate high code coverage on all core operations. Ensure that your changes have appropriate unit and integration tests under the `tests/` directory.

Run the test suite using `pytest`:
```bash
uv run pytest
```

To run tests and capture short traceback outputs:
```bash
uv run pytest --tb=short
```

---

## 🧹 Code Style & Linting

We enforce PEP8 compliance, strong static typing, and structural cleanliness.

Run the linter and format checker via `ruff`:
```bash
uv run ruff check .
```

---

## 📚 Documentation

The documentation site is built with `mkdocs` + `mkdocs-material` from `mkdocs.yml`, pulling its
pages directly from this repo's root `.md` files (`docs/*.md` are symlinks — edit the root files,
not the symlinks).

Preview it locally:
```bash
uv run mkdocs serve
```

Build the static site (output goes to `site/`, which is gitignored):
```bash
uv run mkdocs build
```

---

## 🏷️ Commit Message Conventions

We adhere to the standard Angular Git commit message style:

```
<type>(<scope>): <subject>
```

- **feat**: A new feature (e.g. `feat(core): implement validation beautifier`).
- **fix**: A bug fix (e.g. `fix(fastapi): correct HTTPException status mapping`).
- **docs**: Documentation-only changes (e.g. `docs(readme): add usage examples`).
- **style**: Changes that do not affect code logic (whitespace, formatting, missing semi-colons).
- **refactor**: Code changes that neither fix bugs nor add features.
- **test**: Adding missing tests or correcting existing tests.

---

## 🌿 Branch Naming Rules

Maintain descriptive branch names prefixing the context:
- Features: `feature/short-desc` or `feat/short-desc`
- Bug fixes: `bugfix/short-desc` or `fix/short-desc`
- Documentation: `docs/short-desc`

---

## 🤝 Pull Request Rules

Before submitting your pull request:
1. Ensure the code passes all unit and integration tests.
2. Confirm there are no lingering lint errors (`uv run ruff check .`).
3. Keep the changes minimal and focused. Do not combine multiple unrelated features into a single PR.
4. Add clear descriptions of what the change does and why it was needed.
