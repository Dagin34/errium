# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] — 2026-09-15

Documentation-only release. No code changes — published so the new documentation site is linked
from the PyPI project page, which snapshots project metadata and the README per version.

### Changed

- Documentation moved to https://errium.dagmawi.et/. The `Homepage` and `Documentation` project
  URLs now point there instead of at the previous MkDocs site on GitHub Pages, and the README
  links to it.
- The MkDocs site at https://dagin34.github.io/errium/ is retired; it now serves only a notice
  pointing to the new domain.

## [0.1.1] — 2026-09-03

Documentation-only release. No code changes — published so the updated README renders on the
PyPI project page, which snapshots it per version.

### Changed

- README now carries PyPI, Python version, license, and CI badges, documents the `flask`/`ninja`/
  `drf` extras together, notes the shipped `py.typed` markers, and flags that a server
  (`uvicorn`) must be installed separately since Errium depends on `fastapi`, not
  `fastapi[standard]`.

### Added

- This changelog, published to the docs site at https://dagin34.github.io/errium/changelog/.

## [0.1.0] — 2026-09-03

First public release, [published on PyPI](https://pypi.org/project/errium/).

### Added

- **Core pipeline** (`errium_core`) — framework-agnostic `ClassificationEngine`, the
  `ExceptionClassifier` protocol, `ClassifiedError`/`StandardizedError` contracts,
  `DefaultFormatter`, and `ValidationNormalizer`. Detects framework and SQLAlchemy exception
  types by duck-typing rather than importing them, so the core stays dependency-light.
- **FastAPI adapter** (`errium`) — `ErriumMiddleware` for uncaught and HTTP exceptions, plus
  `validation_exception_handler` for `RequestValidationError` with beautified `details`.
- **Flask adapter** (`errium_flask`) — the `ErriumFlask` extension, covering Werkzeug HTTP
  exceptions, uncaught exceptions, and pydantic validation errors raised inside views.
- **Django Ninja adapter** (`errium_ninja`) — `register_errium(api)`, overriding Ninja's built-in
  handlers for `ValidationError`, `HttpError`, `Http404`, and `Exception`.
- **Django REST Framework adapter** (`errium_drf`) — `errium_exception_handler`, wired through
  `REST_FRAMEWORK["EXCEPTION_HANDLER"]`, with its own `flatten_drf_errors` normalizer.
- **Database classification** — `DatabaseExceptionClassifier` maps SQLAlchemy errors to
  `DATABASE_ERROR`, and uniqueness violations to `DUPLICATE_RESOURCE`, with no hard SQLAlchemy
  dependency.
- **Dev vs. prod sanitization** — `ERRIUM_DEBUG` controls whether 5xx responses are sanitized and
  whether a `debug` block with the stack trace and hints is attached.
- **Typing** — all five packages ship a `py.typed` marker; the source is checked under
  `mypy --strict`.

[Unreleased]: https://github.com/Dagin34/errium/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Dagin34/errium/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Dagin34/errium/releases/tag/v0.1.0
