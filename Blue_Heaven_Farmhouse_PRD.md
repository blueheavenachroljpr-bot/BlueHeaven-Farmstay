# Product Requirements Document
## Blue Heaven Farmhouse — Booking Website

**Owner:** Jai (Founder)
**Status:** Draft v1.0
**Last updated:** July 22, 2026

---

## 1. Overview

Blue Heaven Farmhouse is a private farmhouse property near Jaipur, rented out for day outings, overnight stays, and celebrations. A single-file marketing website already exists (HTML/Tailwind, fully responsive, with hero, about, amenities, gallery, packages, testimonials, and a contact section). This PRD covers turning that static frontend into a working booking system: a real reservation flow, an owner-facing view of incoming bookings, and reliable hosting.

## 2. Problem Statement

The current site looks complete but functionally does nothing — the booking form shows a fake confirmation and no data is saved or sent anywhere. Guests have no reliable way to actually reserve a date, and Jai has no way to see or manage requests except by phone. There's also no protection against two guests being confirmed for overlapping dates.

## 3. Goals

- Let a guest submit a real booking request tied to specific dates, a package, and guest count.
- Guarantee Jai is notified (email, and ideally WhatsApp) within minutes of a new request, not just "within 4 hours" by luck.
- Prevent double-bookings for the same date range.
- Give Jai a simple way to see, confirm, or reject incoming requests without needing a phone call first.
- Keep the existing visual design and content untouched — this is a backend/functionality layer, not a redesign.

## 4. Non-Goals (out of scope for v1)

- Online payment collection (flagged as a fast-follow, not required for launch).
- Multi-property / multi-listing support — this is a single-property site.
- Guest login accounts or booking history for guests.
- Dynamic pricing or seasonal rate changes (fixed package prices for now).

## 5. Target Users

| User | Need |
|---|---|
| Prospective guest (family/couple booking a day trip or overnight stay) | See the property, pick a package, submit a request confidently, get confirmation |
| Corporate/event organizer (birthdays, small weddings) | Enquire about the "Celebration" package with custom requirements |
| Jai (owner) | See new requests instantly, avoid double-booking, confirm/reject quickly |

## 6. Functional Requirements

### 6.1 Marketing site (already built)
- Hero, about, amenities, gallery, video, packages, testimonial, contact/map, footer.
- **Fix required:** replace gallery/hero image URLs (currently pointing to a third-party CDN with expiring auth-key parameters) with permanently hosted images (Cloudinary, S3, or served from the app's own `/public` folder).
- **Fix required:** WhatsApp button currently links to `#` — must point to a real `wa.me` link.

### 6.2 Booking flow
- Guest fills the existing form: name, email, phone, check-in, check-out, guest count, package, special requests.
- On submit, the frontend calls a real backend API instead of only showing a toast.
- Backend validates:
  - Check-out is after check-in.
  - Guest count is within a sane range (configurable, e.g. 1–50 depending on package).
  - Requested date range does not overlap an existing **confirmed** booking.
- On success: booking is stored, guest sees a real confirmation message, Jai receives a notification.
- On conflict (dates unavailable): guest sees a clear message and is prompted to pick different dates or contact directly.

### 6.3 Availability logic
- A booking has a status: `pending`, `confirmed`, `cancelled`.
- Only `confirmed` bookings block a date range; `pending` requests do not auto-block (since Jai still needs to approve), but should be visibly flagged to Jai so two pending requests for the same dates aren't both confirmed by mistake.

### 6.4 Owner notifications
- Email (via Resend or SendGrid) sent to Jai immediately on every new booking request, containing all submitted details.
- *Fast-follow:* WhatsApp Cloud API notification for faster response on mobile.

### 6.5 Admin view
- A lightweight, password-protected page (or authenticated API) listing all bookings: guest info, dates, package, status.
- Ability to change a booking's status to `confirmed` or `cancelled`.
- No need for a polished dashboard in v1 — a clean table is sufficient.

### 6.6 Enquiry handling (Celebration / custom package)
- The "Celebration" and "Custom / Wedding enquiry" package options should route to the same booking table but flagged for manual follow-up rather than instant confirmation, since these require a phone conversation.

## 7. Non-Functional Requirements

- **Reliability:** booking submissions must not silently fail — show the guest a clear success or error state.
- **Performance:** page should remain fast on mobile (most guests will book from a phone); keep image sizes optimized.
- **Security:** admin view must be authenticated; booking API should have basic rate-limiting to prevent spam submissions.
- **Mobile responsiveness:** already handled by the existing Tailwind layout — must be preserved.

## 8. Proposed Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Existing HTML/Tailwind (unchanged), form wired to real API calls | Already built, no need to rewrite |
| Backend | FastAPI | Fast to scaffold, Jai already has FastAPI experience |
| Database | SQLite for MVP → Postgres (Supabase/Neon) once live | Zero setup to start, easy migration path |
| Email notifications | Resend or SendGrid | Simple API, generous free tier |
| Image hosting | Cloudinary or backend-served `/public` folder | Removes dependency on expiring third-party CDN links |
| Hosting | Backend: Render/Railway. Frontend: same backend (static files) or Vercel | Free/cheap tiers, simple deploys |
| Domain | Existing/new domain via Cloudflare DNS | — |

## 9. Data Model (v1)

**Booking**
| Field | Type | Notes |
|---|---|---|
| id | int, PK | |
| first_name, last_name | string | |
| email | string | |
| phone | string | |
| check_in | date | |
| check_out | date | |
| guests | int | |
| package | enum (day_outing, overnight, celebration, custom) | |
| special_requests | text, nullable | |
| status | enum (pending, confirmed, cancelled) | default: pending |
| created_at | datetime | |

## 10. Key User Flows

**Guest books a stay**
1. Guest browses site → selects package → fills booking form → submits.
2. Backend checks date availability.
3. If available: booking saved as `pending`, guest sees confirmation, Jai gets emailed.
4. If unavailable: guest sees conflict message.

**Jai confirms a booking**
1. Jai opens admin page, sees pending request.
2. Calls/messages guest to confirm details (per current 4-hour promise).
3. Marks booking `confirmed` in admin view → date range now blocked for future requests.

## 11. Success Metrics

- % of booking form submissions that result in a real, storable booking (target: 100%, i.e. zero silent failures).
- Time from guest submission to owner notification (target: under 2 minutes).
- Zero double-bookings for confirmed dates.

## 12. Risks / Open Questions

- **Payments:** should guests pay an advance to confirm, or is pay-on-arrival acceptable long-term? Affects whether Razorpay/UPI integration becomes a v1 requirement.
- **Image hosting:** current images are hosted on a third-party CDN with auth-key URLs — confirm these are temporary and migrate before relying on this site for real bookings.
- **Volume:** if booking volume grows significantly, SQLite should be migrated to Postgres sooner rather than later.

## 13. Milestones

| Phase | Deliverable |
|---|---|
| 1 | Backend scaffolded, booking endpoint working locally |
| 2 | Form wired to backend, availability checks working |
| 3 | Owner email notifications working |
| 4 | Admin view live, images migrated off temporary CDN |
| 5 | Deployed to production domain |
| 6 (fast-follow) | Payment integration, WhatsApp notifications, SEO/analytics |
