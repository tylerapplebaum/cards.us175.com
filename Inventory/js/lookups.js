let authRedirectStarted = false;
const authRecoveryKey = 'inventory.lookupAuthRecovery';

function showLookupError(message) {
  let notice = document.getElementById('lookupError');
  if (!notice) {
    notice = document.createElement('div');
    notice.id = 'lookupError';
    notice.className = 'alert alert-warning m-3';
    notice.setAttribute('role', 'alert');
    document.body.prepend(notice);
  }
  notice.textContent = message;
}

function isProtectedLookup(url) {
  return url.startsWith('partials/') || url.startsWith('/Inventory/partials/');
}

function redirectToAuth() {
  if (authRedirectStarted) return;
  authRedirectStarted = true;

  try {
    if (sessionStorage.getItem(authRecoveryKey)) {
      showLookupError('Unable to restore your session. Please sign in again, then reload this page.');
      return;
    }
    sessionStorage.setItem(authRecoveryKey, '1');
  } catch (err) {
    // Without persistent storage, an automatic navigation could loop forever.
    console.error('Unable to save authentication recovery state:', err);
    showLookupError('Unable to restore your session automatically. Please sign in again, then reload this page.');
    return;
  }

  // Force a top-level navigation so CloudFront can perform the Cognito redirect.
  window.location.assign(window.location.pathname + window.location.search);
}

async function populateSelect({ url, key, selectId }) {
  try {
    const res = await fetch(url, {
      credentials: 'same-origin',
      redirect: 'manual',
      cache: 'no-store'
    });

    // Manual redirects hide the target; allow only one automatic recovery attempt.
    if (res.type === 'opaqueredirect' || res.status === 307 || res.status === 302) {
      redirectToAuth();
      return false;
    }

    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);

    const data = await res.json();
    const list = document.getElementById(selectId);
    if (!list) throw new Error(`Missing select element: ${selectId}`);

    data[key].forEach(item => {
      const option = document.createElement('option');
      option.value = item;
      option.textContent = item;
      list.appendChild(option);
    });
    return true;
  } catch (err) {
    console.error(`Error loading ${selectId}:`, err);
    if (!authRedirectStarted) {
      showLookupError('Some search options could not be loaded. Check your connection and reload this page to retry.');
    }
    return false;
  }
}

async function loadLookups() {
  const lookups = [{
    url: 'partials/sets.json',
    key: 'Sets',
    selectId: 'setSearchList'
  }, {
    url: 'partials/subsets.json',
    key: 'Subsets',
    selectId: 'subsetSearchList'
  }, {
    url: 'https://test.us175.com/PriceArchive/players.json',
    key: 'Players',
    selectId: 'playerSearchList'
  }, {
    url: 'partials/boxes.json',
    key: 'Boxes',
    selectId: 'boxSearchList'
  }];

  const results = await Promise.all(lookups.map(populateSelect));
  if (!authRedirectStarted && lookups.every((lookup, index) =>
    !isProtectedLookup(lookup.url) || results[index]
  )) {
    try {
      sessionStorage.removeItem(authRecoveryKey);
    } catch (err) {
      console.error('Unable to clear authentication recovery state:', err);
    }
  }
}
