const form = document.querySelector("#search-form");
const requestInput = document.querySelector("#request-input");
const characterCount = document.querySelector("#character-count");
const submitButton = document.querySelector("#submit-button");
const feedback = document.querySelector("#feedback");
const resultsSection = document.querySelector("#results-section");
const resultsTitle = document.querySelector("#results-title");
const resultsSubtitle = document.querySelector("#results-subtitle");
const specifiedCriteria = document.querySelector("#specified-criteria");
const unspecifiedBlock = document.querySelector("#unspecified-block");
const unspecifiedCriteria = document.querySelector("#unspecified-criteria");
const filterNote = document.querySelector("#filter-note");
const filterNoteText = document.querySelector("#filter-note-text");
const exactSearchLink = document.querySelector("#exact-search-link");
const resultList = document.querySelector("#result-list");

const criterionLabels = {
  location: "Location",
  county: "Division",
  min_fees: "Minimum fees",
  max_fees: "Maximum fees",
  gender: "Gender",
  boarding: "Boarding",
  level: "School level",
  admission_class: "Admission class",
  admitting_now: "Admitting now",
  school_name: "School name",
  curriculum: "Curriculum",
  facility: "Facility",
  affiliation: "Affiliation",
};

const keyCriteria = [
  "location", "county", "min_fees", "max_fees", "gender", "boarding",
  "level", "admission_class", "admitting_now",
];

function formatFees(amount) {
  return `UGX ${Number(amount).toLocaleString("en-UG")}`;
}

function criterionValue(key, value) {
  if (key === "min_fees" || key === "max_fees") {
    return `${formatFees(value)} / term`;
  }
  if (key === "gender") {
    return ({ girls: "Girls", boys: "Boys", mixed: "Mixed" })[value] || value;
  }
  if (key === "boarding") {
    return ({ boarding: "Boarding", day: "Day", both: "Day & boarding" })[value] || value;
  }
  if (key === "admitting_now") {
    return value ? "Yes" : "No";
  }
  return String(value);
}

function criterionRows(criteria) {
  return Object.entries(criteria || {}).filter(([key, value]) =>
    key !== "unsupported" && key !== "clarification_question" && value !== null && value !== undefined
      && !(Array.isArray(value) && value.length === 0)
  );
}

function renderCriteria(criteria) {
  const rows = criterionRows(criteria);
  specifiedCriteria.replaceChildren();

  if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-criteria";
    empty.textContent = "No specific filter was confirmed.";
    specifiedCriteria.append(empty);
  } else {
    for (const [key, value] of rows) {
      const row = document.createElement("div");
      row.className = "criteria-row";
      const label = document.createElement("dt");
      label.textContent = criterionLabels[key] || key.replaceAll("_", " ");
      const detail = document.createElement("dd");
      detail.textContent = criterionValue(key, value);
      row.append(label, detail);
      specifiedCriteria.append(row);
    }
  }

  const absent = [];
  const feeFloor = criteria?.min_fees;
  const feeCeiling = criteria?.max_fees;
  if (feeFloor == null && feeCeiling == null) {
    absent.push("Fee range");
  } else {
    if (feeFloor == null) absent.push("Minimum fees");
    if (feeCeiling == null) absent.push("Maximum fees");
  }
  for (const key of keyCriteria) {
    if (key === "min_fees" || key === "max_fees") continue;
    if (criteria?.[key] == null) absent.push(criterionLabels[key]);
  }
  unspecifiedCriteria.replaceChildren();
  for (const label of absent) {
    const chip = document.createElement("span");
    chip.className = "criteria-chip";
    chip.textContent = label;
    unspecifiedCriteria.append(chip);
  }
  unspecifiedBlock.hidden = absent.length === 0;
}

function safeExternalUrl(value, fallback = "https://eschool.ug/find-schools/search") {
  if (!value) return fallback;
  try {
    const url = new URL(value, window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : fallback;
  } catch {
    return fallback;
  }
}

function showFeedback(kind, title, message, actions = []) {
  feedback.replaceChildren();
  feedback.className = "feedback page-width";
  const card = document.createElement("div");
  card.className = `feedback-card is-${kind}`;
  const icon = document.createElement("span");
  icon.className = "feedback-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = kind === "error" ? "!" : kind === "clarification" ? "?" : "✓";
  const copy = document.createElement("div");
  const heading = document.createElement("h2");
  heading.textContent = title;
  const body = document.createElement("p");
  body.textContent = message;
  copy.append(heading, body);
  if (actions.length) {
    const actionRow = document.createElement("div");
    actionRow.className = "feedback-actions";
    for (const action of actions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "small-button";
      button.textContent = action.label;
      button.addEventListener("click", action.onClick);
      actionRow.append(button);
    }
    copy.append(actionRow);
  }
  card.append(icon, copy);
  feedback.append(card);
  feedback.hidden = false;
}

function resultScore(item) {
  return Array.isArray(item.matched) ? item.matched.length : 0;
}

function appendList(container, headingText, entries, className, emptyText) {
  const section = document.createElement("section");
  const heading = document.createElement("h4");
  heading.textContent = headingText;
  section.append(heading);
  if (entries.length) {
    const list = document.createElement("ul");
    list.className = className;
    for (const entry of entries) {
      const item = document.createElement("li");
      item.textContent = entry;
      list.append(item);
    }
    section.append(list);
  } else {
    const empty = document.createElement("p");
    empty.className = "empty-detail";
    empty.textContent = emptyText;
    section.append(empty);
  }
  container.append(section);
}

function schoolCard(item, index, totalRequirements) {
  const school = item.school || {};
  const matched = Array.isArray(item.matched) ? item.matched : [];
  const unverified = Array.isArray(item.unverified) ? item.unverified : [];
  const count = matched.length;
  const score = totalRequirements ? Math.round((count / totalRequirements) * 100) : 0;
  const card = document.createElement("article");
  card.className = `school-card${index === 0 ? " is-best" : ""}`;
  const content = document.createElement("div");
  content.className = "school-content";

  if (index === 0 && totalRequirements) {
    const best = document.createElement("span");
    best.className = "best-label";
    const star = document.createElement("span");
    star.setAttribute("aria-hidden", "true");
    star.textContent = "★";
    best.append(star, document.createTextNode(" Best match"));
    content.append(best);
  }

  const top = document.createElement("div");
  top.className = "school-topline";
  const title = document.createElement("h3");
  title.className = "school-title";
  const safeSchoolUrl = safeExternalUrl(school.url, "");
  if (safeSchoolUrl) {
    const link = document.createElement("a");
    link.href = safeSchoolUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = school.name || "School";
    title.append(link);
  } else {
    title.textContent = school.name || "School";
  }
  const scoreLabel = document.createElement("div");
  scoreLabel.className = "score";
  const scoreValue = document.createElement("strong");
  scoreValue.textContent = `${count}${totalRequirements ? ` of ${totalRequirements}` : ""}`;
  scoreLabel.append(
    scoreValue,
    document.createTextNode(totalRequirements ? "requirements confirmed" : "confirmed"),
  );
  top.append(title, scoreLabel);
  content.append(top);

  const metadata = document.createElement("div");
  metadata.className = "school-meta";
  if (school.location) {
    const location = document.createElement("span");
    location.className = "school-meta-item";
    location.textContent = `⌖ ${school.location}`;
    metadata.append(location);
  }
  if (school.level) {
    const level = document.createElement("span");
    level.className = "school-meta-item";
    level.textContent = school.level;
    metadata.append(level);
  }
  if (school.rating) {
    const rating = document.createElement("span");
    rating.className = "school-meta-item";
    rating.textContent = `★ ${school.rating}`;
    metadata.append(rating);
  }
  if (metadata.childElementCount) content.append(metadata);

  const badges = document.createElement("div");
  badges.className = "school-badges";
  for (const value of [school.gender, school.boarding]) {
    if (!value) continue;
    const badge = document.createElement("span");
    badge.className = "school-badge";
    badge.textContent = value;
    badges.append(badge);
  }
  if (school.admission_status) {
    const admission = document.createElement("span");
    const status = school.admission_status;
    admission.className = `school-badge ${/open|admitting|accepting/i.test(status) ? "admissions-open" : /closed|full/i.test(status) ? "admissions-closed" : ""}`;
    admission.textContent = status;
    badges.append(admission);
  }
  if (badges.childElementCount) content.append(badges);

  const fee = document.createElement("p");
  fee.className = `school-fee${school.fees == null ? " is-missing" : ""}`;
  if (school.fees == null) {
    fee.append(document.createTextNode("Fees not listed"));
    const note = document.createElement("small");
    note.textContent = "Ask the school";
    fee.append(note);
  } else {
    fee.append(document.createTextNode(formatFees(school.fees)));
    const term = document.createElement("small");
    term.textContent = "per term";
    fee.append(term);
  }
  content.append(fee);

  if (totalRequirements) {
    const meter = document.createElement("div");
    meter.className = "match-meter";
    meter.setAttribute("role", "progressbar");
    meter.setAttribute("aria-label", `${count} of ${totalRequirements} requirements confirmed`);
    meter.setAttribute("aria-valuemin", "0");
    meter.setAttribute("aria-valuemax", String(totalRequirements));
    meter.setAttribute("aria-valuenow", String(count));
    const fill = document.createElement("span");
    fill.style.width = `${Math.min(100, Math.max(0, score))}%`;
    meter.append(fill);
    content.append(meter);
  }

  const details = document.createElement("div");
  details.className = "match-details";
  appendList(details, "WHY IT MATCHES", matched, "confirmed-list", "No requirements confirmed from the listing.");
  appendList(details, "COULDN’T CONFIRM", unverified, "unconfirmed-list", "Nothing flagged. Every checked requirement is on the listing.");
  content.append(details);

  if (school.url) {
    const actions = document.createElement("div");
    actions.className = "school-actions";
    const viewLink = document.createElement("a");
    viewLink.className = "school-link";
    viewLink.href = safeSchoolUrl || "https://eschool.ug/find-schools/search";
    viewLink.target = "_blank";
    viewLink.rel = "noopener noreferrer";
    viewLink.textContent = "View on eSchool ↗";
    actions.append(viewLink);
    content.append(actions);
  }
  card.append(content);
  return card;
}

function renderResults(data) {
  const criteria = data.criteria || {};
  const rows = criterionRows(criteria);
  const totalRequirements = rows.length;
  const results = [...(data.results || [])].sort((first, second) => resultScore(second) - resultScore(first));

  feedback.hidden = true;
  feedback.replaceChildren();
  resultsSection.hidden = false;
  resultsTitle.textContent = `${results.length} ${results.length === 1 ? "school" : "schools"} found`;
  resultsSubtitle.textContent = `Sorted by how many of your ${totalRequirements} requirements the listing confirms.`;
  renderCriteria(criteria);
  resultList.replaceChildren(...results.map((item, index) => schoolCard(item, index, totalRequirements)));

  const unsupported = [
    ...(data.not_filterable_on_site || []),
    ...(criteria.unsupported || []),
  ];
  filterNote.hidden = unsupported.length === 0;
  if (unsupported.length) {
    const labels = unsupported.map((key) => criterionLabels[key] || key).join(", ");
    filterNoteText.textContent = `${labels} can’t be searched as eSchool filters. The assistant checks each listing where possible and marks missing details as unconfirmed.`;
  }

  exactSearchLink.href = safeExternalUrl(data.search_url);
  exactSearchLink.hidden = !data.search_url;
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showClarification(data) {
  resultsSection.hidden = true;
  filterNote.hidden = true;
  showFeedback("clarification", "Let’s narrow it down", data.message || "Could you add a location, class, or budget?", [
    { label: "Edit request", onClick: () => requestInput.focus() },
  ]);
}

function showNoResults(data) {
  filterNote.hidden = true;
  resultsSection.hidden = false;
  resultsTitle.textContent = "No suitable schools";
  resultsSubtitle.textContent = "Try widening your budget, removing an area filter, or searching a nearby location.";
  renderCriteria(data.criteria || {});
  resultList.replaceChildren();
  exactSearchLink.href = safeExternalUrl(data.search_url);
  exactSearchLink.hidden = !data.search_url;
  showFeedback("clarification", "No schools matched", data.message || "Try widening your budget or searching a nearby area.", [
    { label: "Edit request", onClick: () => requestInput.focus() },
    { label: "Open eSchool search", onClick: () => window.open(safeExternalUrl(data.search_url), "_blank", "noopener,noreferrer") },
  ]);
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showError(message, criteria = null) {
  resultsSection.hidden = !criteria;
  filterNote.hidden = true;
  if (criteria) {
    resultsTitle.textContent = "Search service unavailable";
    resultsSubtitle.textContent = "Your request was understood, so nothing needs retyping.";
    renderCriteria(criteria);
    resultList.replaceChildren();
    exactSearchLink.hidden = true;
  }
  showFeedback("error", "We couldn’t complete the search", message || "The search service didn’t respond. Please try again shortly.", [
    { label: "Try again", onClick: () => form.requestSubmit() },
    { label: "Open eSchool.ug", onClick: () => window.open("https://eschool.ug/find-schools/search", "_blank", "noopener,noreferrer") },
  ]);
}

requestInput.addEventListener("input", () => {
  characterCount.textContent = `${requestInput.value.length} / 1000`;
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    requestInput.value = button.dataset.request || "";
    characterCount.textContent = `${requestInput.value.length} / 1000`;
    requestInput.focus();
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = requestInput.value.trim();
  if (!request) {
    requestInput.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.querySelector(".button-label").textContent = "Searching…";
  feedback.hidden = true;
  resultsSection.hidden = true;

  try {
    const response = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ request }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join("; ")
        : payload.detail;
      throw new Error(detail || `Request failed (${response.status}).`);
    }

    switch (payload.status) {
      case "ok":
        renderResults(payload);
        break;
      case "needs_clarification":
        showClarification(payload);
        break;
      case "no_results":
        showNoResults(payload);
        break;
      case "error":
        showError(payload.message, payload.criteria);
        break;
      default:
        showError("The search service returned an unexpected response. Please try again.");
    }
  } catch (error) {
    showError(error instanceof Error ? error.message : "The search service didn’t respond.");
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector(".button-label").textContent = "Find schools";
  }
});
