(function (root) {
    'use strict';

    // Measured from templates/AveryPresta94102-template.pdf, in PDF points.
    const layout = Object.freeze({
        width: 612, height: 792, columns: 8, rows: 10,
        left: 27, top: 45, pitch: 72, labelSize: 54, qrSize: 50.4
    });
    const guidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    function collectVisibleItems(table) {
        const seen = new Set();
        return Array.from(table.querySelectorAll('tbody tr[data-guid]'))
            .filter(row => !row.hidden && row.getClientRects().length > 0 &&
                getComputedStyle(row).visibility !== 'hidden')
            .map(row => ({
                guid: row.dataset.guid.trim(),
                description: ['column1', 'column2', 'column4', 'column5']
                    .map(column => row.querySelector(`.${column}`)?.textContent.trim())
                    .filter(Boolean).join(' · ')
            }))
            .filter(item => {
                if (seen.has(item.guid)) return false;
                seen.add(item.guid);
                return true;
            });
    }

    function planLabels(items, startLabel = 1) {
        if (!Number.isInteger(startLabel) || startLabel < 1 || startLabel > 80) {
            throw new Error('Starting label must be a whole number from 1 to 80.');
        }
        if (!items.length) throw new Error('No visible results to label. Search inventory or adjust the filter first.');
        return items.map((item, index) => {
            if (!guidPattern.test(item.guid)) {
                throw new Error(`Result ${index + 1} has an invalid GUID. No labels were generated.`);
            }
            const position = startLabel - 1 + index;
            const slot = position % 80;
            return {
                ...item, page: Math.floor(position / 80), slot,
                x: layout.left + (slot % layout.columns) * layout.pitch,
                top: layout.top + Math.floor(slot / layout.columns) * layout.pitch
            };
        });
    }

    function makeQr(guid) {
        const qr = root.qrcode(0, 'M');
        qr.addData(guid, 'Byte'); // Preserve the exact DynamoDB key, without a URL or redirect.
        qr.make();
        return qr;
    }

    async function buildPdf(labels, templateBytes, showGuides = false) {
        const { PDFDocument, rgb } = root.PDFLib;
        const source = await PDFDocument.load(templateBytes);
        const template = source.getPage(0);
        if (source.getPageCount() !== 1 || template.getWidth() !== layout.width || template.getHeight() !== layout.height) {
            throw new Error('The label template must be the original Letter-size Avery 94102 PDF.');
        }
        const pdf = await PDFDocument.create();
        pdf.setTitle('Inventory GUID labels — Avery 94102');
        const pageCount = labels[labels.length - 1].page + 1;
        const pages = [];
        for (let i = 0; i < pageCount; i++) {
            const [page] = await pdf.copyPages(source, [0]);
            pdf.addPage(page);
            // Keep outlines available for alignment proofs, but omit them on adhesive labels.
            if (!showGuides) page.drawRectangle({
                x: 0, y: 0, width: layout.width, height: layout.height, color: rgb(1, 1, 1)
            });
            pages.push(page);
        }
        for (const [index, label] of labels.entries()) {
            const qr = makeQr(label.guid);
            const count = qr.getModuleCount();
            const quietZone = 4;
            const unit = layout.qrSize / (count + quietZone * 2);
            const inset = (layout.labelSize - layout.qrSize) / 2;
            const x = label.x + inset + quietZone * unit;
            const top = label.top + inset + quietZone * unit;
            // Vector modules stay sharp at any printer resolution. Merge horizontal runs.
            for (let row = 0; row < count; row++) {
                for (let col = 0; col < count;) {
                    if (!qr.isDark(row, col)) { col++; continue; }
                    const start = col;
                    while (col < count && qr.isDark(row, col)) col++;
                    pages[label.page].drawRectangle({
                        x: x + start * unit,
                        y: layout.height - top - (row + 1) * unit,
                        width: (col - start) * unit, height: unit, color: rgb(0, 0, 0)
                    });
                }
            }
            if (index % 80 === 79) await new Promise(resolve => setTimeout(resolve, 0));
        }
        return pdf.save();
    }

    function init() {
        const button = document.getElementById('generateQrLabels');
        if (!button) return;
        const status = document.getElementById('qrLabelStatus');
        const download = document.getElementById('qrLabelDownload');
        const preview = document.getElementById('qrLabelPreview');
        const details = document.getElementById('qrLabelPreviewDetails');
        let downloadUrl;
        button.addEventListener('click', async () => {
            button.disabled = true;
            download.classList.add('d-none');
            details.classList.add('d-none');
            preview.replaceChildren();
            if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
            try {
                const items = collectVisibleItems(document.getElementById('itemsTable'));
                const labels = planLabels(items, Number(document.getElementById('qrLabelStart').value));
                status.textContent = `Generating ${labels.length} QR labels…`;
                const response = await fetch('templates/AveryPresta94102-template.pdf');
                if (!response.ok) throw new Error('Unable to load the Avery template. Please try again.');
                const bytes = await buildPdf(labels, await response.arrayBuffer(), document.getElementById('qrLabelGuides').checked);
                downloadUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
                download.href = downloadUrl;
                download.download = 'inventory-guid-labels-avery-94102.pdf';
                download.classList.remove('d-none');
                const fragment = document.createDocumentFragment();
                for (const label of labels) {
                    const card = document.createElement('figure');
                    card.className = 'qr-label-preview-item';
                    const image = document.createElement('img');
                    image.width = image.height = 75;
                    image.alt = `QR code for ${label.guid}`;
                    image.loading = 'lazy';
                    image.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(makeQr(label.guid).createSvgTag(2, 8));
                    const caption = document.createElement('figcaption');
                    caption.textContent = `Sheet ${label.page + 1}, label ${label.slot + 1}: ${label.description || label.guid}`;
                    const key = document.createElement('small');
                    key.textContent = label.guid;
                    card.append(image, caption, key);
                    fragment.appendChild(card);
                }
                preview.appendChild(fragment);
                details.classList.remove('d-none');
                const sheets = labels[labels.length - 1].page + 1;
                status.textContent = `${labels.length} labels on ${sheets} sheet${sheets === 1 ? '' : 's'}, ready to download. Regenerate after changing results or label options.`;
            } catch (error) {
                console.error('QR label generation failed:', error);
                status.textContent = error.message || 'Unable to generate QR labels. Please try again.';
            } finally {
                button.disabled = false;
            }
        });
    }

    root.InventoryQrLabels = { layout, collectVisibleItems, planLabels, makeQr, buildPdf };
    if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', init);
})(typeof window !== 'undefined' ? window : globalThis);
