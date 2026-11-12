# NextGen Opportunity brief: implementation audit

Checked against the complete pasted brief on 12 November 2026. This checklist records features in the local project workspace, open product work and external setup needs. The Render preview can lag local changes until they are published.

## Implemented in the local project workspace

- Original NextGen brand, plus-mark logo, current pink/red diagonal artwork, glass cards, and dark blue accent.
- Public homepage, global opportunity listings and detail pages, events and event detail pages, Community Highlights media gallery, Programs, About, Contact, and the admin content studio.
- Opportunity publishing, category and broad-region search, save-for-later, a single-statement internal application, deadline countdowns, and application status display.
- Event publishing, countdown, capacity-limited registration, and ticket checkout flow.
- Admin event editing for title, dates, location, capacity, ticket price, copy, and attached photos/videos. Start/end input is validated as UTC; reducing capacity below existing registrations is blocked, and registered members receive an in-app update when event details change.
- Member email/password registration and sign-in, personal hub for saved opportunities, applications, and event registrations.
- Admin upload/selection of photos and videos for homepage, gallery, page copy, opportunities, and events.
- Learning Centre with an admin-managed catalogue of original video/audio lessons, articles, practical guides, and learning notes; supports public/member-only access and HTTPS hosted resources.
- CSRF protection, Werkzeug password hashing for members, safe post-login redirects, file-extension checks for supported media, unique payment references, Flutterwave webhook signature checks, and server-side transaction verification.
- Global opportunities directory with keyword, category, broad region, destination and eligible countries, education level, format, funding, study field, age, paid/unpaid, experience, application-fee and deadline filters.
- Opportunity listings support sponsor/source, verification, opening/expiry dates, required documents, funding coverage and application steps. The directory excludes expired dated listings; listing-specific external applications use secure provider URLs.
- Admins can edit opportunity details and archive/restore a listing without deleting its application history.
- Application review includes search and status/opportunity filters, reviewer assignment records, scored internal notes, status-change history and admin-only CSV export.
- Member notification centre with unread counts, read/read-all actions, category preferences, opportunity and event publication alerts, registration/application updates, payment confirmations, and seven-day reminders generated when members open My Hub for saved opportunities and registered events.
- Members can view the status-change history attached to their own applications.
- Member profile fields for name/contact, nationality/residence, education, work background, skills, languages, interests, and goals. Applications now retain a point-in-time JSON snapshot of account contact and profile fields. My Hub shows profile-based keyword recommendations and completion progress.

## Required gaps still open

### Public discovery and content

- Add richer opportunity categories/subcategories, related listings, and share/report controls. The admin editor still needs preview and scheduled publication.
- Build dedicated Sponsorships and Funding, Countries and Regions, Organizations and Announcements, Blog/News, Help/FAQs, and legal/contact/social pages.
- The Learning Centre accepts links to hosted media and notes; private file storage and direct PDF/audio/video uploads remain open pending durable object storage.
- Add organization profiles, verification, announcements and an approval workflow for organization-submitted listings.
- Keep discovery free. Do not imply a payment guarantees selection. Internal application and verified official-source flows need explicit labels. Never link to either reference organization; external official application sources are a separate, listing-specific workflow.

### Events and applications

- Expand event data with organizer, venue/mode, eligibility, application deadline, schedule, speakers, FAQs, funding categories, configurable packages/prices and package-specific availability.
- Add configurable multi-step forms, reusable profile fields, private document uploads, review/confirmation, event applications, participant review, decisions, attendance, invitations, certificates and published results. Opportunity reviewer assignment and scoring are implemented; event-specific selection workflows remain open.
- Add preview and scheduled publication for opportunities; event editing and visibility toggles exist, while event package pricing, explicit archive history, participant management and attendance tools remain open.
- Status choices now match the requested Submitted, Under review, Shortlisted, Interview, Accepted, Rejected, Waitlisted and Withdrawn lifecycle. New status changes are tracked. Named reviewer accounts/roles and member withdrawal controls remain open.

### Member portal

- Add secure private CV/document storage and selection on applications; the current profile snapshot does not store files.
- Add application answers/documents, payment history and downloadable receipts, browser push/email delivery controls for member notification preferences, profile-based stronger recommendations, account settings/security, email verification, password reset, and optional Google/2FA. In-app notifications, category preferences and reminder records are implemented. Submitted account/profile information is already stored as a point-in-time snapshot.
- Add support requests and member-controlled withdrawal where allowed.

### Administration and trust

- Replace the single shared admin-password session with named administrator accounts and role-based access (Super Admin, Content, Applications, Reviewer, Finance, Support and Organization roles). Add admin profile/security controls.
- Add admin user/organization/support management; opportunity preview/scheduling; named reviewer accounts/roles; and bulk application notifications.
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
| 2. Opportunities | Partial | Core global filters and source metadata, edit and archive/restore exist; richer taxonomy, related listings, share/report, preview and scheduling remain |
| 3. User dashboard | Partial | Profile, basic recommendations, application status history and in-app notifications/preferences/reminders exist; private documents and payment history/receipts remain |
| 4. Events and applications | Partial | Opportunity review now has assignments, scores, internal notes, status history and CSV export; event applications, configurable forms, private documents, selection, attendance/certificates remain |
| 5. Payments | Partial | Flutterwave path exists; provider setup, full reconciliation/refunds/receipts, currency handling and production verification remain |
| 6. Administration | Partial | Basic content/admin operations exist; RBAC, user/org controls, audit logs, reporting and full workflows remain |
| 7. Global expansion | Partial | Global listings, broad regions, and a Learning Centre exist; localization, multiple currencies, WhatsApp, SEO and scalable recommendations remain |
| 8. Testing and deployment | Preview deployed; incomplete | Security, payment, mobile and workflow verification; backups and production deployment remain |

## External inputs needed before production

- Approved Flutterwave merchant account and live credentials/webhook secret.
- SMTP sender/provider credentials and verified sending domain.
- Durable private file storage credentials/bucket and retention policy.
- Reviewed opportunity, event, sponsor and organization data with authoritative sources and permission to publish.
- Final legal/privacy/refund policy text and organization contact details.
- Supported countries/currencies and the business's settlement choices.

The public Render URL is a demonstration preview, not a production payment or personal-document service.

