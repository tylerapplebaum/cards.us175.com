async function populateSelect({ url, key, selectId }) {
  try {
    const res = await fetch(url);
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
