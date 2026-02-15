let currentView = "checklist";
let wantlistItems = [];

function sanitizeValue(value) {
  if (value === undefined || value === null || value === "undefined") return "";
  return String(value).trim();
}

function formatMoney(value) {
  const n = parseFloat(value);
  if (Number.isNaN(n)) return "";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function setStatus(message, variant) {
  const banner = document.getElementById("statusBanner");
  if (!banner) return;
  banner.className = `alert py-2 mb-0 alert-${variant}`;
  banner.textContent = message;
}

function renderHeaders(view) {
  const head = document.querySelector("#itemsTable thead tr");
  if (!head) return;
  head.innerHTML = `
    <th scope="col" class="column0" hidden>guid</th>
    <th scope="col" class="column1">Year</th>
    <th scope="col" class="column2">Set</th>
    <th scope="col" class="column3">Subset</th>
    <th scope="col" class="column4">CardNum</th>
    <th scope="col" class="column5">Player</th>
    <th scope="col" class="column6">Qty</th>
  `;

  if (view === "details") {
    head.insertAdjacentHTML(
      "beforeend",
      `
      <th scope="col" class="column8">Authenticator</th>
      <th scope="col" class="column9">Grade</th>
      <th scope="col" class="column10">CertNum</th>
      <th scope="col" class="column11">BoxNum</th>
      <th scope="col" class="column12">SerialNumber</th>
    `
    );
  }

  if (view === "financial") {
    head.insertAdjacentHTML(
      "beforeend",
      `
      <th scope="col" class="column8">Authenticator</th>
      <th scope="col" class="column9">Grade</th>
      <th scope="col" class="column10">Purchase Price</th>
      <th scope="col" class="column11">Grading Fee</th>
      <th scope="col" class="column12">MktVal</th>
      <th scope="col" class="column13">Txn Source</th>
    `
    );
  }
}

function applyMobileLabels(rowEl) {
  const headers = Array.from(document.querySelectorAll("#itemsTable thead th"))
    .filter((th) => !th.hidden)
    .map((th) => th.textContent.trim());
  const cells = Array.from(rowEl.querySelectorAll("td")).filter((td) => !td.hidden);
  cells.forEach((td, i) => td.setAttribute("data-label", headers[i] || ""));
}

function renderRows(items, view) {
  const tbody = document.querySelector("#itemsTable tbody");
  const tfoot = document.querySelector("#itemsTable tfoot tr");
  if (!tbody || !tfoot) return;

  tbody.innerHTML = "";
  tfoot.innerHTML = "";

  let mktValTotal = 0;
  let gradingFeeTotal = 0;
  let purchasePriceTotal = 0;

  items.forEach((item) => {
    let extraCols = "";
    if (view === "details") {
      extraCols = `
        <td class="column8">${sanitizeValue(item.Authenticator)}</td>
        <td class="column9">${sanitizeValue(item.Grade)}</td>
        <td class="column10">${sanitizeValue(item.CertNumber)}</td>
        <td class="column11">${sanitizeValue(item.BoxNum)}</td>
        <td class="column12">${sanitizeValue(item.SerialNumber)}</td>
      `;
    }

    if (view === "financial") {
      const mktVal = parseFloat(item.MktVal);
      const gradingFee = parseFloat(item.GradingFee);
      const purchasePrice = parseFloat(item.PurchasePrice);
      if (!Number.isNaN(mktVal)) mktValTotal += mktVal;
      if (!Number.isNaN(gradingFee)) gradingFeeTotal += gradingFee;
      if (!Number.isNaN(purchasePrice)) purchasePriceTotal += purchasePrice;

      extraCols = `
        <td class="column8">${sanitizeValue(item.Authenticator)}</td>
        <td class="column9">${sanitizeValue(item.Grade)}</td>
        <td class="column10">${sanitizeValue(item.PurchasePrice)}</td>
        <td class="column11">${sanitizeValue(item.GradingFee)}</td>
        <td class="column12">${sanitizeValue(item.MktVal)}</td>
        <td class="column13">${sanitizeValue(item.TxnSource)}</td>
      `;
    }

    const row = document.createElement("tr");
    row.dataset.guid = sanitizeValue(item.guid);
    row.innerHTML = `
      <td class="column0" hidden>${sanitizeValue(item.guid)}</td>
      <td class="column1">${sanitizeValue(item.Year)}</td>
      <td class="column2">${sanitizeValue(item.Set)}</td>
      <td class="column3">${sanitizeValue(item.Subset)}</td>
      <td class="column4">${sanitizeValue(item.CardNum)}</td>
      <td class="column5">${sanitizeValue(item.PlayerName)}</td>
      <td class="column6">${sanitizeValue(item.Qty)}</td>
      ${extraCols}
    `;
    applyMobileLabels(row);
    tbody.appendChild(row);
  });

  if (view === "financial") {
    tfoot.innerHTML = `
      <th colspan="9"></th>
      <th title="Purchase price total">${formatMoney(purchasePriceTotal)}</th>
      <th title="Grading fee total">${formatMoney(gradingFeeTotal)}</th>
      <th title="Market value total">${formatMoney(mktValTotal)}</th>
      <th colspan="1"></th>
    `;
  }
}

function applyFilter() {
  const filterInput = document.getElementById("tableFilter");
  const select = document.getElementById("tableFilterSelect");
  const tbodyRows = document.querySelectorAll("#itemsTable tbody tr");
  const filterText = (filterInput?.value || "").toUpperCase();
  const columnClass = select?.value || "column5";

  let visible = 0;
  tbodyRows.forEach((row) => {
    const cell = row.querySelector(`td.${columnClass}`);
    const text = (cell?.textContent || "").toUpperCase();
    const matches = text.includes(filterText);
    row.style.display = matches ? "" : "none";
    if (matches) visible += 1;
  });

  const resultsBadge = document.getElementById("num-results");
  if (resultsBadge) resultsBadge.textContent = String(visible);
}

function getVisibleRows() {
  return Array.from(document.querySelectorAll("#itemsTable tbody tr")).filter(
    (row) => row.style.display !== "none"
  );
}

function exportVisibleToCSV() {
  const rows = getVisibleRows();
  if (!rows.length) {
    alert("No rows to export.");
    return;
  }

  const headers = Array.from(document.querySelectorAll("#itemsTable thead th"))
    .filter((th) => !th.hidden)
    .map((th) => th.textContent.trim());

  let csvContent = `${headers.join(",")}\n`;
  rows.forEach((row) => {
    const values = Array.from(row.querySelectorAll("td"))
      .filter((td) => !td.hidden)
      .map((td) => {
        const escaped = (td.textContent || "").replace(/"/g, "\"\"");
        return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
      });
    csvContent += `${values.join(",")}\n`;
  });

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `wantlist_export_${Date.now()}.csv`);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function setGeneratedAt(value) {
  const el = document.getElementById("generated-at");
  if (!el) return;
  if (!value) {
    el.textContent = "-";
    return;
  }
  const dt = new Date(value);
  el.textContent = Number.isNaN(dt.valueOf()) ? sanitizeValue(value) : dt.toLocaleString();
}

function renderView() {
  renderHeaders(currentView);
  renderRows(wantlistItems, currentView);
  applyFilter();
}

async function loadWantlist() {
  const response = await fetch("wantlist.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load wantlist.json (${response.status})`);
  }
  const payload = await response.json();
  const items = Array.isArray(payload) ? payload : payload.items;
  if (!Array.isArray(items)) {
    throw new Error("Invalid wantlist payload.");
  }
  wantlistItems = items;
  setGeneratedAt(payload.generatedAt);
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("tableFilter")?.addEventListener("input", applyFilter);
  document.getElementById("tableFilterSelect")?.addEventListener("change", applyFilter);
  document.getElementById("exportBtn")?.addEventListener("click", exportVisibleToCSV);

  document.querySelectorAll("#view-selector [data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      currentView = button.dataset.view || "checklist";
      renderView();
    });
  });

  try {
    await loadWantlist();
    renderView();
    setStatus(`Loaded ${wantlistItems.length} wantlist cards.`, "success");
  } catch (err) {
    setStatus(`Could not load wantlist data: ${err.message}`, "danger");
  }
});
