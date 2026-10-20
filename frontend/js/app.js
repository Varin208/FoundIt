/**
 * app.js — shared page utilities: auth guarding, header wiring,
 * formatting helpers, and small UI behaviors reused across pages.
 */

/**
 * Asks the server who is logged in; sends visitors to the login page if nobody is.
 * Use at the top of every protected page:   const user = await requireAuth();
 */
async function requireAuth() {
  let user = null;
  try {
    user = await api.getCurrentUser();
  } catch (err) {
    user = null; // server unreachable -> treat as logged out (login page explains)
  }
  if (!user) {
    // Remember where they were headed (e.g. a potential-match link from an
    // email) so login can send them back after they sign in.
    sessionStorage.setItem('foundit_redirect', window.location.pathname + window.location.search);
    window.location.href = 'login.html';
    return null;
  }
  return user;
}

/** Wires up the shared header once the page's #site-header partial is in the DOM. */
function initHeader(activePage) {
  const user = api.getCachedUser(); // already loaded by requireAuth()
  const nameEl = document.querySelector('[data-user-name]');
  const initialEl = document.querySelector('[data-user-initial]');
  if (user) {
    if (nameEl) nameEl.textContent = user.name;
    if (initialEl) initialEl.textContent = user.name.trim().charAt(0).toUpperCase();
  }

  document.querySelectorAll('.site-nav a[data-page]').forEach((link) => {
    if (link.dataset.page === activePage) {
      link.setAttribute('aria-current', 'page');
    }
  });

  const toggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('.site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      nav.classList.toggle('is-open');
    });
  }

  const logoutBtn = document.querySelector('[data-logout]');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await api.logout();
      window.location.href = 'login.html';
    });
  }
}

/** Formats an ISO date string like "Sep 20, 2026 · 3:40 PM". */
function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const datePart = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  const timePart = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `${datePart} · ${timePart}`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

const STATUS_LABELS = {
  searching: 'Searching',
  potential_match: 'Potential match',
  claimed: 'Claimed',
  returned: 'Returned',
};
const STATUS_CLASSES = {
  searching: 'status--searching',
  potential_match: 'status--potential-match',
  claimed: 'status--claimed',
  returned: 'status--returned',
};
function statusPillHtml(status) {
  const label = STATUS_LABELS[status] || status;
  const cls = STATUS_CLASSES[status] || 'status--searching';
  return `<span class="status ${cls}">${label}</span>`;
}

/** Reads a File object into a base64 data URL (stand-in for a real upload). */
function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

const MAX_PHOTO_BYTES = 10 * 1024 * 1024; // 10MB, matches the server limit

/**
 * Wires a .photo-upload dropzone + hidden file input + preview block.
 * onChange(dataUrl, file) runs when a photo is chosen, and onChange(null, null)
 * when it is removed. `dataUrl` is only for the preview; upload the `file`.
 * onInvalid(message) runs if the chosen file isn't an image or is too big.
 */
function initPhotoUpload({ dropzoneSelector, inputSelector, previewSelector, imgSelector, removeSelector, onChange, onInvalid }) {
  const dropzone = document.querySelector(dropzoneSelector);
  const input = document.querySelector(inputSelector);
  const preview = document.querySelector(previewSelector);
  const img = document.querySelector(imgSelector);
  const removeBtn = document.querySelector(removeSelector);
  if (!dropzone || !input) return;

  async function handleFiles(files) {
    const file = files && files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      input.value = '';
      if (onInvalid) onInvalid('That file is not an image. Please choose a JPG or PNG photo.');
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      input.value = '';
      if (onInvalid) onInvalid('That photo is larger than 10MB. Please choose a smaller one.');
      return;
    }
    const dataUrl = await readFileAsDataUrl(file);
    if (img) img.src = dataUrl;
    if (preview) preview.classList.add('is-visible');
    dropzone.style.display = 'none';
    if (onChange) onChange(dataUrl, file);
  }

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  input.addEventListener('change', (e) => handleFiles(e.target.files));

  ['dragover', 'dragenter'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add('is-dragover'); })
  );
  ['dragleave', 'drop'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove('is-dragover'); })
  );
  dropzone.addEventListener('drop', (e) => handleFiles(e.dataTransfer.files));

  if (removeBtn) {
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      input.value = '';
      if (preview) preview.classList.remove('is-visible');
      dropzone.style.display = '';
      if (onChange) onChange(null, null);
    });
  }
}

function showBanner(el, message, type = 'error') {
  if (!el) return;
  el.textContent = message;
  el.classList.remove('form-banner--error', 'form-banner--success');
  el.classList.add(type === 'success' ? 'form-banner--success' : 'form-banner--error', 'is-visible');
}
function hideBanner(el) {
  if (!el) return;
  el.classList.remove('is-visible');
}
