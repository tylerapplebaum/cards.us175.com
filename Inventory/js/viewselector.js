// Track the current view mode
let currentView = 'checklist';

// Helper: rebuild table based on view mode
function updateTableView(view) {
    const itemsTable = document.getElementById('itemsTable');
    const thead = itemsTable.querySelector('thead tr');
    const tfoot = itemsTable.querySelector('tfoot tr');
    const tbody = itemsTable.querySelector('tbody');

    // Reset to base columns
    thead.innerHTML = `
    <th scope="col" class="column0" hidden>guid</th>
    <th scope="col" class="column1">Year</th>
    <th scope="col" class="column2">Set</th>
    <th scope="col" class="column3">Subset</th>
    <th scope="col" class="column4">CardNum</th>
    <th scope="col" class="column5">Player</th>
    <th scope="col" class="column6">Qty</th>
    <th scope="col" class="column7">Action</th>
    `;

    // Add new columns for Details or Financial view
    if (view === 'details') {
    thead.insertAdjacentHTML('beforeend', `
        <th scope="col" class="column8">Authenticator</th>
        <th scope="col" class="column9">Grade</th>
        <th scope="col" class="column10">CertNum</th>
        <th scope="col" class="column11">BoxNum</th>
        <th scope="col" class="column12">SerialNumber</th>
    `);
    } else if (view === 'financial') {
    thead.insertAdjacentHTML('beforeend', `
        <th scope="col" class="column8">Authenticator</th>
        <th scope="col" class="column9">Grade</th>
        <th scope="col" class="column10">Purchase Price</th>
        <th scope="col" class="column11">Grading Fee</th>
        <th scope="col" class="column12">MktVal</th>
        <th scope="col" class="column13">Txn Source</th>
    `);
    }

    // Rebuild body if data already loaded
    if (window.lastFetchedData) populateTable(window.lastFetchedData);
}
// Set up labels for mobile view
function applyMobileLabels(rowEl) {
  const headers = Array.from(document.querySelectorAll('#itemsTable thead th'))
    .filter(th => !th.hidden)   // skip GUID header
    .map(th => th.textContent.trim());

  const cells = Array.from(rowEl.querySelectorAll('td'))
    .filter(td => !td.hidden);  // skip GUID cell

  cells.forEach((td, i) => {
    td.setAttribute('data-label', headers[i] || '');
  });
}

// Rebuild the table body based on current view
function populateTable(data) {
    const tbody = document.querySelector('#itemsTable tbody');
    const tfoot = document.querySelector('tfoot');
    tbody.innerHTML = '';
    tfoot.innerHTML = ''; // reset footer
    let mktValTotal = 0;
    let gradingFeeTotal = 0;
    let purchPriceTotal = 0;
    data.body.forEach((item, index) => {
    let baseCols = `
        <td class="column0" hidden>${sanitizeValue(item.guid)}</td>
        <td class="column1">${sanitizeValue(item.Year)}</td>
        <td class="column2">${sanitizeValue(item.Set)}</td>
        <td class="column3">${sanitizeValue(item.Subset)}</td>
        <td class="column4">${sanitizeValue(item.CardNum)}</td>
        <td class="column5">${sanitizeValue(item.PlayerName)}</td>
        <td class="column6">${sanitizeValue(item.Qty)}</td>
        <td class="column7">
        <a href="#"
            class="btn btn-info btn-sm details-btn"
            data-index="${index}"
            data-toggle="modal"
            data-target="#staticBackdrop">
            Details
        </a>
        </td>
    `;

    let extraCols = '';
    if (currentView === 'details') {
        extraCols = `
        <td class="column8">${sanitizeValue(item.Authenticator)}</td>
        <td class="column9">${sanitizeValue(item.Grade)}</td>
        <td class="column10">${sanitizeValue(item.CertNumber)}</td>
        <td class="column11">${sanitizeValue(item.BoxNum)}</td>
        <td class="column12">${sanitizeValue(item.SerialNumber)}</td>
        `;
    } else if (currentView === 'financial') {
        const mktVal = parseFloat(item.MktVal);
        if (!isNaN(mktVal)) {
        mktValTotal += mktVal;
        }
        const purchPrice = parseFloat(item.PurchasePrice);
        if (!isNaN(purchPrice)) {
        purchPriceTotal += purchPrice;
        }
        const gradeFee = parseFloat(item.GradingFee);
        if (!isNaN(gradeFee)) {
        gradingFeeTotal += gradeFee;
        }
        extraCols = `
        <td class="column8">${sanitizeValue(item.Authenticator)}</td>
        <td class="column9">${sanitizeValue(item.Grade)}</td>
        <td class="column10">${sanitizeValue(item.PurchasePrice)}</td>
        <td class="column11">${sanitizeValue(item.GradingFee)}</td>
        <td class="column12">${sanitizeValue(item.MktVal)}</td>
        <td class="column13">${sanitizeValue(item.TxnSource)}</td>
        `;
    }

    const row = document.createElement('tr');
    row.innerHTML = baseCols + extraCols;
    applyMobileLabels(row);
    tbody.appendChild(row);
    });

    // ---- FOOTER (financial view only) ----
    if (currentView === 'financial') {
        const footerRow = document.createElement('tr');
        footerRow.classList.add('table100-foot');
        footerRow.innerHTML = `
        <th colspan="9"></th>
        <th title="Purchase price total">${formatMoney(purchPriceTotal)}</th>
        <th title="Grading fee total">${formatMoney(gradingFeeTotal)}</th>
        <th title="Market value total">${formatMoney(mktValTotal)}</th>
        <th colspan="1"></th>
        `;
        tfoot.appendChild(footerRow);
    }
}
// Wire up the buttons
document.querySelector('#view-selector .btn-secondary').addEventListener('click', () => {
    currentView = 'checklist';
    updateTableView('checklist');
});
document.querySelector('#view-selector .btn-info').addEventListener('click', () => {
    currentView = 'details';
    updateTableView('details');
});
document.querySelector('#view-selector .btn-success').addEventListener('click', () => {
    currentView = 'financial';
    updateTableView('financial');
});