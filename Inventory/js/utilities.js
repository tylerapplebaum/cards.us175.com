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

function generateUUID(inputId) {
    document.getElementById(inputId).value = crypto.randomUUID();
}