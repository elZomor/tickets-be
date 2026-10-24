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
- **Terms & Conditions**: `TermsVersion` (version, effective_date, is_published, `content` JSON of `{title, sections:[{heading, paragraphs, bullets}]}` as ar/en/ro maps). Current = latest published with `effective_date <= today`. Published versions are read-only in the admin: publish a new version instead. `GET terms|terms/versions|terms/{version}` are public (`?lang=`), meant for signup and any future social-login client. `auth/signup` requires `accepted_terms_version` == current version once one is in force (stale = 400 field error) and writes a `TermsAcceptance`. Seeded from the FE `mock/terms.json`.

- Localized reads take `?lang=ar|en|ro` (`third_side/i18n.py`: `localize`, `localize_tree`). Localized taxonomy fields are `{ar,en,ro}` JSON maps; articles have `ArticleTranslation` rows (title/slug/Lexical body per locale, written by the admin editor through `POST/PATCH /articles` with a `doc`, then read back with `GET /articles/{id}/doc`; excerpt is set here). Django owns all article data: metadata (category, critic, cover, tags, status, `via_website`) and the per-locale text (locales ar, en, ro). `doc.isOriginalLanguage` (the ticked locale becomes `Article.original_language`; none/absent leaves it unchanged) and `doc.aiGenerated` (copied to `ArticleTranslation.is_ai_generated`, shown as the AI tag; absent leaves the flag unchanged) are handled by `services/translations.sync_translations`. Editors upload article images to `POST /media`.
- Read serializers shaped for the FE: `third_side/read_serializers.py`. Writes still use `serializers.py`.
- Endpoints: `home`, `nav-groups`, `tags`, `categories`, `category-pages/{slug}`, `articles` (filters `category group tag critic featured search`; `by-slug/{slug}`, `{id}/similar`, `{id}/read`), `comments` (`?article=`, `{id}/like`), `ratings` (own only), `reports` (one per reader per target), `critics` (`by-slug/{slug}`), `festivals` (`by-slug/{slug}`), `festival-posts` (`?festival=<id>`, newest first; read-only, content via Django admin), `about`, `terms` (+ `terms/versions`, `terms/{version}`), `ads/pick` + `ads/{id}/impression|click`, `submissions` + `submissions/mine`, `auth/*`, `profile/me`. Schema: `/third_side/schema` (drf-spectacular).
- Site content editor writes (admin panel): `nav-groups` + `categories` CRUD with `{id}/doc` (all locales; `site_serializers.py`), `about/doc` GET/PUT, `footer` GET/PUT (SiteSettings contact/social/sponsors; hero untouched). Images stored by key (`services/media_urls`).
- Readers upload images too: `POST media` (not in the activity log), attached via `submissions` `images` (`Article.submitted_media`, appended as upload nodes to the editor doc until first saved); avatar `profile/me/avatar` POST/DELETE (a writer without a photo shows it).
- Reader submissions are `Article`s in `SUBMITTED`; the reader sees pending/published/rejected (`views/SubmissionViews.py`).
- Email (`emails` GET/POST, editors only; `views/EmailViews.py`, `services/mail.py`, model `OutgoingEmail`): an editor sends from their own account email, which must be on `THIRD_SIDE_MAIL_DOMAIN` (third-side.org, authenticated in Brevo), via Brevo's HTTPS API (`BREVO_API_KEY`); never SMTP, Railway Hobby blocks it. `test: true` sends to the editor only and is not stored. Every email gets the editor's signature (`ThirdSideUser.signature` JSON: name/title `{ar,en}`, phone, show_photo/show_social; avatar + footer social links; `rtl` picks ar, `ltr` en) unless `signature: false`; edited at `profile/me/signature` GET/PUT; `emails/preview` returns the full rendered email without sending. `audience=subscribers` is reserved (400 until consent + unsubscribe exist). Password-reset mail also goes through Brevo, from `THIRD_SIDE_SYSTEM_SENDER`. Inbound mail is Cloudflare Email Routing to Gmail, outside this app.
- Throttle scopes: `third_side_write`, `third_side_read`, `third_side_submit` (env `THIRD_SIDE_*_RATE`). Tests that post repeatedly should `cache.clear()` in `setUp`.
- Email verification (`services/account_mail.py`, `views/AuthViews.py`): signup (takes `lang`, stored as `ThirdSideUser.language`) sends a confirm mail from `THIRD_SIDE_SYSTEM_SENDER` (`noreply@third-side.org`); link `/{lang}/{verify segment}?uid&token` where token = `django.core.signing` of uid+email, 3 days. `POST auth/verify-email {uid, token}` (public, POST so mail scanners can't verify) sets `email_verified` and sends the welcome mail once; `POST auth/resend-verification` (signed in, scope `third_side_verify_resend`, 5/hour). Unverified readers get 403 `{code: email_not_verified}` on `POST submissions`, `POST media`, avatar POST/DELETE and on changing `bio` (permission `EmailVerified`; staff = superuser or any group are exempt via `can_contribute`). Migration 0031 marked every pre-existing account verified. Profile: `PATCH profile/me` edits name, `date_of_birth` (13-120y), `gender`, `governorate` (27 Egyptian slugs + `outside_egypt`), `bio` (500), `newsletter_opt_in`; GET returns them plus `email_verified`, `language`. FE segments are duplicated in `account_mail.py`.
- Reports/moderation (`views/ReportViews.py`, `models/ModerationAction.py`, `services/moderation_mail.py`): `POST reports {content_type, object_id, reason: spam|abuse_hate|misinformation|copyright|other, note?}` needs a verified email (403 `email_not_verified`); repeat = 200 no-op; 5 reports auto-hide the target. Moderators (`view_report`/`change_report`) list with `?reviewed=&content_type=&reason=`; `GET reports/{id}/warning-template` (author's language), `POST reports/{id}/resolve {action: dismiss|hide|warn|delete|suspend, note, hide_content, send_email, email_subject, email_body, notify_reporters}` settles every open report on the target, logs a `ModerationAction` (strikes = warn/delete/suspend per author) + ActivityLog, emails the author (optional) and thanks reporters. Delete = hard delete for comments, hide only for articles; suspend needs `suspend_user` and never hits staff. Mail failure never undoes the decision (`email_sent` in the response). `PATCH reports/{id}/review` = dismiss alias.
- Notifications / saved / follows (`models/Notification|PushSubscription|NotificationPreference|SavedArticle|Follow.py`, `services/notify.py|push.py|publishing.py`, `tasks.py`, `views/NotificationViews.py|LibraryViews.py`): signals (`signals.py`) queue Celery tasks after commit (`notify.enqueue`; `THIRD_SIDE_NOTIFY_EAGER=1` runs them inline, used by tests). Types: `article_status` (author; not DRAFT/SUBMITTED), `profile_updated` (from `profile/me` PATCH + avatar), `report_reviewed` (reporter), `content_reported` (author, reporter never named), `article_comment` / `article_rating` (author, coalesced into one unread row with `count`), `new_article` (followers of critic / category / nav group), `new_festival_post` (festival followers). Rows hold type+params only (`params.paths` = article/festival URL per locale); copy is rendered by the FE inbox and by `services/push.py` (user's `language`). Endpoints: `notifications` (`?unread=1`, `unread-count`, `{id}/read`, `read-all`, DELETE), `notification-preferences` (gate push only), `push/subscriptions` POST/DELETE (browser `toJSON()` shape), `saved-articles` (+`ids`, PUT/DELETE `{article_id}`), `follows` (`?lang=`) + PUT/DELETE `follows/{critic|category|navgroup|festival}/{id}`. Push needs `THIRD_SIDE_SEND_PUSH=1`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, and a running celery worker + beat (beat: `promote_scheduled_articles` every minute replaces the old lazy `.update()`, `purge_notifications` daily keeps read rows 90 days).
- Seed from the FE mock JSON: `python manage.py seed_third_side [--mock-dir ../../third_side_frontend/app/lib/mock]`; `tests/test_seed_contract.py` diffs API output against those mocks.
- Tests: `python manage.py test third_side` (set `ENVIRONMENT=local DEBUG=true ALLOWED_HOSTS=localhost SECRET_KEY=...`).
- Env: `THIRD_SIDE_FE_URL` (reset links), `CORS_ALLOW_ALL_ORIGINS`/`CORS_EXTRA_ORIGINS`, `THIRD_SIDE_SEND_EMAIL` (password-reset mail; the global `SEND_EMAIL` belongs to the festival apps), `BREVO_API_KEY`.
