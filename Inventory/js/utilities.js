// ---- utilities ----

function sanitize(value) {
    if (value == null) return '';

    return String(value)
    .replace(/\s+/g, ' ')   // collapse tabs/newlines to single space
    .trim()                 // remove leading/trailing whitespace
    .replace(/^undefined$/i, '');    
}

function sanitizeValue(value) {
    if (value === undefined || value === null || value === 'undefined') {
    return '';
    }
    return String(value).trim();
}

function formatMoney(value) {
    const n = parseFloat(value);
    return isNaN(n)
    ? ''
    : n.toLocaleString(undefined, {
        style: 'currency',
        currency: 'USD'
        });
}

const TXN_STORAGE_KEY = 'inventoryStoredTxnId';

function getStoredTxnId() {
    try {
        return sanitize(window.sessionStorage.getItem(TXN_STORAGE_KEY));
    } catch (err) {
        console.warn('Could not read stored transaction ID:', err);
        return '';
    }
}

function setStoredTxnId(value) {
    const txnId = sanitize(value);

    try {
        if (txnId) {
            window.sessionStorage.setItem(TXN_STORAGE_KEY, txnId);
        } else {
            window.sessionStorage.removeItem(TXN_STORAGE_KEY);
        }
    } catch (err) {
        console.warn('Could not store transaction ID:', err);
    }

    renderStoredTxnIdStatus();
    return txnId;
}

function formatStoredTxnIdLabel(value) {
    const txnId = sanitize(value);
    if (!txnId) return 'Stored ID: none';
    return `Stored ID: ${txnId}`;
}

function renderStoredTxnIdStatus() {
    const storedTxnId = getStoredTxnId();

    document.querySelectorAll('[data-txn-storage-status]').forEach((el) => {
        el.textContent = formatStoredTxnIdLabel(storedTxnId);
    });
}

function storeTxnIdFromInput(inputId) {
    const input = document.getElementById(inputId);
    const txnId = sanitize(input?.value);

    if (!txnId) {
        console.warn('No transaction ID available to store.');
        return;
    }

    setStoredTxnId(txnId);
}

function applyStoredTxnIdToInput(inputId) {
    const storedTxnId = getStoredTxnId();
    const input = document.getElementById(inputId);

    if (!input) return;
    if (!storedTxnId) {
        console.warn('No stored transaction ID available.');
        renderStoredTxnIdStatus();
        return;
    }

    input.value = storedTxnId;
    renderStoredTxnIdStatus();
}

function clearStoredTxnId() {
    setStoredTxnId('');
}

function generateUUID(inputId) {
    document.getElementById(inputId).value = crypto.randomUUID();
}

document.addEventListener('DOMContentLoaded', renderStoredTxnIdStatus);
