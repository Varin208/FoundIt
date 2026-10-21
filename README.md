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
│   ├── js/api.js          The ONLY file that talks to the server (all calls are real)
│   ├── js/app.js          Page helpers (auth guard, header, formatting)
│   └── js/icons.js
├── backend/
│   ├── app.py             Flask server: serves the website AND the /api routes
│   ├── models.py          Database tables (users, reports, matches)
│   ├── auth.py            Register / login / logout
│   ├── reports.py         Save lost/found reports + photos, list my reports
│   ├── matching.py        Gemini AI matching (runs when a found item is reported)
│   ├── matches.py         View a match, confirm / deny it, update statuses
│   ├── check_gemini.py    Tests your Gemini key and model before you rely on them
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
| 3 | Gemini image matching | Done |
| 4 | Potential Match page: confirm / deny, update status | Done |
| 5 | Email notifications with a link to the match page | Next |

## How the AI matching works

1. Someone submits a **found** item (photo, location, optional notes).
2. In the background, the server sends Gemini that photo plus the open **lost**
   reports from *other* people (newest 20, up to 60 days old) and their photos.
3. Gemini scores each lost report from 0 to 1. Scores at or above
   `MATCH_THRESHOLD` (default 0.6) become a **pending match**, at most 3 per found
   item. Both reports change to **Potential match**.
4. The owner of the lost report sees a **Review match** button in My Reports and
   opens the Potential Match page, where they answer **This is my item** or
   **This isn't my item**.

**What each answer does**

| Answer | Match | Lost report | Found report |
|--------|-------|-------------|--------------|
| This is my item | confirmed | Claimed | Claimed |
| This isn't my item | rejected | back to Searching* | back to Searching* |
| Someone else claimed it first | closed | back to Searching* | stays Claimed |

\* unless another match is still waiting on that report.

When an owner confirms, any other pending matches for the same lost report or
found item are closed, so an item can never be handed to two people.
**Returned** is not set by anything yet.

Matching only runs when a *found* item is submitted. A lost report filed after
the item was already found is not compared automatically (see "Ideas for later").

Progress and each score are printed in the server terminal. If matching seems
to do nothing, check there first, then run `python check_gemini.py`.

Settings in `backend/.env`: `GEMINI_API_KEY`, `GEMINI_MODEL`, `MATCH_THRESHOLD`.

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
| GET | `/api/matches/<id>` | | `{match, lostReport, foundReport}` (owner of the lost report only) |
| POST | `/api/matches/<id>/respond` | `{confirmed: true\|false}` | `{match}` |

## Security notes

- Secrets (`SECRET_KEY`, later `GEMINI_API_KEY` and email password) live only in
  `backend/.env`, which is git-ignored. They are never sent to the browser.
- Passwords are stored as salted hashes. The login cookie is `HttpOnly`.
- Only emails ending in `@aupp.edu.kh` can register (checked on the server).
- A match can only be opened or answered by the owner of the lost report (anyone
  else gets "not found"). The finder's name and email are never sent to the owner.
- `GEMINI_API_KEY` is read only on the server and is never sent to the browser.
- Found-item photos are sent to Google's Gemini API for analysis. Photos can
  contain personal items such as student ID cards, so check Google's Gemini API
  terms for how your plan handles data before using this with real students.
- Uploaded photos are verified as real images with Pillow, stripped of metadata
  (including GPS location), shrunk, and re-saved as JPEG under random names.
  Only logged-in users can view them.

## Ideas for later (not built)

- A way to mark a claimed item as **Returned** once it has been handed over.
- Also compare a **new lost report** against already-reported found items.
- Hand-over verification: matching only suggests; staff should still check that
  the person claiming an item can describe it.
