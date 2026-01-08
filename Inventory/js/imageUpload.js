// js/imageUpload.js
//
// Uploads two images (front/back) for the active item guid.
// Uses the same guid resolution strategy as imageGallery.js: activeGuid -> #modal-guid
// and avoids stacking modals (hides Item Details first, reopens after close).

let reopenDetailsAfterUpload = false;

function getActiveGuidFromDetailsModal_ForUpload() {
  const guidFromGlobal =
    (typeof activeGuid !== "undefined" && activeGuid) ? String(activeGuid).trim() : "";
  if (guidFromGlobal) return guidFromGlobal;

  const el = document.getElementById("modal-guid");
  return (el && el.value ? el.value : "").trim();
}

function openImageUploadFromDetails() {
  const guid = getActiveGuidFromDetailsModal_ForUpload();
  openImageUpload(guid);
}

function openImageUpload(guid) {
  const g = String(guid || "").trim();

  // update labels
  const guidLabel = document.getElementById("imageUploadGuidLabel");
  const statusEl = document.getElementById("imageUploadStatus");
  const reqFront = document.getElementById("req-front");
  const reqBack = document.getElementById("req-back");

  if (guidLabel) guidLabel.textContent = `GUID: ${g || "(not set)"}`;
  if (reqFront) reqFront.textContent = `${g || "(guid)"}-front.jpg`;
  if (reqBack) reqBack.textContent = `${g || "(guid)"}-back.jpg`;
  if (statusEl) statusEl.textContent = "";

  // reset any previous selection each open (optional; comment out if you want persistence)
  clearUploadSelection();

  // Avoid stacking modals
  reopenDetailsAfterUpload = $("#staticBackdrop").hasClass("show");
  if (reopenDetailsAfterUpload) {
    $("#staticBackdrop").one("hidden.bs.modal", () => {
      $("#imageUpload").modal("show");
    });
    $("#staticBackdrop").modal("hide");
  } else {
    $("#imageUpload").modal("show");
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read blob"));
    reader.onload = () => resolve(String(reader.result || ""));
    reader.readAsDataURL(blob);
  });
}

// Returns { blob, contentType, dataUrl, width, height, bytes }
async function optimizeToWebP(file, {
  maxDim = 2200,       // good default for card photos
  quality = 0.80,      // 0..1 (lower => smaller)
  forceSRGB = true,    // keeps colors sane across browsers
} = {}) {
  // Decode
  const bitmap = await createImageBitmap(file);

  // Compute scale
  const w0 = bitmap.width;
  const h0 = bitmap.height;
  const scale = Math.min(1, maxDim / Math.max(w0, h0));
  const w = Math.max(1, Math.round(w0 * scale));
  const h = Math.max(1, Math.round(h0 * scale));

  // Draw to canvas
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;

  const ctx = canvas.getContext("2d", { alpha: false, colorSpace: forceSRGB ? "srgb" : undefined });
  ctx.drawImage(bitmap, 0, 0, w, h);

  // Encode WebP
  const blob = await new Promise((resolve) => {
    canvas.toBlob(
      (b) => resolve(b),
      "image/webp",
      quality
    );
  });

  if (!blob) throw new Error("WebP conversion failed (canvas.toBlob returned null)");

  const dataUrl = await blobToDataUrl(blob);

  return {
    blob,
    contentType: "image/webp",
    dataUrl,
    width: w,
    height: h,
    bytes: blob.size,
  };
}

// Base64 payload without "data:...;base64," prefix
function dataUrlToBase64(dataUrl) {
  return (String(dataUrl).split("base64,")[1] || "");
}

// Rough estimate of JSON payload bytes (base64 expands ~4/3)
function estimateJsonPayloadBytes(frontB64Len, backB64Len) {
  // base64 length approximates bytes; JSON adds overhead, so pad a bit
  const base64Bytes = frontB64Len + backB64Len;
  return Math.round(base64Bytes * 1.05); // small cushion for JSON keys etc
}

// --- selection state ---
const uploadState = {
  guid: "",
  frontFile: null,          // original file (optional; keep)
  backFile: null,
  frontOptimized: null,     // { blob, contentType, dataUrl, bytes, width, height }
  backOptimized: null,
};

function setStatus(msg, isError = false) {
  const el = document.getElementById("imageUploadStatus");
  if (!el) return;
  el.className = isError ? "small text-danger" : "small text-muted";
  el.textContent = msg || "";
}

function setSubmitEnabled() {
  const btn = document.getElementById("imageUploadSubmitBtn");
  if (!btn) return;
  btn.disabled = !(uploadState.guid && uploadState.frontOptimized && uploadState.backOptimized);
}

function clearUploadSelection() {
  uploadState.guid = getActiveGuidFromDetailsModal_ForUpload();
  uploadState.frontFile = null;
  uploadState.backFile = null;
  uploadState.frontOptimized = null;
  uploadState.backOptimized = null;

  // reset UI
  for (const side of ["front", "back"]) {
    const img = document.getElementById(`preview-${side}`);
    const name = document.getElementById(`name-${side}`);
    const input = document.getElementById(`file-${side}`);
    if (img) { img.src = ""; img.classList.add("d-none"); }
    if (name) name.textContent = "";
    if (input) input.value = "";
  }

  setStatus("");
  setSubmitEnabled();
}

function isProbablyJpeg(file) {
  // Your system requires .jpg names; if your backend truly requires JPEG bytes,
  // enforce it here. If backend accepts any image bytes but uses the name, relax this.
  return file && (file.type === "image/jpeg" || file.name.toLowerCase().endsWith(".jpg") || file.name.toLowerCase().endsWith(".jpeg"));
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.onload = () => resolve(String(reader.result || ""));
    reader.readAsDataURL(file);
  });
}

async function handlePickedFile(side, file) {
  uploadState.guid = getActiveGuidFromDetailsModal_ForUpload();
  if (!uploadState.guid) {
    setStatus("No GUID found for this item.", true);
    return;
  }
  if (!file) return;

  setStatus(`Optimizing ${side} image...`);

  try {
    // Convert to WebP + downscale
    const optimized = await optimizeToWebP(file, {
      maxDim: 2200,
      quality: 0.80
    });

    const img = document.getElementById(`preview-${side}`);
    const name = document.getElementById(`name-${side}`);

    if (img) {
      img.src = optimized.dataUrl;
      img.classList.remove("d-none");
    }
    if (name) {
      const kb = Math.round(optimized.bytes / 1024);
      name.textContent = `${file.name} → webp (${optimized.width}×${optimized.height}, ${kb} KB)`;
    }

    if (side === "front") {
      uploadState.frontFile = file;
      uploadState.frontOptimized = optimized;
    } else {
      uploadState.backFile = file;
      uploadState.backOptimized = optimized;
    }

    setStatus("");
    setSubmitEnabled();
  } catch (e) {
    console.error(e);
    setStatus(`Could not optimize ${side} image.`, true);
  }
}

function wireDropZone(side) {
  const drop = document.getElementById(`drop-${side}`);
  const input = document.getElementById(`file-${side}`);
  if (!drop || !input) return;

  // click-to-choose
  drop.addEventListener("click", () => input.click());
  input.addEventListener("change", async () => {
    const file = input.files && input.files[0];
    try {
      await handlePickedFile(side, file);
    } catch (e) {
      console.error(e);
      setStatus("Could not load image.", true);
    }
  });

  // drag/drop
  const prevent = (e) => { e.preventDefault(); e.stopPropagation(); };

  ["dragenter", "dragover", "dragleave", "drop"].forEach(evt =>
    drop.addEventListener(evt, prevent)
  );

  drop.addEventListener("dragover", () => drop.classList.add("border-primary"));
  drop.addEventListener("dragleave", () => drop.classList.remove("border-primary"));
  drop.addEventListener("drop", async (e) => {
    drop.classList.remove("border-primary");
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    try {
      await handlePickedFile(side, file);
    } catch (err) {
      console.error(err);
      setStatus("Could not load dropped image.", true);
    }
  });
}

async function uploadImages() {
  uploadState.guid = getActiveGuidFromDetailsModal_ForUpload();
  const guid = uploadState.guid;

  if (!guid) {
    setStatus("No GUID found for this item.", true);
    return;
  }
  if (!uploadState.frontFile || !uploadState.backFile) {
    setStatus("Please select both front and back images.", true);
    return;
  }

  const btn = document.getElementById("imageUploadSubmitBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Uploading..."; }

  try {
    // Extract base64 payload from data URLs
    // dataUrl format: "data:image/jpeg;base64,AAAA..."
    const frontB64 = dataUrlToBase64(uploadState.frontOptimized.dataUrl);
    const backB64  = dataUrlToBase64(uploadState.backOptimized.dataUrl);

    // Safety check for HTTP API limit (10MB). Keep margin for headers/etc.
    const est = estimateJsonPayloadBytes(frontB64.length, backB64.length);
    const limit = 10 * 1024 * 1024; // 10MB
    if (est > limit) {
      setStatus("Optimized images are still too large for the 10MB API limit. Try lowering quality or max dimension.", true);
      return;
    }

    const body = {
      guid,
      files: [
        {
          side: "front",
          originalName: uploadState.frontFile?.name || "",
          contentType: "image/webp",
          dataBase64: frontB64
        },
        {
          side: "back",
          originalName: uploadState.backFile?.name || "",
          contentType: "image/webp",
          dataBase64: backB64
        }
      ]
    };

    const res = await fetch("https://api.us175.com/demo-inventory-img-upload", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const text = await res.text();
    let parsed = null;
    try { parsed = JSON.parse(text); } catch (_) {}

    if (!res.ok) {
      console.error("Upload failed:", res.status, parsed || text);
      setStatus(`Upload failed (HTTP ${res.status}).`, true);
      return;
    }

    setStatus("Upload successful.");
    // optional: close modal automatically
    // $("#imageUpload").modal("hide");
  } catch (err) {
    console.error(err);
    setStatus("Upload failed due to a network or parsing error.", true);
  } finally {
    if (btn) { btn.textContent = "Upload"; }
    setSubmitEnabled();
  }
}

// Reopen Item Details when upload modal closes (mirrors gallery behavior)
$(document).on("hidden.bs.modal", "#imageUpload", function () {
  if (reopenDetailsAfterUpload) {
    reopenDetailsAfterUpload = false;
    $("#staticBackdrop").modal("show");
  }
});

// Wire up after DOM is ready (works even though modal is loaded via partial)
let imageUploadInitialized = false;

function initImageUploadModal() {
  if (imageUploadInitialized) return;
  imageUploadInitialized = true;

  wireDropZone("front");
  wireDropZone("back");

  document.getElementById("imageUploadClearBtn")?.addEventListener("click", clearUploadSelection);
  document.getElementById("imageUploadSubmitBtn")?.addEventListener("click", uploadImages);

  // When modal opens, refresh GUID label + required filenames
  $(document).on("shown.bs.modal", "#imageUpload", function () {
    const guid = getActiveGuidFromDetailsModal_ForUpload();
    uploadState.guid = guid;
    document.getElementById("imageUploadGuidLabel").textContent = `GUID: ${guid || "(not set)"}`;
    document.getElementById("req-front").textContent = `${guid || "(guid)"}-front.jpg`;
    document.getElementById("req-back").textContent  = `${guid || "(guid)"}-back.jpg`;
    setSubmitEnabled();
  });
}

// expose init globally so loadPartial callback can call it
window.initImageUploadModal = initImageUploadModal;


// expose functions globally
window.openImageUploadFromDetails = openImageUploadFromDetails;
window.openImageUpload = openImageUpload;
