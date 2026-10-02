/**
 * api.js — FoundIt data layer
 * ---------------------------------------------------------------------------
 * Every exported function below is written as `async` and returns data
 * shaped exactly like the future Flask JSON responses. Right now the
 * implementation reads/writes localStorage as a stand-in database so the
 * whole frontend is fully clickable without a server.
 *
 * To connect the real backend later: replace the body of each function with
 * a `fetch()` call to the noted endpoint and keep the same return shape —
 * no page code needs to change. The commented `fetch` calls show the
 * intended contract.
 *
 * Endpoints this file expects to eventually call:
 *   POST   /api/auth/signup
 *   POST   /api/auth/login
 *   POST   /api/auth/logout
 *   GET    /api/auth/me
 *   POST   /api/reports/lost
 *   POST   /api/reports/found
 *   GET    /api/reports/mine
 *   GET    /api/matches/:id
 *   POST   /api/matches/:id/respond
 *
 * Photo uploads: for now files are read client-side into base64 data URLs
 * and stored inline. The real backend should instead accept
 * multipart/form-data and return a hosted image URL — swap
 * `readFileAsDataUrl()` usage in the report forms for a normal
 * `FormData` upload when that endpoint exists, and the AI matching service
 * can hang off the same upload handler server-side.
 * ---------------------------------------------------------------------------
 */

const AUPP_EMAIL_DOMAIN = '@aupp.edu.kh';

const DB_KEYS = {
  users: 'foundit_users',
  session: 'foundit_session',
  reports: 'foundit_reports',
  matches: 'foundit_matches',
};

function readDb(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || [];
  } catch (e) {
    return [];
  }
}
function writeDb(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}
function uid(prefix) {
  return prefix + '_' + Math.random().toString(36).slice(2, 10);
}
function delay(ms = 320) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
function simpleHash(str) {
  // Placeholder only — real password hashing happens server-side (e.g. bcrypt).
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return String(hash);
}

/* --------------------------------------------------------------------- */
/* Seed demo data so the app is explorable on first load                 */
/* --------------------------------------------------------------------- */
function seedIfEmpty() {
  const users = readDb(DB_KEYS.users);
  if (users.length) return;

  const demoUser = {
    id: 'user_demo',
    name: 'Sophea Chan',
    email: 'sophea.chan' + AUPP_EMAIL_DOMAIN,
    passwordHash: simpleHash('foundit123'),
    createdAt: new Date().toISOString(),
  };
  writeDb(DB_KEYS.users, [demoUser]);

  const now = Date.now();
  const day = 86400000;

  const reports = [
    {
      id: 'report_lost_1',
      ownerId: demoUser.id,
      kind: 'lost',
      itemName: 'Blue Hydro Flask Water Bottle',
      description: 'Navy blue, 32oz, with a Faculty of Digital Technologies sticker on the front.',
      location: 'Library, 2nd floor study area',
      dateTime: new Date(now - 2 * day).toISOString(),
      photo: null,
      status: 'potential_match',
      createdAt: new Date(now - 2 * day).toISOString(),
    },
    {
      id: 'report_lost_2',
      ownerId: demoUser.id,
      kind: 'lost',
      itemName: 'Student ID Card',
      description: 'AUPP student card, name Sophea Chan, slight bend in the top corner.',
      location: 'Cafeteria',
      dateTime: new Date(now - 6 * day).toISOString(),
      photo: null,
      status: 'searching',
      createdAt: new Date(now - 6 * day).toISOString(),
    },
    {
      id: 'report_lost_3',
      ownerId: demoUser.id,
      kind: 'lost',
      itemName: 'Black Wired Earphones',
      description: 'JBL earphones in a small black case.',
      location: 'Room 305',
      dateTime: new Date(now - 15 * day).toISOString(),
      photo: null,
      status: 'returned',
      createdAt: new Date(now - 15 * day).toISOString(),
    },
    {
      id: 'report_found_1',
      ownerId: demoUser.id,
      kind: 'found',
      itemName: 'Found item',
      description: 'A grey umbrella left folded by the entrance turnstile.',
      location: 'Main entrance',
      dateTime: new Date(now - 9 * day).toISOString(),
      photo: null,
      status: 'claimed',
      createdAt: new Date(now - 9 * day).toISOString(),
    },
    // The item someone else found that potentially matches report_lost_1
    {
      id: 'report_found_match',
      ownerId: 'user_other_1',
      kind: 'found',
      itemName: 'Found item',
      description: 'A navy-blue insulated water bottle, looks like a Hydro Flask. Left on a study table.',
      location: 'Library, 2nd floor near the windows',
      dateTime: new Date(now - 1 * day).toISOString(),
      photo: null,
      status: 'potential_match',
      createdAt: new Date(now - 1 * day).toISOString(),
    },
  ];
  writeDb(DB_KEYS.reports, reports);

  const matches = [
    {
      id: 'match_demo_1',
      lostReportId: 'report_lost_1',
      foundReportId: 'report_found_match',
      status: 'pending',
      confidence: 0.86,
      createdAt: new Date(now - 1 * day).toISOString(),
    },
  ];
  writeDb(DB_KEYS.matches, matches);
}
seedIfEmpty();

/* --------------------------------------------------------------------- */
/* Auth                                                                   */
/* --------------------------------------------------------------------- */

function isUniversityEmail(email) {
  return typeof email === 'string' && email.toLowerCase().endsWith(AUPP_EMAIL_DOMAIN);
}

async function signup({ name, email, password }) {
  await delay();
  // Future: return fetch('/api/auth/signup', { method: 'POST', body: JSON.stringify({name, email, password}) }).then(r => r.json());
  if (!isUniversityEmail(email)) {
    throw new Error(`Please use your AUPP email address (ends with ${AUPP_EMAIL_DOMAIN}).`);
  }
  const users = readDb(DB_KEYS.users);
  if (users.some((u) => u.email.toLowerCase() === email.toLowerCase())) {
    throw new Error('An account with this email already exists. Try logging in instead.');
  }
  const user = {
    id: uid('user'),
    name: name.trim(),
    email: email.toLowerCase(),
    passwordHash: simpleHash(password),
    createdAt: new Date().toISOString(),
  };
  users.push(user);
  writeDb(DB_KEYS.users, users);
  writeDb(DB_KEYS.session, { userId: user.id });
  return { user: publicUser(user) };
}

async function login({ email, password }) {
  await delay();
  // Future: return fetch('/api/auth/login', { method: 'POST', body: JSON.stringify({email, password}) }).then(r => r.json());
  const users = readDb(DB_KEYS.users);
  const user = users.find((u) => u.email.toLowerCase() === email.toLowerCase());
  if (!user || user.passwordHash !== simpleHash(password)) {
    throw new Error('That email and password combination doesn\'t match our records.');
  }
  writeDb(DB_KEYS.session, { userId: user.id });
  return { user: publicUser(user) };
}

async function logout() {
  await delay(120);
  // Future: return fetch('/api/auth/logout', { method: 'POST' });
  localStorage.removeItem(DB_KEYS.session);
}

function getCurrentUser() {
  // Synchronous on purpose: pages call this on load to guard access before
  // painting. Future backend equivalent is a quick GET /api/auth/me,
  // typically checked via an httpOnly session cookie.
  const session = JSON.parse(localStorage.getItem(DB_KEYS.session) || 'null');
  if (!session) return null;
  const users = readDb(DB_KEYS.users);
  const user = users.find((u) => u.id === session.userId);
  return user ? publicUser(user) : null;
}

function publicUser(user) {
  return { id: user.id, name: user.name, email: user.email };
}

/* --------------------------------------------------------------------- */
/* Reports                                                                */
/* --------------------------------------------------------------------- */

async function createLostReport(data) {
  await delay(500);
  // Future: POST /api/reports/lost (multipart/form-data with the photo file)
  const user = getCurrentUser();
  if (!user) throw new Error('Please log in again.');
  const reports = readDb(DB_KEYS.reports);
  const report = {
    id: uid('report'),
    ownerId: user.id,
    kind: 'lost',
    itemName: data.itemName.trim(),
    description: data.description.trim(),
    location: data.location.trim(),
    dateTime: data.dateTime,
    photo: data.photo || null,
    status: 'searching',
    createdAt: new Date().toISOString(),
  };
  reports.unshift(report);
  writeDb(DB_KEYS.reports, reports);
  return { report };
}

async function createFoundReport(data) {
  await delay(500);
  // Future: POST /api/reports/found (multipart/form-data with the photo file)
  // The AI image-matching pipeline would run server-side right after this
  // upload completes, comparing the photo against open lost reports.
  const user = getCurrentUser();
  if (!user) throw new Error('Please log in again.');
  const reports = readDb(DB_KEYS.reports);
  const report = {
    id: uid('report'),
    ownerId: user.id,
    kind: 'found',
    itemName: 'Found item',
    description: (data.description || '').trim(),
    location: data.location.trim(),
    dateTime: new Date().toISOString(),
    photo: data.photo || null,
    status: 'searching',
    createdAt: new Date().toISOString(),
  };
  reports.unshift(report);
  writeDb(DB_KEYS.reports, reports);
  return { report };
}

async function getMyReports() {
  await delay(250);
  // Future: return fetch('/api/reports/mine').then(r => r.json());
  const user = getCurrentUser();
  if (!user) throw new Error('Please log in again.');
  const reports = readDb(DB_KEYS.reports).filter((r) => r.ownerId === user.id);
  return {
    lost: reports.filter((r) => r.kind === 'lost'),
    found: reports.filter((r) => r.kind === 'found'),
  };
}

/* --------------------------------------------------------------------- */
/* Matches                                                                */
/* --------------------------------------------------------------------- */

async function getMatch(matchId) {
  await delay(300);
  // Future: return fetch(`/api/matches/${matchId}`).then(r => r.json());
  const matches = readDb(DB_KEYS.matches);
  const match = matches.find((m) => m.id === matchId);
  if (!match) throw new Error('This match link is no longer valid.');
  const reports = readDb(DB_KEYS.reports);
  const lostReport = reports.find((r) => r.id === match.lostReportId);
  const foundReport = reports.find((r) => r.id === match.foundReportId);
  return { match, lostReport, foundReport };
}

async function respondToMatch(matchId, confirmed) {
  await delay(400);
  // Future: return fetch(`/api/matches/${matchId}/respond`, { method: 'POST', body: JSON.stringify({ confirmed }) }).then(r => r.json());
  const matches = readDb(DB_KEYS.matches);
  const match = matches.find((m) => m.id === matchId);
  if (!match) throw new Error('This match link is no longer valid.');
  match.status = confirmed ? 'confirmed' : 'rejected';

  const reports = readDb(DB_KEYS.reports);
  const lostReport = reports.find((r) => r.id === match.lostReportId);
  const foundReport = reports.find((r) => r.id === match.foundReportId);
  if (confirmed) {
    if (lostReport) lostReport.status = 'claimed';
    if (foundReport) foundReport.status = 'claimed';
  } else {
    if (lostReport) lostReport.status = 'searching';
    // The found item stays available for other possible matches.
    if (foundReport) foundReport.status = 'searching';
  }
  writeDb(DB_KEYS.matches, matches);
  writeDb(DB_KEYS.reports, reports);
  return { match };
}

/* --------------------------------------------------------------------- */
/* Exported namespace                                                     */
/* --------------------------------------------------------------------- */
const api = {
  AUPP_EMAIL_DOMAIN,
  isUniversityEmail,
  signup,
  login,
  logout,
  getCurrentUser,
  createLostReport,
  createFoundReport,
  getMyReports,
  getMatch,
  respondToMatch,
};
