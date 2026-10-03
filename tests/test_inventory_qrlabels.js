// Run with: node --test tests/test_inventory_qrlabels.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const root = path.join(__dirname, '..');
global.qrcode = require('../vendor/qrcode-generator/qrcode.js');
global.PDFLib = require('../vendor/pdf-lib/pdf-lib.min.js');
require('../Inventory/js/qrlabels.js');
const { planLabels, buildPdf, collectVisibleItems } = global.InventoryQrLabels;
const guid = '19e54c58-b355-4e9b-baa7-5e179fc2946b';

test('visible selection follows row order and excludes filtered/deleted/duplicate results', () => {
    global.getComputedStyle = row => ({ visibility: row.visibility || 'visible' });
    const row = (guid, visible = true) => ({
        dataset: { guid }, getClientRects: () => visible ? [{}] : [],
        querySelector: () => ({ textContent: 'Card' })
    });
    const other = randomUUID();
    const table = { querySelectorAll: () => [row(other), row(randomUUID(), false), row(guid), row(guid)] };
    assert.deepEqual(collectVisibleItems(table).map(item => item.guid), [other, guid]);
});

test('layout matches template corners and adds pages without spilling', () => {
    const labels = planLabels(Array.from({ length: 81 }, () => ({ guid: randomUUID() })));
    assert.deepEqual([labels[0].x, labels[0].top, labels[0].page], [27, 45, 0]);
    assert.deepEqual([labels[79].x, labels[79].top, labels[79].page], [531, 693, 0]);
    assert.deepEqual([labels[80].x, labels[80].top, labels[80].page], [27, 45, 1]);
    const partial = planLabels([{ guid }, { guid }], 80);
    assert.equal(partial[0].slot, 79);
    assert.equal(partial[1].slot, 0);
    assert.equal(partial[1].page, 1);
});

test('empty results, invalid keys, and invalid start positions fail before PDF generation', () => {
    assert.throws(() => planLabels([]), /No visible/);
    assert.throws(() => planLabels([{ guid: 'https://qr.generatorqr.com/AQzD27U0s' }]), /invalid GUID/);
    for (const start of [0, 81, 1.5, NaN]) assert.throws(() => planLabels([{ guid }], start), /Starting label/);
});

test('real QR/PDF libraries produce multi-page Letter PDFs using the supplied template', async () => {
    const items = Array.from({ length: 81 }, (_, index) => ({ guid: index ? randomUUID() : guid }));
    const labels = planLabels(items);
    const template = fs.readFileSync(path.join(root, 'Inventory/templates/AveryPresta94102-template.pdf'));
    const bytes = await buildPdf(labels, template);
    const pdf = await PDFLib.PDFDocument.load(bytes);
    assert.equal(pdf.getPageCount(), 2);
    for (const page of pdf.getPages()) assert.deepEqual(page.getSize(), { width: 612, height: 792 });
    // Retain a raster-decode fixture outside the repository for independent verification.
    fs.writeFileSync('/tmp/inventory-qr-labels-test.pdf', bytes);
    fs.writeFileSync('/tmp/inventory-qr-labels-test.json', JSON.stringify(labels));
    const proof = await buildPdf(planLabels([{ guid }], 80), template, true);
    assert.equal((await PDFLib.PDFDocument.load(proof)).getPageCount(), 1);
    fs.writeFileSync('/tmp/inventory-qr-labels-proof.pdf', proof);
});
