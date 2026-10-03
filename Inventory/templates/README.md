# Inventory label templates

The footer's **Generate QR codes** utility uses `AveryPresta94102-template.pdf`
to create a downloadable PDF entirely in the browser. The original PDF and DOC
are unchanged. The PDF contains outlines, not fillable form fields.

Measured PDF geometry (points; 72 points = 1 inch):

- Letter page: 612 × 792.
- 8 columns × 10 rows; 80 labels per page.
- Each label: 54 × 54 (¾-inch square).
- First label's upper-left corner: 27 points from the left, 45 from the top.
- Horizontal and vertical pitch: 72 points.

`Inventory/js/qrlabels.js` places vector QR codes at these coordinates. Codes
are 50.4 points (0.70 inches) square including a four-module white quiet zone,
centered inside each label. Screen previews are 75 × 75 CSS pixels. Each QR
encodes the exact item's GUID as text, without redirects or external services.

Only visible table rows are included, in display order, once per GUID rather
than once per quantity. A starting label from 1–80 supports partially used
sheets. Extra labels continue on new pages, starting at label 1. The preview
identifies the item, sheet, and slot; identifying text is not printed on these
small labels.

Print the downloaded PDF on Letter paper at **Actual size / 100%**, not Fit.
Use the optional template outlines on plain paper to check alignment before
printing on adhesive labels. Regenerate after changing results or options.

If replacing the template with a different label layout, update the measured
geometry in `qrlabels.js` and the layout tests as well.
