// Features:
// - Reads CSV from #csvInput, converts to base64 (window.b64CSV) for API Gateway/Lambda payload
// - Displays row count and required-field validation status in #csvMeta
// - Disables/enables #bulk-add button appropriately
// - Shows an uploading spinner/state while POST is in-flight
//
// Assumptions:
// - CSV is simple (no quoted commas/newlines). If you later need full CSV parsing, swap parseCsvLineSimple.

function parseCsvLineSimple(line) {
  // Simple split: OK for your example CSV (no quoted commas)
  return line.split(',').map(v => v.trim());
}

function analyzeCsv(text) {
  const lines = text
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l.length > 0);

  if (lines.length === 0) {
    return { rows: 0, invalid: 0, missingPlayerName: 0, missingBoxNum: 0, headerError: false };
  }

  const header = parseCsvLineSimple(lines[0]);
  const idxPlayer = header.indexOf('PlayerName');
  const idxBox = header.indexOf('BoxNum');

  // If header missing required columns, treat as invalid
  if (idxPlayer === -1 || idxBox === -1) {
    return {
      rows: 0,
      invalid: Math.max(0, lines.length - 1),
      missingPlayerName: 0,
      missingBoxNum: 0,
      headerError: true
    };
  }

  let rows = 0;
  let missingPlayerName = 0;
  let missingBoxNum = 0;

  for (let i = 1; i < lines.length; i++) {
    const cols = parseCsvLineSimple(lines[i]);

    // Count as a data row if it has at least one non-empty value
    const hasAnyData = cols.some(c => c !== '');
    if (!hasAnyData) continue;

    rows++;

    const player = (cols[idxPlayer] ?? '').trim();
    const box = (cols[idxBox] ?? '').trim();

    if (!player) missingPlayerName++;
    if (!box) missingBoxNum++;
  }

  const invalid = missingPlayerName + missingBoxNum;
  return { rows, invalid, missingPlayerName, missingBoxNum, headerError: false };
}

// Base64 CSV data used by bulkUpload()
window.b64CSV = null;

(function initBulkUploadUI() {
  const fileInput = document.getElementById('csvInput');
  const uploadBtn = document.getElementById('bulk-add');
  const csvMeta = document.getElementById('csvMeta');

  if (!fileInput || !uploadBtn) return;

  // Tracks whether the currently selected CSV fails required-field checks
  let hasRequiredErrors = false;

  // initial UI state
  uploadBtn.disabled = true;
  if (csvMeta) csvMeta.textContent = '';

  // Avoid attaching multiple listeners if script is included twice
  if (fileInput.dataset.listenerAttached === "true") return;
  fileInput.dataset.listenerAttached = "true";

  fileInput.addEventListener('change', async (event) => {
    const file = event.target.files?.[0];

    // Reset state
    window.b64CSV = null;
    hasRequiredErrors = false;
    uploadBtn.disabled = true;
    uploadBtn.title = '';
    if (csvMeta) csvMeta.textContent = '';

    if (!file) return;

    // 1) Analyze CSV (row count + required fields)
    try {
      const text = await file.text();
      const info = analyzeCsv(text);

      hasRequiredErrors = !!(info.headerError || info.missingPlayerName || info.missingBoxNum);

      if (csvMeta) {
        if (info.headerError) {
          csvMeta.textContent = 'CSV missing PlayerName/BoxNum columns';
        } else if (hasRequiredErrors) {
          csvMeta.textContent =
            `${info.rows.toLocaleString()} rows • ` +
            `Missing PlayerName: ${info.missingPlayerName}, BoxNum: ${info.missingBoxNum}`;
        } else {
          csvMeta.textContent = `${info.rows.toLocaleString()} rows`;
        }
      }

      if (hasRequiredErrors) {
        uploadBtn.title = 'Fix missing PlayerName/BoxNum before uploading';
      }
    } catch (err) {
      console.warn('Could not read CSV for row count/validation:', err);
      hasRequiredErrors = true;
      uploadBtn.title = 'Unable to validate CSV';
      if (csvMeta) csvMeta.textContent = 'Rows: (unable to count)';
    }

    // 2) Convert CSV to base64 (your existing behavior)
    window.convertCSVToBase64(file, () => {
      // Enable only once base64 is ready AND required fields are OK
      uploadBtn.disabled = !window.b64CSV || hasRequiredErrors;
    });
  });

  // Expose for completeness
  window.convertCSVToBase64 = function convertCSVToBase64(file, onReady) {
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = String(reader.result || '');
      window.b64CSV = base64String.replace('data:text/csv;base64,', '');
      if (typeof onReady === 'function') onReady();
    };
    reader.readAsDataURL(file);
  };
})();

// Global for inline onclick="bulkUpload()"
window.bulkUpload = function bulkUpload() {
  const uploadBtn = document.getElementById('bulk-add');
  const fileInput = document.getElementById('csvInput');
  const csvMeta = document.getElementById('csvMeta');

  if (!window.b64CSV) {
    console.warn('Bulk upload blocked: no CSV loaded.');
    return;
  }

  const originalHTML = uploadBtn ? uploadBtn.innerHTML : '';
  const originalDisabled = uploadBtn ? uploadBtn.disabled : false;

  if (uploadBtn) {
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = `
      <span class="spinner-border spinner-border-sm mr-2" role="status" aria-hidden="true"></span>
      Uploading…
    `;
  }

  fetch('https://api.us175.com/demo-bulk-upload-inventory', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ CSVFile: window.b64CSV })
  })
    .then(r => r.json())
    .then(res => {
      const statusCode = res.StatusCode;
      console.log('Bulk upload response:', res);

      if (statusCode == '200') {
        console.log('Bulk load success');

        // Reset input + state
        window.b64CSV = null;
        if (fileInput) fileInput.value = '';
        if (csvMeta) csvMeta.textContent = '';
      } else {
        console.log('Bulk load error:', statusCode);
      }
    })
    .catch(err => {
      console.error('Error:', err);
    })
    .finally(() => {
      if (uploadBtn) {
        uploadBtn.innerHTML = originalHTML; // restore icon/text
        // If success cleared b64CSV -> keep disabled; otherwise allow retry
        uploadBtn.disabled = !!(!window.b64CSV) || originalDisabled;
      }
    });
};

(function resetImportCSVOnModalClose() {
  const modalId = 'staticBackdropAddInventory';
  // If jQuery/Bootstrap 4 is present, hook into the modal lifecycle
  if (typeof window.$ === 'function') {
    $('#' + modalId).on('hidden.bs.modal', function () {
      // reset global + UI state
      window.b64CSV = null;

      const fileInput = document.getElementById('csvInput');
      if (fileInput) fileInput.value = '';

      const csvMeta = document.getElementById('csvMeta');
      if (csvMeta) csvMeta.textContent = '';

      const uploadBtn = document.getElementById('bulk-add');
      if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.title = '';
      }
    });
  } else {
    console.warn('jQuery not found; modal reset hook not installed.');
  }
})();
