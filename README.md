# FoundIt — AUPP Campus Lost & Found (Frontend)

A static frontend for FoundIt, the lost & found system for the American
University of Phnom Penh. No build step — open `index.html` (or any page)
directly, or serve the folder with any static file server.

**Try it:** demo account `sophea.chan@aupp.edu.kh` / `foundit123` is
pre-seeded, along with a few sample reports and one pending match, so the
whole flow is explorable immediately.

## Structure

```
foundit/
├── index.html            Entry point → redirects to home.html or login.html
├── login.html
├── signup.html
├── home.html              "I Lost Something" / "I Found Something"
├── report-lost.html       Full lost-item form (photo optional)
├── report-found.html      Short found-item form (photo required)
├── my-reports.html        List of the user's reports + status
├── potential-match.html   Reached via an emailed link: ?id=<matchId>
├── css/
│   └── styles.css         All design tokens + component styles
├── js/
│   ├── api.js             Data layer — see "Connecting Flask" below
│   ├── app.js              Auth guard, header wiring, formatting helpers
│   └── icons.js            Inline SVG icon set (no icon-font dependency)
└── assets/
    ├── logo-icon.svg       FoundIt mark, recreated as scalable stroke SVG
    ├── favicon.png / favicon-32.png / apple-touch-icon.png
```

Each HTML page repeats the same header/footer markup rather than pulling in
a shared partial, since there's no templating engine yet. Every copy is
wrapped in an HTML comment:

```html
<!-- ==== Shared site header (extract to templates/_header.html when moving to Flask/Jinja) ==== -->
```

When you set up Flask + Jinja, pull that block out into
`templates/_header.html` / `_footer.html` and `{% include %}` it from a
`base.html` layout — the markup won't need to change, just where it lives.

## Connecting the Flask backend

All data access goes through `js/api.js`. Right now every function reads and
writes `localStorage` as a stand-in database, but each one is already
`async` and returns data shaped like the intended JSON response, with the
target endpoint noted in a comment, e.g.:

```js
async function login({ email, password }) {
  // Future: return fetch('/api/auth/login', { method: 'POST', body: JSON.stringify({email, password}) }).then(r => r.json());
  ...
}
```

To connect the real backend, replace each function body with the
commented-out `fetch()` call (or your preferred HTTP client) and keep the
return shape the same — none of the page-level code needs to change.

Planned endpoints:

| Method | Endpoint                    | Used by                      |
|--------|------------------------------|-------------------------------|
| POST   | `/api/auth/signup`           | signup.html                   |
| POST   | `/api/auth/login`             | login.html                    |
| POST   | `/api/auth/logout`            | header logout button          |
| GET    | `/api/auth/me`                 | auth guard on every page      |
| POST   | `/api/reports/lost`            | report-lost.html              |
| POST   | `/api/reports/found`           | report-found.html             |
| GET    | `/api/reports/mine`            | home.html, my-reports.html    |
| GET    | `/api/matches/:id`             | potential-match.html          |
| POST   | `/api/matches/:id/respond`     | potential-match.html          |

### Photo uploads & AI matching

Photos are currently read client-side into base64 data URLs
(`readFileAsDataUrl()` in `app.js`) and stored inline for the demo. When the
backend exists, switch the two report forms to send `multipart/form-data`
instead, and the AI image-matching step can run server-side right after a
found-item photo is uploaded — comparing it against open lost reports and
creating rows in whatever table backs `/api/matches`.

### Email notifications

`potential-match.html` is built to be reached cold, straight from an emailed
link (`potential-match.html?id=<matchId>`) rather than through the nav. If
the person isn't logged in yet, `requireAuth()` in `app.js` remembers the
page they were headed to and sends them back to it right after they log in.
Wire the actual email send-out into whatever server-side job creates a
match record.

### Auth

Signup/login currently restrict to addresses ending in `@aupp.edu.kh`
(see `AUPP_EMAIL_DOMAIN` in `api.js`). Password hashing shown client-side is
a placeholder only — real hashing (e.g. bcrypt/argon2) must happen
server-side once Flask is in place.

## Status vocabulary

Used consistently across My Reports and the match page:

- **Searching** — report is open, no match yet
- **Potential match** — the system (or AI matching) found a candidate; needs the person's review
- **Claimed** — confirmed match, pending pickup/return
- **Returned** — item is back with its owner
