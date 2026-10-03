// QR payloads may contain a bare GUID or an inventory URL with ?guid=… .
function parseInventoryGuid(value) {
    let guid = value.trim();
    try {
        const url = new URL(guid);
        if (url.protocol !== 'https:' && url.protocol !== 'http:') return null;
        guid = (url.searchParams.get('guid') || '').trim();
    } catch (_) {
        // A bare GUID is not a URL.
    }
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(guid)
        ? guid : null;
}

function setSearchStatus(message) {
    document.getElementById('inventorySearchStatus').textContent = message;
}

let guidScanSession = null;

async function startGuidScanner() {
    if (guidScanSession || searchtype !== 'guid') return;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        setSearchStatus('Camera scanning requires HTTPS and a browser with camera access.');
        return;
    }
    if (typeof Html5Qrcode === 'undefined') {
        setSearchStatus('The QR scanner could not load. Please reload the page.');
        return;
    }

    const button = document.getElementById('scanGuidButton');
    const panel = document.getElementById('guidScannerPanel');
    button.disabled = true;
    panel.classList.remove('d-none');
    panel.scrollIntoView({ block: 'nearest' });
    setSearchStatus('Allow camera access to scan your card.');
    const session = {
        reader: new Html5Qrcode('guidQrReader', {
            formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
            verbose: false
        }),
        cancelled: false,
        start: null,
        stop: null
    };
    guidScanSession = session;
    try {
        session.start = session.reader.start(
            { facingMode: 'environment' },
            { fps: 10 },
            async decodedText => {
                if (session.cancelled) return;
                const guid = parseInventoryGuid(decodedText);
                if (!guid) {
                    const isWebLink = /^https?:\/\//i.test(decodedText.trim());
                    setSearchStatus(isWebLink
                        ? 'This QR code contains a link without a valid GUID. Generate the QR code from the GUID itself or an inventory URL containing ?guid=… .'
                        : 'This QR code does not contain an inventory GUID. Try another code.');
                    return;
                }
                // Stop first so repeated video frames cannot submit duplicate searches.
                await stopGuidScanner();
                if (searchtype !== 'guid') return;
                document.getElementById('guidSearchInput').value = guid;
                document.getElementById('existingForm').requestSubmit();
            }
        );
        await session.start;
        if (!session.cancelled) setSearchStatus('Point the camera at the card’s QR code.');
    } catch (error) {
        if (!session.cancelled) {
            setSearchStatus('Unable to open the camera. Allow camera access and try Scan QR again.');
            console.error('QR camera error:', error);
        }
        await stopGuidScanner();
    }
}

function stopGuidScanner() {
    const session = guidScanSession;
    if (!session) return Promise.resolve();
    if (session.stop) return session.stop;
    session.cancelled = true;
    document.getElementById('guidScannerPanel').classList.add('d-none');
    session.stop = (async () => {
        // Cancellation can happen while the camera permission prompt is still open.
        try { await session.start; } catch (_) { /* No active camera on failure. */ }
        try {
            if (session.reader.isScanning) await session.reader.stop();
            session.reader.clear();
        } catch (error) {
            console.error('Unable to stop QR scanner:', error);
        } finally {
            guidScanSession = null;
            document.getElementById('scanGuidButton').disabled = false;
        }
    })();
    return session.stop;
}
