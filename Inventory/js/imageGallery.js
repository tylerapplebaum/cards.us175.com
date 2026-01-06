// imageGallery.js

// Track whether we hid the details modal to open the gallery
let reopenDetailsAfterGallery = false;

function getActiveGuidFromDetailsModal() {
  // Prefer your activeGuid global if set, else read the field value
  const guidFromGlobal =
    (typeof activeGuid !== "undefined" && activeGuid) ? String(activeGuid).trim() : "";
  if (guidFromGlobal) return guidFromGlobal;

  const el = document.getElementById("modal-guid");
  return (el && el.value ? el.value : "").trim();
}

function openImageGalleryFromDetails() {
  const guid = getActiveGuidFromDetailsModal();
  openImageGallery(guid);
}

function openImageGallery(guid) {
  const g = String(guid || "").trim();
  const statusEl = document.getElementById("imageGalleryStatus");
  const frontImg = document.getElementById("gallery-front");
  const backImg  = document.getElementById("gallery-back");

  if (!g) {
    if (statusEl) statusEl.textContent = "No GUID found for this item.";
    if (frontImg) frontImg.removeAttribute("src");
    if (backImg) backImg.removeAttribute("src");
    $("#imageGallery").modal("show");
    return;
  }

  const frontUrl = `../test-gallery/${encodeURIComponent(g)}-front.jpg`;
  const backUrl  = `../test-gallery/${encodeURIComponent(g)}-back.jpg`;

  if (statusEl) statusEl.textContent = `GUID: ${g}`;

  // Reset carousel to first slide every open
  $("#galleryCarousel").carousel(0);

  const attachErrorHandler = (imgEl, label) => {
    if (!imgEl) return;
    imgEl.onerror = () => {
      imgEl.onerror = null; // prevent loops
      imgEl.src = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=";
      if (statusEl) {
        const prev = statusEl.textContent ? statusEl.textContent + "  " : "";
        statusEl.textContent = `${prev}${label} image not found.`;
      }
    };
  };

  attachErrorHandler(frontImg, "Front");
  attachErrorHandler(backImg, "Back");

  if (frontImg) frontImg.src = frontUrl;
  if (backImg) backImg.src = backUrl;

  // Avoid stacking modals
  reopenDetailsAfterGallery = $("#staticBackdrop").hasClass("show");
  if (reopenDetailsAfterGallery) {
    $("#staticBackdrop").one("hidden.bs.modal", () => {
      $("#imageGallery").modal("show");
    });
    $("#staticBackdrop").modal("hide");
  } else {
    $("#imageGallery").modal("show");
  }
}

// Ensure handler is attached even if script loads before the modal exists
$(document).on("hidden.bs.modal", "#imageGallery", function () {
  if (reopenDetailsAfterGallery) {
    reopenDetailsAfterGallery = false;
    $("#staticBackdrop").modal("show");
  }
});

// Optional: expose functions if you're using modules/bundlers later
window.openImageGalleryFromDetails = openImageGalleryFromDetails;
window.openImageGallery = openImageGallery;
