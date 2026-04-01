let reopenDetailsAfterEbaySales = false;
let currentEbaySalesGuid = "";
let ebaySalesTitleManuallyEdited = false;
const EBAY_TITLE_MAX_LENGTH = 80;

function normalizeEbayTitleText(value) {
  return sanitize(value)
    .replace(/[.,]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function updateEbaySalesTitleCounter() {
  const titleEl = document.getElementById("eBaySalesTitle");
  const counterEl = document.getElementById("eBaySalesTitleCounter");
  if (!titleEl || !counterEl) return;

  const length = titleEl.value.length;
  counterEl.textContent = `${length}/${EBAY_TITLE_MAX_LENGTH}`;
  counterEl.className = length >= EBAY_TITLE_MAX_LENGTH ? "text-danger" : "text-muted";
}

function setEbaySalesTitle(value) {
  const titleEl = document.getElementById("eBaySalesTitle");
  if (!titleEl) return;

  titleEl.value = normalizeEbayTitleText(value).slice(0, EBAY_TITLE_MAX_LENGTH).trimEnd();
  updateEbaySalesTitleCounter();
}

function getLastWordOfTeamName(teamName) {
  const parts = normalizeEbayTitleText(teamName).split(" ").filter(Boolean);
  return parts.length ? parts[parts.length - 1] : "";
}

function isAutographedForTitle(value) {
  return normalizeEbayTitleText(value).toLowerCase() === "yes";
}

function getInventoryItemForEbaySales(guid) {
  if (!guid) return null;

  if (Array.isArray(window.exportInventoryData)) {
    const cachedItem = window.exportInventoryData.find((item) => sanitize(item?.guid) === guid);
    if (cachedItem) return cachedItem;
  }

  const modalGuid = sanitize(document.getElementById("modal-guid")?.value);
  if (modalGuid !== guid) return null;

  return {
    guid: modalGuid,
    Year: document.getElementById("modal-Year")?.value,
    Set: document.getElementById("modal-Set")?.value,
    Subset: document.getElementById("modal-Subset")?.value,
    CardNum: document.getElementById("modal-CardNum")?.value,
    PlayerName: document.getElementById("modal-PlayerName")?.value,
    Authenticator: document.getElementById("modal-Authenticator")?.value,
    Grade: document.getElementById("modal-Grade")?.value,
    SerialNumber: document.getElementById("modal-SerialNumber")?.value
  };
}

function buildProposedEbayTitle(item, teamName = "", autographed = "No") {
  if (!item || typeof item !== "object") return "";

  const grade = normalizeEbayTitleText(item.Grade);
  const normalizedGrade = grade === "0" || grade === "0.0" ? "" : grade;
  const teamSuffix = getLastWordOfTeamName(teamName);
  const autoText = isAutographedForTitle(autographed) ? "Auto" : "";
  const parts = [
    normalizeEbayTitleText(item.Year),
    normalizeEbayTitleText(item.Set),
    normalizeEbayTitleText(item.Subset),
    normalizeEbayTitleText(item.CardNum),
    normalizeEbayTitleText(item.PlayerName),
    autoText,
    normalizeEbayTitleText(item.Authenticator),
    normalizedGrade,
    normalizeEbayTitleText(item.SerialNumber),
    teamSuffix
  ];

  return parts
    .filter(Boolean)
    .join(" ")
    .slice(0, EBAY_TITLE_MAX_LENGTH)
    .trimEnd();
}

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
  ebaySalesTitleManuallyEdited = false;

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
  setEbaySalesTitle("");
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
  const team = document.getElementById("eBaySalesTeam")?.value || "";
  const autographed = document.getElementById("eBaySalesAutographed")?.value || "No";
  setEbaySalesTitle(buildProposedEbayTitle(getInventoryItemForEbaySales(guid), team, autographed));

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
  const title = normalizeEbayTitleText(document.getElementById("eBaySalesTitle")?.value).slice(0, EBAY_TITLE_MAX_LENGTH).trimEnd();
  const submitBtn = document.getElementById("eBaySalesSubmitBtn");

  if (!guid) {
    setEbaySalesStatus("GUID is required.", true);
    return;
  }

  if (!team) {
    setEbaySalesStatus("Team is required.", true);
    return;
  }

  if (!title) {
    setEbaySalesStatus("Title is required.", true);
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
    title,
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
  const autographedEl = document.getElementById("eBaySalesAutographed");
  const teamEl = document.getElementById("eBaySalesTeam");
  const titleEl = document.getElementById("eBaySalesTitle");

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

  if (teamEl) {
    teamEl.addEventListener("input", () => {
      if (ebaySalesTitleManuallyEdited) return;
      const item = getInventoryItemForEbaySales(getActiveGuidFromDetailsModalForEbaySales());
      const autographed = autographedEl?.value || "No";
      setEbaySalesTitle(buildProposedEbayTitle(item, teamEl.value, autographed));
    });
  }

  if (autographedEl) {
    autographedEl.addEventListener("change", () => {
      if (ebaySalesTitleManuallyEdited) return;
      const item = getInventoryItemForEbaySales(getActiveGuidFromDetailsModalForEbaySales());
      const team = teamEl?.value || "";
      setEbaySalesTitle(buildProposedEbayTitle(item, team, autographedEl.value));
    });
  }

  if (titleEl) {
    titleEl.addEventListener("input", () => {
      const start = titleEl.selectionStart;
      const end = titleEl.selectionEnd;
      const sanitizedValue = normalizeEbayTitleText(titleEl.value).slice(0, EBAY_TITLE_MAX_LENGTH);
      titleEl.value = sanitizedValue;
      ebaySalesTitleManuallyEdited = true;

      if (typeof start === "number" && typeof end === "number") {
        const nextPosition = Math.min(start, sanitizedValue.length);
        titleEl.setSelectionRange(nextPosition, Math.min(end, sanitizedValue.length));
      }

      updateEbaySalesTitleCounter();
    });
  }

  updateEbaySalesTitleCounter();
}

$(document).on("hidden.bs.modal", "#eBaySalesModal", function () {
  if (reopenDetailsAfterEbaySales) {
    reopenDetailsAfterEbaySales = false;
    $("#staticBackdrop").modal("show");
  }
});

window.openeBaySalesModal = openeBaySalesModal;
window.initEbaySalesModal = initEbaySalesModal;
