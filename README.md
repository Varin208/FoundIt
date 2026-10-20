# FoundIt - AUPP Campus Lost & Found

A Lost & Found website for the American University of Phnom Penh.
**Frontend:** plain HTML/CSS/JS. **Backend:** Python Flask + SQLite, with Gemini for AI image matching.

## Project layout

```
FoundIt/
├── frontend/              The website (unchanged design)
│   ├── *.html             login, signup, home, report-lost, report-found,
│   │                      my-reports, potential-match
│   ├── css/styles.css
│   ├── js/api.js          The ONLY file that talks to the server
│   ├── js/app.js          Page helpers (auth guard, header, formatting)
│   └── js/icons.js
├── backend/
│   ├── app.py             Flask server: serves the website AND the /api routes
│   ├── models.py          Database tables (users, reports, matches)
│   ├── auth.py            Register / login / logout
│   ├── reports.py         Save lost/found reports + photos, list my reports
│   ├── uploads/           Saved photos (git-ignored)
│   ├── requirements.txt
│   └── .env.example       Copy to .env and fill in (never commit .env)
└── README.md
```

## Run it

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then edit .env and set SECRET_KEY
python app.py
```

Open **http://localhost:5000** (do not double-click the HTML files any more -
the pages need the server).

## Build progress

| Step | Feature | Status |
|------|---------|--------|
| 1 | Flask + SQLite + register / login / logout | Done |
| 2 | Save lost/found reports and photos; My Reports and Home stats from the database | Done |
| 3 | Gemini image matching | Next |
| 4 | Potential Match page: confirm / deny, update status | |
| 5 | Email notifications with a link to the match page | |

Until its step is done, `getMatch` and `respondToMatch` in `frontend/js/api.js`
(marked **MOCK**) still use the browser's localStorage instead of the server.

## API (so far)

| Method | Endpoint | Body | Result |
|--------|----------|------|--------|
| POST | `/api/auth/signup` | `{name, email, password}` | `{user}` |
| POST | `/api/auth/login` | `{email, password}` | `{user}` |
| POST | `/api/auth/logout` | | `{ok: true}` |
| GET | `/api/auth/me` | | `{user}` or 401 |
| POST | `/api/reports/lost` | form: `itemName, description, location, dateTime, photo?` | `{report}` |
| POST | `/api/reports/found` | form: `photo, location, description?` | `{report}` |
| GET | `/api/reports/mine` | | `{lost: [...], found: [...]}` |
| GET | `/api/photos/<name>` | | the photo (login required) |

## Security notes

- Secrets (`SECRET_KEY`, later `GEMINI_API_KEY` and email password) live only in
  `backend/.env`, which is git-ignored. They are never sent to the browser.
- Passwords are stored as salted hashes. The login cookie is `HttpOnly`.
- Only emails ending in `@aupp.edu.kh` can register (checked on the server).
- Uploaded photos are verified as real images with Pillow, stripped of metadata
  (including GPS location), shrunk, and re-saved as JPEG under random names.
  Only logged-in users can view them.
