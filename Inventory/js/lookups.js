let authRedirectStarted = false;

function isProtectedLookup(url) {
  return url.startsWith('partials/') || url.startsWith('/Inventory/partials/');
}

function redirectToAuth() {
  if (authRedirectStarted) return;
  authRedirectStarted = true;

  // Force a top-level navigation so CloudFront can perform the Cognito redirect.
  window.location.assign(window.location.pathname + window.location.search);
}

async function populateSelect({ url, key, selectId }) {
  try {
    const res = await fetch(url, {
      credentials: 'same-origin',
      redirect: 'manual'
    });

    // Browser hides cross-origin redirect targets from fetch as "opaqueredirect".
    if (res.type === 'opaqueredirect' || res.status === 307 || res.status === 302) {
      redirectToAuth();
      return;
    }

    if (!res.ok) throw new Error(`Failed to fetch ${url}`);

    const data = await res.json();
    const list = document.getElementById(selectId);
    if (!list) return;

    data[key].forEach(item => {
      const option = document.createElement('option');
      option.value = item;
      option.textContent = item;
      list.appendChild(option);
    });
  } catch (err) {
    // CORS-blocked redirected auth requests are surfaced as generic fetch failures.
    if (err instanceof TypeError && isProtectedLookup(url)) {
      redirectToAuth();
      return;
    }

    console.error(`Error loading ${selectId}:`, err);
  }
}

function loadLookups() {
  populateSelect({
    url: 'partials/sets.json',
    key: 'Sets',
    selectId: 'setSearchList'
  });

  populateSelect({
    url: 'partials/subsets.json',
    key: 'Subsets',
    selectId: 'subsetSearchList'
  });

  populateSelect({
    url: 'https://test.us175.com/PriceArchive/players.json',
    key: 'Players',
    selectId: 'playerSearchList'
  });

  populateSelect({
    url: 'partials/boxes.json',
    key: 'Boxes',
    selectId: 'boxSearchList'
  });
}
