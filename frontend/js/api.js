/**
 * api.js - FoundIt data layer
 * ---------------------------------------------------------------------------
 * Every page talks to the server only through the functions exported at the
 * bottom of this file.
 *
 *   LIVE (real Flask backend):   signup, login, logout, getCurrentUser,
 *                                createLostReport, createFoundReport, getMyReports
 *   MOCK (localStorage for now): getMatch, respondToMatch
 *
 * The mock functions are marked "MOCK" below. They get replaced one step at a
 * time (matching -> confirmation page) with the same
 * return shapes, so the pages never need to change again.
 *
 * The login cookie is HttpOnly - JavaScript never sees it or the password
 * hash. No secrets (API keys etc.) ever belong in this file.
 * ---------------------------------------------------------------------------
 */

const AUPP_EMAIL_DOMAIN = '@aupp.edu.kh';

/* --------------------------------------------------------------------- */
/* Talking to the server                                                  */
/* --------------------------------------------------------------------- */

// Same address as the pages (Flask serves both), so the base is empty.
const API_BASE = '';

async function request(path, { method = 'GET', body, form } = {}) {
  const options = { method, credentials: 'same-origin', headers: {} };
  if (form !== undefined) {
    // FormData (used for photo uploads). Don't set Content-Type: the browser
    // adds it, including the boundary the server needs.
    options.body = form;
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(API_BASE + path, options);
  } catch (networkError) {
    throw new Error("Can't reach the server. Make sure the Flask app is running.");
  }

  let data = null;
  try {
    data = await response.json();
  } catch (notJson) {
    /* empty or non-JSON body */
  }

  if (!response.ok) {
    const err = new Error((data && data.error) || 'Something went wrong. Please try again.');
    err.status = response.status;
    throw err;
  }
  return data;
}

/* --------------------------------------------------------------------- */
/* Auth  (LIVE)                                                           */
/* --------------------------------------------------------------------- */

let currentUserCache = null; // filled in by getCurrentUser / login / signup

function isUniversityEmail(email) {
  // Quick check for friendly errors; the server enforces this for real.
  return typeof email === 'string' && email.toLowerCase().endsWith(AUPP_EMAIL_DOMAIN);
}

async function signup({ name, email, password }) {
  const data = await request('/api/auth/signup', { method: 'POST', body: { name, email, password } });
  currentUserCache = data.user;
  return data;
}

async function login({ email, password }) {
  const data = await request('/api/auth/login', { method: 'POST', body: { email, password } });
  currentUserCache = data.user;
  return data;
}

async function logout() {
  try {
    await request('/api/auth/logout', { method: 'POST' });
  } finally {
    currentUserCache = null;
  }
}

/** Asks the server who is logged in. Resolves to the user, or null if nobody is. */
async function getCurrentUser() {
  try {
    const data = await request('/api/auth/me');
    currentUserCache = data.user;
  } catch (err) {
    if (err.status !== 401) throw err;
    currentUserCache = null;
  }
  return currentUserCache;
}

/** Instant, no network: whoever getCurrentUser/login/signup last returned. */
function getCachedUser() {
  return currentUserCache;
}

/* --------------------------------------------------------------------- */
/* MOCK storage - used only by the match functions below, until they are  */
/* replaced with real endpoints.                                          */
/* --------------------------------------------------------------------- */

const DB_KEYS = {
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

/* --------------------------------------------------------------------- */
/* Reports  (LIVE)                                                        */
/* --------------------------------------------------------------------- */

/** photo: a File from <input type="file"> (optional), not a data URL. */
async function createLostReport({ itemName, description, location, dateTime, photo }) {
  const form = new FormData();
  form.append('itemName', itemName);
  form.append('description', description);
  form.append('location', location);
  // The <input type="datetime-local"> value is the person's local time with no
  // timezone. Convert to UTC so the server stores one consistent clock.
  form.append('dateTime', new Date(dateTime).toISOString());
  if (photo) form.append('photo', photo);
  return request('/api/reports/lost', { method: 'POST', form });
}

/** photo: a File (required). */
async function createFoundReport({ location, description, photo }) {
  const form = new FormData();
  form.append('location', location);
  form.append('description', description || '');
  form.append('photo', photo);
  return request('/api/reports/found', { method: 'POST', form });
}

/** Resolves to { lost: [...], found: [...] } for the logged-in user, newest first. */
async function getMyReports() {
  return request('/api/reports/mine');
}

/* --------------------------------------------------------------------- */
/* Matches  (MOCK - replaced in Steps 3-4)                                  */
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
  getCachedUser,
  createLostReport,
  createFoundReport,
  getMyReports,
  getMatch,
  respondToMatch,
};
