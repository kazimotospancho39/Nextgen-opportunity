# NextGen Opportunities Plus

NextGen Opportunities Plus is an independent global platform for discovering opportunities, applying, registering for events, and tracking next steps. Discover. Connect. Explore. Its original brand, copy, sample listings and graphics are created for this product.

## Features

- Worldwide opportunity discovery: scholarships, fellowships, internships, jobs, grants, leadership camps, training, conferences and exchange programs.
- Keyword, category and region filters, with online and in-person listings.
- Internal member accounts, saved opportunities, application forms, deadline countdowns and progress tracking.
- Member profile with reusable education, experience, skills, language and interest details; profile-based recommendations and a point-in-time profile snapshot for each new application.
- Event calendar, live event countdowns, registration windows, capacity tracking and ticketing.
- Page-specific admin content, opportunity and event publishing, application review stages, contact inbox and newsletter subscribers.
- Admins can optionally attach one or more photos or videos to page content, new opportunities and events; attached media appears on the matching public page and can also be managed in the media library.
- Admin photo and video library with independent homepage and gallery visibility controls. Media files are stored under `static/uploads/media`; uploads are limited to 100 MB per request.
- Secure checkout for Visa and other supported cards in the configured currency. Tanzania mobile money is available when `PAYMENT_CURRENCY=TZS`.

## Run the local review model

Event times and application closing times are entered in UTC for consistent global countdowns. The included `.env` is configured for USD display and demo payments. Demo checkout records a test transaction only; it does not charge a card.

In PowerShell:

```powershell
Set-Location 'C:\Users\kazim\Documents\Codex\2026-11-04\https-youthimpactcamp-org-utm-source-ig\outputs'
& 'C:\Users\kazim\OneDrive\Documents\Opportunity Hub Tanzania\.venv\Scripts\python.exe' app.py
```

Open `http://127.0.0.1:5000`. Admin studio: `http://127.0.0.1:5000/admin`. The admin password is read from the local `.env` file and is intentionally not published. Keep PowerShell open while using the app and press `Ctrl+C` there to stop it.

If required packages are missing, install them in the active environment with `python -m pip install -r requirements.txt`.

## Payments and global availability

`PAYMENT_CURRENCY` controls the amount currency (the review model uses USD). `FLW_SECRET_KEY` and `FLW_WEBHOOK_SECRET_HASH` are required for live checkout and verified payment updates. Set `DEMO_PAYMENTS=false` in a production environment. Add the gateway credentials through secure environment settings, never through the admin content editor.

Visa is a card network; Flutterwave provides the configured checkout and payment processing. Customers can pay with eligible international cards when the Opportunity Hub merchant account is approved for international card acceptance. Their card issuer may apply a currency conversion. Availability depends on merchant-country rules, the issuer and gateway approvals. A TZS setup can also show Tanzania mobile-money options.

The app keeps opportunity browsing, application forms, event registration, accounts and content inside Opportunity Hub. Only the secure payment step may open the payment processor's checkout.

## Content and notifications

Sample opportunities and event information are demonstration content. Replace them with reviewed global listings before launch. Update opt-ins are stored for the team. Emails about newly published opportunities and events are sent only when `SMTP_*` settings are configured.

## Client feedback

Use [CLIENT_REVIEW.md](CLIENT_REVIEW.md) to guide a product review. A running local address is only available on your own computer; use a hosted staging environment to let a client try the app remotely.

