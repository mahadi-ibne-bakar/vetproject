# VetProject

Online veterinary consultation platform for Bangladesh. Pet owners can book video consultations with certified vets, pay via bKash, and receive prescriptions — all without leaving home.

**Live:** https://vetproject-avel.onrender.com

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [User Roles](#user-roles)
- [Booking Flow](#booking-flow)
- [Payment Flow](#payment-flow)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Demo Credentials](#demo-credentials)
- [Deployment](#deployment)
- [Architecture Decisions](#architecture-decisions)

---

## Overview

VetProject is a full-stack Django web application built specifically for the Bangladeshi market. It handles the complete lifecycle of an online vet consultation: scheduling, bKash payment verification, Google Meet video calls, prescription generation as PDF, and post-consultation reviews.

The platform is designed around three constraints specific to Bangladesh:
- **Mobile-first** — most users are on Android with slow connections; WOFF2 fonts, lazy loading, and PWA support are built in
- **bKash payments** — no payment gateway; admins manually verify bKash SMS confirmations
- **Trust-building** — a two-payment model (booking fee upfront, consultation fee after the session) reduces risk for first-time users

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1 |
| Database | Supabase PostgreSQL (via psycopg2) |
| File Storage | Supabase S3-compatible storage (via django-storages) |
| Frontend | Django templates + vanilla JS + Material Design 3 |
| CSS | Custom design system with CSS variables (no Tailwind at runtime) |
| Fonts | Self-hosted Nunito (WOFF2 + TTF fallback), Material Symbols |
| Hosting | Render (web service) |
| CI/CD | GitHub Actions |
| Error Monitoring | Sentry |
| PDF Generation | ReportLab |
| Image Processing | Pillow |
| Caching | Django database cache (`django_cache` table) |
| Task Scheduling | cron-job.org hitting `/cron/send-reminders/` |
| PWA | Service worker + Web App Manifest |

---

## Features

### For Pet Owners
- Register and manage a profile with multiple pets (cat, dog, bird, rabbit, livestock, other)
- Browse and filter certified vets by availability and specialty
- Book consultation slots (two entry points: vet profile → pick date, or pick time → pick vet)
- Pay booking fee via bKash, receive Google Meet link on confirmation
- Attend video consultation, pay consultation fee afterward
- Download PDF prescription
- Submit star ratings and written reviews
- View full appointment history with status tracking

### For Vets
- Apply for platform registration (admin-approved)
- Set recurring weekly availability or one-off date-specific windows
- Block specific dates
- View upcoming and past appointments
- Write and publish blog posts (admin-moderated)
- Manage their public profile (bio, education, BVC registration, photo)

### For Admins
- Full dashboard with analytics (consultations per day, revenue, species breakdown, top vets)
- bKash SMS verification tool — paste the SMS, system extracts amount + TrxID + phone and auto-matches
- One-tap manual payment verification with confirmation modal
- Vet application review (approve / reject with reason)
- User management (ban / unban, promote to admin)
- Google Meet link pool — add links, system auto-assigns them to confirmed appointments
- Coupon code system (percentage or flat discount, per-user limits, expiry dates, usage analytics)
- Sitewide discount toggle with optional expiry
- Blog moderation (approve / reject with feedback note)
- Review moderation (show / hide)
- Refund tracking
- Audit log — every significant admin action recorded with actor, timestamp, and IP
- Email verification toggle (on/off without redeploying)
- Site settings: booking fee, cancellation deduction, slot duration, bKash merchant number, service on/off message

### Platform
- Dark mode with localStorage persistence and anti-flash script
- PWA: installable on Android home screen, offline fallback page
- Content Security Policy (nonce-based, report-only mode — enforcing after Phase 7 template refactor)
- Security headers: HSTS, X-Frame-Options, XSS filter, secure cookies (production only)
- Rate limiting on login and payment submission
- N+1 query fixes with `select_related` / `prefetch_related` throughout
- Slot generation caching with per-vet cache invalidation
- Dynamic sitemap at `/sitemap.xml`
- `robots.txt` and `/.well-known/security.txt`
- Custom branded 404 and 500 error pages

---

## Project Structure

```
vetproject/
├── accounts/               # Auth, user model, vet application flow
│   ├── models.py           # Custom User (AbstractUser + role, is_banned, email_verified)
│   ├── decorators.py       # @login_required_user/vet/admin
│   ├── middleware.py       # Ban check middleware
│   ├── verification.py     # Email verification tokens (Django signing framework)
│   └── views.py
│
├── consultations/          # Core booking and consultation logic
│   ├── models.py           # Pet, VetAvailability, Appointment, Payment,
│   │                       # Prescription, AppointmentPhoto, CouponCode, CouponUsage
│   ├── slots.py            # Slot generation from availability windows
│   ├── slot_cache.py       # get_slots_cached(), invalidate_vet_slots()
│   ├── pricing.py          # get_effective_price(), validate_coupon()
│   ├── emails.py           # Transactional email senders
│   ├── pdf.py              # ReportLab prescription PDF generation
│   └── templatetags/
│       └── species_tags.py # species_emoji, has_sitewide_discount,
│                           # calc_discounted_fee, url_replace, etc.
│
├── blog/                   # Blog posts and reviews
│   └── models.py           # BlogPost (status workflow, category, reading_time property)
│                           # Review (rating, comment, is_visible)
│
├── core/                   # Shared utilities and platform config
│   ├── models.py           # SiteSettings (singleton), MeetLink, AuditLog
│   ├── middleware.py       # CSP middleware (nonce-based)
│   ├── context_processors.py  # csp_nonce → available in all templates
│   ├── utils.py            # log_action(), get_client_ip()
│   ├── ratelimit.py        # Simple DB-backed rate limiting
│   ├── sitemaps.py         # Dynamic sitemap
│   └── views.py            # Cron endpoint, offline page, service worker, CSP report
│
├── vetproject/
│   ├── admin_views.py      # All admin dashboard views (~1600 lines, split pending)
│   ├── admin_urls.py       # Admin URL configuration
│   └── settings.py
│
├── static/
│   ├── css/fonts.css       # @font-face declarations (WOFF2 + TTF, font-display: swap)
│   ├── fonts/              # Self-hosted Nunito (6 weights) + Material Symbols
│   ├── img/                # favicon.svg, PWA icons (192px, 512px)
│   └── manifest.json       # PWA manifest
│
└── templates/
    ├── base.html           # Main layout (dark mode, CSP nonce, PWA registration)
    ├── dashboard/          # Admin templates
    ├── vet/                # Vet dashboard templates
    ├── user/               # Pet owner templates
    └── public/             # Public-facing pages
```

---

## User Roles

| Role | Access |
|---|---|
| `user` | Book consultations, manage pets, submit payments, view prescriptions, write reviews |
| `vet` | Manage availability, view appointments, write prescriptions, publish blog posts |
| `admin` | Full dashboard access, payment verification, user/vet management, site settings |

Role is stored on the `User` model. Vets also have a `VetProfile` with application status (`pending` → `approved` / `rejected`).

---

## Booking Flow

```
1. Pet owner browses vet list or "book by time" page
2. Selects a vet → picks an available date → picks a time slot (AJAX)
3. Selects (or adds) a pet for the consultation
4. Optionally applies a coupon code (AJAX validation)
5. Sees booking summary with final fee breakdown
6. Submits bKash payment details (TrxID + phone number)
7. Admin verifies payment (SMS paste tool or manual one-tap)
8. On verification: appointment confirmed, Google Meet link assigned, confirmation email sent
9. Vet conducts consultation via Google Meet
10. Pet owner submits consultation fee via bKash
11. Admin verifies second payment → appointment marked completed
12. Vet writes prescription → PDF available for download
13. Pet owner submits review (optional)
```

---

## Payment Flow

VetProject uses a **two-payment model** with manual bKash verification:

| Payment | Amount | Timing |
|---|---|---|
| Booking fee | ৳50 (configurable) | At booking — confirms the slot |
| Consultation fee | Vet rate (with any discount/coupon applied) | After the consultation session |

**Admin verification options:**
- **SMS paste tool** — admin pastes the full bKash confirmation SMS; system uses regex to extract amount, phone, and TrxID and auto-matches against pending payments
- **Quick verify** — one-tap manual confirmation from the payment list

On booking payment verification: appointment status → `confirmed`, Google Meet link auto-assigned from pool, confirmation email sent to owner and vet.

On consultation payment verification: appointment status → `completed`, prescription-ready email sent.

---

## Local Development

**Requirements:** Python 3.12+, uv

```bash
# Clone
git clone https://github.com/mahadi-ibne-bakar/vetproject.git
cd vetproject

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Run migrations
python manage.py migrate

# Create demo data (vets, owners, pets, appointments, blog posts)
python manage.py create_demo_data

# Collect static files
python manage.py collectstatic --noinput

# Start development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres

# Email (Gmail SMTP)
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=VetProject <your-gmail@gmail.com>
EMAIL_TIMEOUT=10

# Supabase Storage
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_BUCKET=vetproject-media
SUPABASE_S3_ACCESS_KEY=your-access-key
SUPABASE_S3_SECRET_KEY=your-secret-key

# Cron job secret (for /cron/send-reminders/?secret=...)
REMINDER_SECRET=your-random-secret

# Logging
DJANGO_LOG_LEVEL=INFO

# Error monitoring
SENTRY_DSN=https://your-dsn@sentry.io/project

# Content Security Policy
# True = report-only (safe for development and initial production)
# False = enforcing (switch after Phase 7 template refactor)
CSP_REPORT_ONLY=True
```

For **local development** with local file storage instead of Supabase, you can omit the Supabase variables — Django will fall back to local `MEDIA_ROOT`.

---

## Running Tests

```bash
# Run all tests
python manage.py test --settings=vetproject.settings_test

# Run specific app
python manage.py test accounts --settings=vetproject.settings_test
python manage.py test consultations --settings=vetproject.settings_test
python manage.py test core --settings=vetproject.settings_test
```

Test settings (`vetproject/settings_test.py`) use SQLite in-memory and disable Supabase storage so no external services are needed.

The test suite covers: registration and login flows, role-based access control, booking slot generation, payment submission, coupon validation, and core public pages.

---

## Demo Credentials

After running `python manage.py create_demo_data`:

| Role | Email | Password |
|---|---|---|
| Admin | admin@vetproject.com | admin1234 |
| Vet | vet1@vetproject.com | vet1234 |
| Vet | vet2@vetproject.com | vet1234 |
| Pet Owner | user1@demo.com | user1234 |
| Pet Owner | user2@demo.com | user1234 |

Demo data includes 4 approved vets, 6 pet owners with pets (cat, dog, bird, rabbit), 10 completed consultations, 3 blog posts, site settings, and Google Meet links.

---

## Deployment

The project deploys to **Render** via `render.yaml`.

**Build command** (`build.sh`):
```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

**Start command:**
```bash
gunicorn vetproject.wsgi:application
```

**CI/CD:** GitHub Actions runs the test suite on every push to `main`. Render deploys automatically on passing tests.

**Scheduled tasks:** cron-job.org pings `/cron/send-reminders/?secret=REMINDER_SECRET` every 5 minutes. This handles:
- 30-minute appointment reminder emails
- Auto-cancel appointments unpaid after 1 hour
- Auto-assign Google Meet links to confirmed appointments without one

---

## Architecture Decisions

**Why Django templates instead of React?**
The application is primarily request-response. The interactive parts (slot picker, coupon validation, quick view panels) are small enough for vanilla JS with fetch(). A React rewrite would add build complexity with minimal UX benefit at current scale. This will be reconsidered if real-time features (in-app notifications, live status updates) are added.

**Why manual bKash verification instead of a payment gateway?**
bKash's merchant API requires a registered business entity and a non-trivial integration process. Manual verification via SMS paste is faster to ship, works reliably, and is the standard practice for small Bangladeshi platforms. The SMS regex parser makes it nearly as fast as an automated system for low-to-medium transaction volumes.

**Why two payments?**
Pet owners in Bangladesh are cautious about paying upfront for a service they haven't experienced. A small ৳50 booking fee confirms commitment while keeping the barrier low. The consultation fee after the session builds trust and reduces refund requests.

**Why Supabase for both DB and storage?**
Single vendor simplifies operations. Supabase's free tier is generous enough for an MVP. PostgreSQL on Supabase is standard Django-compatible — migrating to another host later is straightforward.

**Why self-hosted fonts?**
Google Fonts requires a network request to a third-party CDN, adds a render-blocking resource, and introduces a CSP `connect-src` exception. Self-hosting WOFF2 files via Whitenoise eliminates all three issues and works better in low-connectivity environments.

---

## Roadmap

- [ ] Phase 7 — Template include refactor (extract vet card, appointment card, review card into `{% include %}` partials; migrate `onclick=` to `addEventListener` to enable CSP enforcing mode)
- [ ] Phase 9 — In-app notification system (notification model, bell in navbar, key event triggers)
- [ ] Custom domain + Resend email (currently using Gmail SMTP)
- [ ] CSP enforcing mode (blocked on Phase 7)
- [ ] Load testing with Locust before public launch

---

## License

MIT
