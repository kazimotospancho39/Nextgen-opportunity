# NextGen Opportunity brief: implementation audit

Checked against the complete pasted brief on 12 November 2026. The brief is a product specification and phased roadmap; it is not a claim that all features already exist. This checklist records current implementation and external setup dependencies so future work does not silently skip them.

## Implemented in the current preview

- Original NextGen brand, plus-mark logo, current pink/red diagonal artwork, glass cards, and dark blue accent.
- Public homepage, global opportunity listings and detail pages, events and event detail pages, Community Highlights media gallery, Programs, About, Contact, and the admin content studio.
- Opportunity publishing, category and broad-region search, save-for-later, a single-statement internal application, deadline countdowns, and application status display.
- Event publishing, countdown, capacity-limited registration, and ticket checkout flow.
- Member email/password registration and sign-in, personal hub for saved opportunities, applications, and event registrations.
- Admin upload/selection of photos and videos for homepage, gallery, page copy, opportunities, and events.
- CSRF protection, Werkzeug password hashing for members, safe post-login redirects, file-extension checks for supported media, unique payment references, Flutterwave webhook signature checks, and server-side transaction verification.
- Global opportunities directory with keyword, category, broad region, education level, format, application-fee and deadline filters. This is a partial implementation of the much wider filter specification.
- Member profile fields for name/contact, nationality/residence, education, work background, skills, languages, interests, and goals. Applications now retain a point-in-time JSON snapshot of account contact and profile fields. My Hub shows profile-based keyword recommendations and completion progress.

## Required gaps still open

### Public discovery and content

- Add destination country, applicant-eligible country, funding type/coverage, field of study, age, paid/unpaid and experience filters, plus richer categories/subcategories.
- Extend opportunity records and detail pages with organization/sponsor, source URL, verification status/date, opening date, required documents, procedure, application mode, related listings, and share/report controls. Expired dated listings should be excluded from active search.
- Build dedicated Sponsorships and Funding, Countries and Regions, Learning Centre, Organizations and Announcements, Blog/News, Help/FAQs, and legal/contact/social pages.
- Add the Learning Centre CMS for articles, guides, PDF notes, audio and video, with categories and public/member-only visibility.
- Add organization profiles, verification, announcements and an approval workflow for organization-submitted listings.
- Keep discovery free. Do not imply a payment guarantees selection. Internal application and verified official-source flows need explicit labels. Never link to either reference organization; external official application sources are a separate, listing-specific workflow.

### Events and applications

- Expand event data with organizer, venue/mode, eligibility, application deadline, schedule, speakers, FAQs, funding categories, configurable packages/prices and package-specific availability.
- Add configurable multi-step forms, reusable profile fields, document uploads, review/confirmation, event applications, participant review, scoring/notes/reviewer assignment, decisions, attendance, invitations, certificates and published results.
- Add edit/archive/preview/scheduling/verification tools for opportunities and full edit/archive/package/participant tools for events.
- Status choices now match the requested Submitted, Under review, Shortlisted, Interview, Accepted, Rejected, Waitlisted and Withdrawn lifecycle. Status history, named reviewer roles and member withdrawal controls remain open.

### Member portal

- Add secure private CV/document storage and selection on applications; the current profile snapshot does not store files.
- Add application history snapshots/answers/documents, payment history and downloadable receipts, notification centre and preferences, upcoming deadline/event reminders, profile-based stronger recommendations, account settings/security, email verification, password reset, and optional Google/2FA.
- Add support requests and member-controlled withdrawal where allowed.

### Administration and trust

- Replace the single shared admin-password session with named administrator accounts and role-based access (Super Admin, Content, Applications, Reviewer, Finance, Support and Organization roles). Add admin profile/security controls.
- Add admin user/organization/support management; opportunity editing/deletion/archive/preview/scheduling/source verification; and application filters, scoring, review notes, assignment, exports and bulk notifications.
- Add audit logs for sensitive changes, admin action history, real analytics, reports, and reliable search/pagination.
- Add website settings for branding/contact, localization, currencies, email templates, notification channels, payment configuration, SEO, security, backups, maintenance and legal copy.
- Add rate limiting, data retention/deletion controls, private object storage, upload scanning/strict content validation, error monitoring, and operational backup/restore procedures.

### Payments and production readiness

- The app has a Flutterwave checkout/webhook path and does not collect card numbers. Real payment acceptance is not confirmed until the merchant account, supported currencies, international card acceptance, `FLW_SECRET_KEY`, and webhook secret are configured and verified in the provider dashboard.
- Complete and verify idempotent webhook handling, failed-payment reconciliation, refunds, receipts, gateway-neutral provider interface, currency-aware decimal amounts, revenue/currency/event reports, and payment audit records. Keep demo payments off in production.
- Configure SMTP for email verification/notifications; durable object storage (for example R2/S3) for uploads; PostgreSQL migrations; backup/restore; HTTPS/domain; and monitoring. Render's free filesystem is not durable for user documents/media.
- Add production migrations before changing existing table columns. New profile/snapshot tables use `create_all`; that is not a substitute for a migration system.
- The current code is concentrated in `app.py`; the brief's modular blueprints/services are still a maintainability task.

## Roadmap status

| Phase | Current status | Remaining work |
|---|---|---|
| 1. Foundation | Partial | Named roles, email verification/reset, migrations, security controls, production storage/operations |
| 2. Opportunities | Partial | Extended taxonomy, country/eligibility/funding/field/age/experience filters, verified source data, edit/preview/report |
| 3. User dashboard | Partial | Profile and basic recommendations now exist; private documents, notifications/preferences, payment history/receipts remain |
| 4. Events and applications | Partial | Event registrations exist; configurable packages/forms, review, documents, selection, attendance/certificates remain |
| 5. Payments | Partial | Flutterwave path exists; provider setup, full reconciliation/refunds/receipts, currency handling and production verification remain |
| 6. Administration | Partial | Basic content/admin operations exist; RBAC, user/org controls, audit logs, reporting and full workflows remain |
| 7. Global expansion | Partial | Global listings and broad regions exist; localization, multiple currencies, WhatsApp, SEO and scalable recommendations remain |
| 8. Testing and deployment | Preview deployed; incomplete | Security, payment, mobile and workflow verification; backups and production deployment remain |

## External inputs needed before production

- Approved Flutterwave merchant account and live credentials/webhook secret.
- SMTP sender/provider credentials and verified sending domain.
- Durable private file storage credentials/bucket and retention policy.
- Reviewed opportunity, event, sponsor and organization data with authoritative sources and permission to publish.
- Final legal/privacy/refund policy text and organization contact details.
- Supported countries/currencies and the business's settlement choices.

The public Render URL is a demonstration preview, not a production payment or personal-document service.

