let reopenDetailsAfterEbaySales = false;
let currentEbaySalesGuid = "";

function getGuidFromTriggerElementForEbaySales(triggerEl) {
  const rowGuid = triggerEl?.closest?.("tr")?.dataset?.guid;
  return String(rowGuid || "").trim();
}

function getActiveGuidFromDetailsModalForEbaySales() {
  if (currentEbaySalesGuid) return currentEbaySalesGuid;

  const guidFromGlobal =
    (typeof activeGuid !== "undefined" && activeGuid) ? String(activeGuid).trim() : "";
  if (guidFromGlobal) return guidFromGlobal;

  const el = document.getElementById("modal-guid");
  return (el && el.value ? el.value : "").trim();
}

function setEbaySalesStatus(message, isError = false) {
  const el = document.getElementById("eBaySalesStatus");
  if (!el) return;
  el.className = isError ? "small text-danger mr-auto" : "small text-muted mr-auto";
  el.textContent = message || "";
}

function setEbaySalesResponse(value) {
  const el = document.getElementById("eBaySalesResponse");
  if (!el) return;
  el.value = value || "";
}

function updateStartingBidState() {
  const listingTypeEl = document.getElementById("eBaySalesListingType");
  const startingBidEl = document.getElementById("eBaySalesStartingBid");
  if (!listingTypeEl || !startingBidEl) return;

  const isAuction = listingTypeEl.value === "AUCTION";
  startingBidEl.disabled = !isAuction;
  startingBidEl.required = isAuction;

  if (!isAuction) startingBidEl.value = "";
}

function resetEbaySalesForm(guid) {
  currentEbaySalesGuid = String(guid || "").trim();

  const guidEl = document.getElementById("eBaySalesGuid");
  const listingTypeEl = document.getElementById("eBaySalesListingType");
  const allowOffersEl = document.getElementById("eBaySalesAllowOffers");
  const autographedEl = document.getElementById("eBaySalesAutographed");
  const teamEl = document.getElementById("eBaySalesTeam");
  const submitBtn = document.getElementById("eBaySalesSubmitBtn");

  if (guidEl) guidEl.value = currentEbaySalesGuid;
  if (listingTypeEl) listingTypeEl.value = "BUY_IT_NOW";
  if (allowOffersEl) allowOffersEl.value = "false";
  if (autographedEl) autographedEl.value = "No";
  if (teamEl) teamEl.value = "";
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit";
  }

  updateStartingBidState();
  setEbaySalesStatus("");
  setEbaySalesResponse("");
}

function openeBaySalesModal(triggerEl) {
  const guid = getGuidFromTriggerElementForEbaySales(triggerEl) || getActiveGuidFromDetailsModalForEbaySales();
  resetEbaySalesForm(guid);

  reopenDetailsAfterEbaySales = $("#staticBackdrop").hasClass("show");
  if (reopenDetailsAfterEbaySales) {
    $("#staticBackdrop").one("hidden.bs.modal", () => {
      $("#eBaySalesModal").modal("show");
    });
    $("#staticBackdrop").modal("hide");
  } else {
    $("#eBaySalesModal").modal("show");
  }
}

async function submitEbaySalesForm() {
  const guid = sanitize(document.getElementById("eBaySalesGuid")?.value);
  const listingType = sanitize(document.getElementById("eBaySalesListingType")?.value);
  const startingBidRaw = sanitize(document.getElementById("eBaySalesStartingBid")?.value);
  const allowOffersValue = sanitize(document.getElementById("eBaySalesAllowOffers")?.value);
  const team = sanitize(document.getElementById("eBaySalesTeam")?.value);
  const autographed = sanitize(document.getElementById("eBaySalesAutographed")?.value);
  const submitBtn = document.getElementById("eBaySalesSubmitBtn");

  if (!guid) {
    setEbaySalesStatus("GUID is required.", true);
    return;
  }

  if (!team) {
    setEbaySalesStatus("Team is required.", true);
    return;
  }

  if (listingType === "AUCTION" && !startingBidRaw) {
    setEbaySalesStatus("Starting bid is required for auctions.", true);
    return;
  }

  if (listingType === "AUCTION" && Number.isNaN(Number(startingBidRaw))) {
    setEbaySalesStatus("Starting bid must be a valid number.", true);
    return;
  }

  const payload = {
    guid,
    listingType,
    allowOffers: allowOffersValue === "true",
    team,
    autographed
  };

  if (listingType === "AUCTION") {
    payload.startingBid = Number(startingBidRaw);
  }

  try {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";
    }

    setEbaySalesStatus("Submitting request...");
    setEbaySalesResponse("");

    const response = await fetch("https://api.us175.com/demo-list-ebay", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const rawText = await response.text();
    let parsedBody;

    try {
      parsedBody = rawText ? JSON.parse(rawText) : {};
    } catch (_) {
      parsedBody = rawText;
    }

    const responseText =
      typeof parsedBody === "string"
        ? parsedBody
        : JSON.stringify(parsedBody, null, 2);

    setEbaySalesResponse(responseText);
    setEbaySalesStatus(response.ok ? "Request completed." : `Request failed with HTTP ${response.status}.`, !response.ok);
  } catch (error) {
    console.error("Error submitting eBay listing request:", error);
    setEbaySalesStatus("Request failed. See console for details.", true);
    setEbaySalesResponse(String(error?.message || error || "Unknown error"));
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit";
    }
  }
}

function initEbaySalesModal() {
  const formEl = document.getElementById("eBaySalesForm");
  const listingTypeEl = document.getElementById("eBaySalesListingType");
  const submitBtn = document.getElementById("eBaySalesSubmitBtn");

  if (formEl) {
    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      submitEbaySalesForm();
    });
  }

  if (listingTypeEl) {
    listingTypeEl.addEventListener("change", updateStartingBidState);
  }

  if (submitBtn) {
    submitBtn.addEventListener("click", submitEbaySalesForm);
  }
}

$(document).on("hidden.bs.modal", "#eBaySalesModal", function () {
  if (reopenDetailsAfterEbaySales) {
    reopenDetailsAfterEbaySales = false;
    $("#staticBackdrop").modal("show");
  }
});

window.openeBaySalesModal = openeBaySalesModal;
window.initEbaySalesModal = initEbaySalesModal;
