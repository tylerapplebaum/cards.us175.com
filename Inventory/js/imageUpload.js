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

// --- selection state ---
const uploadState = {
  guid: "",
  frontFile: null,
  backFile: null,
  frontDataUrl: "",
  backDataUrl: "",
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
  btn.disabled = !(uploadState.guid && uploadState.frontFile && uploadState.backFile);
}

function clearUploadSelection() {
  uploadState.guid = getActiveGuidFromDetailsModal_ForUpload();
  uploadState.frontFile = null;
  uploadState.backFile = null;
  uploadState.frontDataUrl = "";
  uploadState.backDataUrl = "";

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

  // Optional strict JPEG enforcement:
  if (!isProbablyJpeg(file)) {
    setStatus("Please upload a .jpg/.jpeg image (JPEG).", true);
    return;
  }

  const dataUrl = await fileToDataUrl(file);

  const img = document.getElementById(`preview-${side}`);
  const name = document.getElementById(`name-${side}`);

  if (img) {
    img.src = dataUrl;
    img.classList.remove("d-none");
  }
  if (name) {
    name.textContent = file.name;
  }

  if (side === "front") {
    uploadState.frontFile = file;
    uploadState.frontDataUrl = dataUrl;
  } else {
    uploadState.backFile = file;
    uploadState.backDataUrl = dataUrl;
  }

  setStatus("");
  setSubmitEnabled();
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
    const frontBase64 = (uploadState.frontDataUrl.split("base64,")[1] || "");
    const backBase64  = (uploadState.backDataUrl.split("base64,")[1] || "");

    // Required names:
    const frontName = `${guid}-front.jpg`;
    const backName  = `${guid}-back.jpg`;

    // IMPORTANT:
    // I don't know your API's exact JSON schema, so this uses a common pattern.
    // Adjust field names to match your Lambda / integration if needed.
    const body = {
      guid,
      files: [
        {
        side: "front",
        originalName: uploadState.frontFile.name,
        contentType: uploadState.frontFile.type || "image/jpeg",
        dataBase64: frontBase64
        },
        {
        side: "back",
        originalName: uploadState.backFile.name,
        contentType: uploadState.backFile.type || "image/jpeg",
        dataBase64: backBase64
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
