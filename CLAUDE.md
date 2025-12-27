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
