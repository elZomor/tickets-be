# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 5.2 backend for a theatrical/entertainment platform managing shows, festivals, performers, and artist profiles. Features AI-powered performer search using OpenAI embeddings and pgvector.

## Development Commands

### Docker-based (production-like)
```bash
docker-compose up -d              # Start all services (admin:8005, redis:6379, celery)
make format                       # Run Black formatter
make lint                         # Run Flake8 linter
make make-migrations              # Create Django migrations
make migrate                      # Apply migrations
docker exec -it admin python manage.py <command>  # Run any Django command
```

### Local development
```bash
python manage.py runserver        # Dev server (uses SQLite)
python manage.py check            # Validate project
python manage.py makemigrations
python manage.py migrate
```

### Code quality
- **Black**: Line length 88, Python 3.12, skips migrations/tests
- **Flake8**: Line length 88, ignores E203/E266/E501/W503
- Pre-commit hooks enforce formatting on commit

## Architecture

### Django Apps
| App | Purpose |
|-----|---------|
| `show` | Shows, festivals, theaters, show dates, reservations, publications |
| `hita` | HITA member profiles, performers, achievements, experiences, galleries |
| `hita_arab_festival` | HITA Arab Festival shows, articles, comments, reservations |
| `hita_evaluation` | Performer evaluation and analytics |
| `ai` | OpenAI embeddings, semantic performer search, text extraction |
| `social_login` | Google OAuth and Clerk authentication |
| `eldorg` | Organizational script management |

### Key Patterns
- **ViewSets**: DRF ViewSets in `<app>/views/` directories
- **Models**: Split into separate files under `<app>/models/` with `__init__.py` exports
- **Authentication**: JWT via simplejwt, social login via Clerk/Google
- **Async tasks**: Celery with Redis broker for email, AI processing
- **Storage**: S3 in production, local filesystem in development
- **AI Search**: pgvector for semantic search on performer embeddings

### Services Stack
- **admin**: Django app (port 8005 externally, 8000 internally)
- **redis**: Message broker and cache (port 6379)
- **celery_worker**: Async task processing

### Database
- **Production**: PostgreSQL with pgvector extension
- **Development**: SQLite (set `ENVIRONMENT=local`)

### Environment
Key variables in `.env`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `ENVIRONMENT` (local/production), database credentials, AWS S3 config, OpenAI API keys, Google/Clerk OAuth credentials.

## Third Side (`third_side` app)

API for the Third Side magazine frontend (`../../third_side_frontend`, see its CLAUDE.md). Mounted at `/third_side/`, no trailing slashes.

- **Own accounts, not `django.contrib.auth.User`**: `ThirdSideUser` (email login, `role` EDITOR/READER) so the app can be lifted into its own project/DB (there it can become `AUTH_USER_MODEL`). Its own JWT realm (`third_side/auth.py`): tokens carry `ts_user_id` + `realm: third_side`; `ThirdSideJWTAuthentication` is set on every third_side view, and the project-wide JWTAuthentication rejects these tokens (and vice versa). Endpoints: `auth/signup|login|refresh|forgot-password|reset-password`, `profile/me`. Migration 0011 copied referenced django Users (same ids, password hashes kept, roles from the old `Profile`). Editors are made in the Django admin (ThirdSideUser). Social login is not available for Third Side accounts.

- Localized reads take `?lang=ar|en|ro` (`third_side/i18n.py`: `localize`, `localize_tree`). Localized taxonomy fields are `{ar,en,ro}` JSON maps; articles have `ArticleTranslation` rows (title/slug/Lexical body synced from Payload by the webhook, excerpt/AI flag set here). Django owns article metadata (category, critic, cover, tags); Payload owns title/slug/body per locale (locales ar, en, ro) and the per-locale `aiGenerated` tick, which the webhook copies to `ArticleTranslation.is_ai_generated` (shown as the AI tag; a doc without the field leaves the flag unchanged).
- Read serializers shaped for the FE: `third_side/read_serializers.py`. Writes still use `serializers.py`.
- Endpoints: `home`, `nav-groups`, `tags`, `categories`, `category-pages/{slug}`, `articles` (filters `category group tag critic featured search`; `by-slug/{slug}`, `{id}/similar`, `{id}/read`), `comments` (`?article=`, `{id}/like`), `ratings` (own only), `reports` (one per reader per target), `critics` (`by-slug/{slug}`), `about`, `ads/pick` + `ads/{id}/impression|click`, `submissions` + `submissions/mine`, `auth/*`, `profile/me`. Schema: `/third_side/schema` (drf-spectacular).
- Reader submissions are `Article`s in `SUBMITTED`; the reader sees pending/published/rejected (`views/SubmissionViews.py`).
- Throttle scopes: `third_side_write`, `third_side_read`, `third_side_submit` (env `THIRD_SIDE_*_RATE`). Tests that post repeatedly should `cache.clear()` in `setUp`.
- Seed from the FE mock JSON: `python manage.py seed_third_side [--mock-dir ../../third_side_frontend/app/lib/mock]`; `tests/test_seed_contract.py` diffs API output against those mocks.
- Tests: `python manage.py test third_side` (set `ENVIRONMENT=local DEBUG=true ALLOWED_HOSTS=localhost SECRET_KEY=... PAYLOAD_CMS_WEBHOOK_SECRET=...`).
- Env: `THIRD_SIDE_FE_URL` (reset links), `CORS_ALLOW_ALL_ORIGINS`/`CORS_EXTRA_ORIGINS`, `SEND_EMAIL`.
