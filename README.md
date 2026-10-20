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
| 2 | Save lost/found reports and photos | Next |
| 3 | My Reports + Home stats from the database | |
| 4 | Gemini image matching | |
| 5 | Confirm / deny a match, then email notifications | |

Until its step is done, a function in `frontend/js/api.js` marked **MOCK**
still uses the browser's localStorage instead of the server.

## API (so far)

| Method | Endpoint | Body | Result |
|--------|----------|------|--------|
| POST | `/api/auth/signup` | `{name, email, password}` | `{user}` |
| POST | `/api/auth/login` | `{email, password}` | `{user}` |
| POST | `/api/auth/logout` | | `{ok: true}` |
| GET | `/api/auth/me` | | `{user}` or 401 |

## Security notes

- Secrets (`SECRET_KEY`, later `GEMINI_API_KEY` and email password) live only in
  `backend/.env`, which is git-ignored. They are never sent to the browser.
- Passwords are stored as salted hashes. The login cookie is `HttpOnly`.
- Only emails ending in `@aupp.edu.kh` can register (checked on the server).
