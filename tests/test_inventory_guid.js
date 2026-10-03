// Run with: node --test tests/test_inventory_guid.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const guid = '6aa476ae-65cf-405a-ba0a-8a088dd136f8';

function setup(startCamera = () => Promise.resolve()) {
    const elements = {};
    const listeners = {};
    let submits = 0;
    let reader;
    const getElement = id => elements[id] ||= {
        value: '', disabled: false, required: false, textContent: '',
        classList: {
            values: new Set(),
            add(c) { this.values.add(c); },
            remove(c) { this.values.delete(c); },
            contains(c) { return this.values.has(c); },
            toggle(c, on) { on ? this.add(c) : this.remove(c); }
        },
        focus() {}, scrollIntoView() {}, addEventListener() {},
        requestSubmit() { submits++; }
    };
    const context = vm.createContext({
        URL, console: { log() {}, error() {} },
        window: { isSecureContext: true, addEventListener() {} },
        navigator: { mediaDevices: { getUserMedia() {} } },
        document: { getElementById: getElement, addEventListener(n, f) { listeners[n] = f; } },
        Html5QrcodeSupportedFormats: { QR_CODE: 0 },
        Html5Qrcode: class {
            constructor() { reader = this; this.stops = 0; }
            async start(camera, options, callback) {
                this.decode = callback;
                await startCamera();
                this.isScanning = true;
            }
            async stop() { this.stops++; this.isScanning = false; }
            clear() {}
        }
    });
    for (const name of ['guidscanner', 'searchandfilter']) {
        vm.runInContext(fs.readFileSync(path.join(root, `Inventory/js/${name}.js`), 'utf8'), context);
    }
    listeners.DOMContentLoaded();
    const run = code => vm.runInContext(code, context);
    return { context, run, getElement, reader: () => reader, submits: () => submits };
}

function guidMode(app) {
    app.run('toggleSetPlayerBox(); toggleSetPlayerBox(); toggleSetPlayerBox();');
}

test('toggle cycles through GUID and resets fields and visibility', () => {
    const app = setup();
    app.getElement('setSearchList').value = 'old set';
    guidMode(app);
    assert.equal(app.run('searchtype'), 'guid');
    assert.equal(app.getElement('setSearchList').value, '');
    assert.equal(app.getElement('guidSearchInput').disabled, false);
    assert.equal(app.getElement('scanGuidButton').classList.contains('d-none'), false);
    app.run('toggleSetPlayerBox()');
    assert.equal(app.run('searchtype'), 'set');
    assert.equal(app.getElement('guidSearchInput').disabled, true);
    assert.equal(app.getElement('queryYear').classList.contains('d-none'), false);
});

test('QR payload accepts GUID or URL, rejecting unrelated content', () => {
    const app = setup();
    assert.equal(app.context.parseInventoryGuid(` ${guid}\n`), guid);
    assert.equal(app.context.parseInventoryGuid(`https://test.us175.com/Inventory/?guid=${guid}`), guid);
    for (const input of ['', 'not a guid', 'https://example.com/', `javascript:${guid}`]) {
        assert.equal(app.context.parseInventoryGuid(input), null);
    }
});

test('scan fills GUID, submits once, and stops camera', async () => {
    const app = setup(); guidMode(app);
    await app.run('startGuidScanner()');
    await app.reader().decode('invalid');
    assert.equal(app.submits(), 0);
    await Promise.all([app.reader().decode(guid), app.reader().decode(guid)]);
    assert.equal(app.getElement('guidSearchInput').value, guid);
    assert.equal(app.submits(), 1);
    assert.equal(app.reader().stops, 1);
});

test('cancel during camera startup releases camera without submitting', async () => {
    let allowCamera;
    const app = setup(() => new Promise(resolve => { allowCamera = resolve; }));
    guidMode(app);
    const starting = app.run('startGuidScanner()');
    const stopping = app.run('stopGuidScanner()');
    allowCamera();
    await Promise.all([starting, stopping]);
    await app.reader().decode(guid);
    assert.equal(app.reader().stops, 1);
    assert.equal(app.submits(), 0);
    assert.equal(app.getElement('scanGuidButton').disabled, false);
});

test('camera permission failure allows retry', async () => {
    const app = setup(() => Promise.reject(new Error('Permission denied')));
    guidMode(app);
    await app.run('startGuidScanner()');
    assert.match(app.getElement('inventorySearchStatus').textContent, /Unable to open/);
    assert.equal(app.getElement('scanGuidButton').disabled, false);
    assert.equal(app.run('guidScanSession'), null);
});

test('GUID form sends exact request and renders empty results', async () => {
    const app = setup(); guidMode(app);
    const html = fs.readFileSync(path.join(root, 'Inventory/index.html'), 'utf8');
    const functionCode = html.slice(html.indexOf('    function fetchItems()'), html.indexOf('    // Add Inventory button helper'));
    vm.runInContext(functionCode, app.context);
    let payload;
    app.context.fetch = async (url, options) => {
        payload = JSON.parse(options.body);
        return { json: async () => ({ StatusCode: 200, body: [] }) };
    };
    app.context.populateTable = () => {};
    app.getElement('guidSearchInput').value = guid;
    app.getElement('setSearchList').value = 'stale set';
    await app.run('fetchItems()');
    assert.deepEqual(payload, { guid, SearchType: 'guid' });
    assert.equal(app.getElement('num-results').textContent, 0);
    assert.match(app.getElement('inventorySearchStatus').textContent, /No matching/);
});


test('generator short links explain the missing GUID; direct replacement scans successfully', async () => {
    const app = setup(); guidMode(app);
    await app.run('startGuidScanner()');
    // Exact payload decoded from the reported qr.png.
    await app.reader().decode('https://qr.generatorqr.com/AQzD27U0s');
    assert.equal(app.submits(), 0);
    assert.match(app.getElement('inventorySearchStatus').textContent, /link without a valid GUID/);
    assert.equal(app.reader().isScanning, true);
    const replacementGuid = '19e54c58-b355-4e9b-baa7-5e179fc2946b';
    await app.reader().decode(replacementGuid);
    assert.equal(app.getElement('guidSearchInput').value, replacementGuid);
    assert.equal(app.submits(), 1);
    assert.equal(app.reader().stops, 1);
});
