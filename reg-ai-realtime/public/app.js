const PAGE_SIZE = 10;

const state = {
  view: "overview",
  previousView: "overview",
  apiBase: localStorage.getItem("regai_api_base") || window.REGAI_API_BASE || "",
  stats: null,
  documents: [],
  filteredDocuments: [],
  detail: null,
  currentPage: 1,
  pageSize: PAGE_SIZE,
  sortDirection: "desc",
  globalQuery: "",
  isLoading: false
};

const views = {
  overview: {
    title: "Overview",
    subtitle: "Current FDA source status and document change monitoring.",
    source: "all"
  },
  guidances: {
    title: "FDA Guidances",
    subtitle: "Guidance documents filtered for CDER, CBER and OCE when available.",
    source: "guidance"
  },
  press: {
    title: "Press Announcements",
    subtitle: "Recent FDA newsroom press announcements.",
    source: "press"
  },
  approvals: {
    title: "Drug Approvals",
    subtitle: "Approved cellular and gene therapy products tracked from FDA.",
    source: "approval"
  },
  advisory: {
    title: "Advisory Committees",
    subtitle: "Prepared for source expansion.",
    source: "advisory",
    placeholder: true
  },
  oce: {
    title: "OCE Publications",
    subtitle: "Prepared for source expansion.",
    source: "oce_publication",
    placeholder: true
  },
  settings: {
    title: "Settings",
    subtitle: "Connection and source readiness.",
    source: "settings",
    settings: true
  },
  detail: {
    title: "Document Detail",
    subtitle: "Regulatory package and extracted FDA metadata.",
    source: "detail"
  }
};

const sourceEndpoints = {
  guidance: "/api/guidances",
  press: "/api/press",
  approval: "/api/approvals"
};

const elements = {
  toastRegion: document.getElementById("toastRegion"),
  pageTitle: document.getElementById("pageTitle"),
  pageSubtitle: document.getElementById("pageSubtitle"),
  sidebarSyncState: document.getElementById("sidebarSyncState"),
  collectionStatus: document.getElementById("collectionStatus"),
  globalSearch: document.getElementById("globalSearch"),
  settingsApiBase: document.getElementById("settingsApiBase"),
  saveSettings: document.getElementById("saveSettings"),
  syncButton: document.getElementById("syncButton"),
  exportReport: document.getElementById("exportReport"),
  overviewView: document.getElementById("overviewView"),
  documentsView: document.getElementById("documentsView"),
  detailView: document.getElementById("detailView"),
  placeholderView: document.getElementById("placeholderView"),
  settingsView: document.getElementById("settingsView"),
  kpiGrid: document.getElementById("kpiGrid"),
  recentActivity: document.getElementById("recentActivity"),
  priorityUpdates: document.getElementById("priorityUpdates"),
  documentsBySource: document.getElementById("documentsBySource"),
  activityTrend: document.getElementById("activityTrend"),
  overviewSources: document.getElementById("overviewSources"),
  activityMeta: document.getElementById("activityMeta"),
  tableTitle: document.getElementById("tableTitle"),
  tableMeta: document.getElementById("tableMeta"),
  searchFilter: document.getElementById("searchFilter"),
  sourceFilter: document.getElementById("sourceFilter"),
  centerFilter: document.getElementById("centerFilter"),
  statusFilter: document.getElementById("statusFilter"),
  fromFilter: document.getElementById("fromFilter"),
  toFilter: document.getElementById("toFilter"),
  newFilter: document.getElementById("newFilter"),
  updatedFilter: document.getElementById("updatedFilter"),
  clearFilters: document.getElementById("clearFilters"),
  tableLoading: document.getElementById("tableLoading"),
  tableError: document.getElementById("tableError"),
  emptyState: document.getElementById("emptyState"),
  tableWrap: document.getElementById("tableWrap"),
  documentsTable: document.getElementById("documentsTable"),
  dateSortButton: document.getElementById("dateSortButton"),
  sortIndicator: document.getElementById("sortIndicator"),
  pagination: document.getElementById("pagination"),
  prevPage: document.getElementById("prevPage"),
  nextPage: document.getElementById("nextPage"),
  pageInfo: document.getElementById("pageInfo"),
  sourceReadiness: document.getElementById("sourceReadiness"),
  backToList: document.getElementById("backToList"),
  detailBreadcrumb: document.getElementById("detailBreadcrumb"),
  detailCategory: document.getElementById("detailCategory"),
  detailTitle: document.getElementById("detailTitle"),
  detailSubtitle: document.getElementById("detailSubtitle"),
  detailBadges: document.getElementById("detailBadges"),
  detailActions: document.getElementById("detailActions"),
  detailSummary: document.getElementById("detailSummary"),
  detailCollectionStatus: document.getElementById("detailCollectionStatus"),
  detailCards: document.getElementById("detailCards"),
  supportingDocuments: document.getElementById("supportingDocuments"),
  detailVersions: document.getElementById("detailVersions")
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function displayValue(value, fallback = "Not identified") {
  if (value === null || typeof value === "undefined") return fallback;
  const clean = String(value).trim();
  if (!clean || clean.toLowerCase() === "null" || clean.toLowerCase() === "undefined") return fallback;
  return clean;
}

function sourceLabel(sourceType) {
  return {
    guidance: "FDA Guidance",
    press: "Press Announcement",
    approval: "Drug Approval",
    advisory: "Advisory Committee",
    oce_publication: "OCE Publication"
  }[sourceType] || "FDA Document";
}

function supportTypeLabel(type) {
  return {
    package_insert: "Package Insert",
    approval_letter: "Approval Letter",
    clinical_review: "Clinical Review",
    statistical_review: "Statistical Review",
    sbra: "Summary Basis for Regulatory Action",
    prescribing_information: "Prescribing Information",
    label: "Label",
    fda_review: "FDA Review",
    briefing_document: "Briefing Document",
    presentation: "Presentation",
    transcript: "Transcript",
    agenda: "Agenda",
    questions: "Questions",
    other: "Supporting Document"
  }[type] || "Supporting Document";
}

function formatDate(value, options = {}) {
  const clean = displayValue(value, "");
  if (!clean) return options.empty || "Not identified";
  const date = new Date(clean);
  if (Number.isNaN(date.getTime())) return clean;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    ...(options.withTime ? { hour: "2-digit", minute: "2-digit" } : {})
  }).format(date);
}

function formatRelative(value) {
  const clean = displayValue(value, "");
  if (!clean) return "Never";
  const date = new Date(clean);
  if (Number.isNaN(date.getTime())) return formatDate(clean);
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return formatDate(clean);
}

function parseMetadata(document) {
  if (document?.metadata && typeof document.metadata === "object") return document.metadata;
  try {
    const parsed = JSON.parse(document?.metadata_json || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function getDocumentDate(document) {
  const metadata = parseMetadata(document);
  return (
    document.published_date ||
    metadata.approvalDate ||
    metadata.sourceCurrentAsOf ||
    document.updated_at ||
    document.created_at ||
    document.last_checked_at ||
    null
  );
}

function apiPath(path) {
  const base = state.apiBase.replace(/\/$/, "");
  return `${base}${path}`;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(apiPath(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  const payload = await response.json();
  if (!payload.success) throw new Error(payload.error?.message || "API request failed");
  return payload.data;
}

async function fetchStats() {
  state.stats = await apiFetch("/api/stats");
  return state.stats;
}

async function fetchDocuments(source = resolveActiveSource()) {
  const sources = source === "all" ? Object.keys(sourceEndpoints) : [source];
  const requests = sources
    .filter((item) => sourceEndpoints[item])
    .map((item) => apiFetch(`${sourceEndpoints[item]}?limit=500`));

  const responses = await Promise.all(requests);
  state.documents = responses.flatMap((response) => response.items || []);
  applyFilters(false);
  return state.documents;
}

function resolveActiveSource() {
  const view = views[state.view];
  if (!view || view.source === "all") return elements.sourceFilter.value || "all";
  if (sourceEndpoints[view.source]) return view.source;
  return "all";
}

function renderFilters() {
  const fixedSource = sourceEndpoints[views[state.view]?.source];
  elements.sourceFilter.disabled = Boolean(fixedSource);
  if (fixedSource) elements.sourceFilter.value = views[state.view].source;
}

function applyFilters(resetPage = true) {
  const q = elements.searchFilter.value.trim().toLowerCase();
  const globalQ = state.globalQuery.trim().toLowerCase();
  const activeSource = resolveActiveSource();
  const center = elements.centerFilter.value;
  const status = elements.statusFilter.value;
  const from = elements.fromFilter.value ? new Date(`${elements.fromFilter.value}T00:00:00Z`) : null;
  const to = elements.toFilter.value ? new Date(`${elements.toFilter.value}T23:59:59Z`) : null;
  const onlyNew = elements.newFilter.checked;
  const onlyUpdated = elements.updatedFilter.checked;

  state.filteredDocuments = state.documents
    .filter((document) => {
      const metadata = parseMetadata(document);
      const haystack = [
        document.title,
        document.topic,
        document.fda_center,
        document.status,
        metadata.sponsor,
        metadata.manufacturer,
        metadata.indication,
        metadata.properName,
        metadata.tradename
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const dateValue = getDocumentDate(document);
      const date = dateValue ? new Date(dateValue) : null;

      if (activeSource !== "all" && document.source_type !== activeSource) return false;
      if (q && !haystack.includes(q)) return false;
      if (globalQ && !haystack.includes(globalQ)) return false;
      if (center && document.fda_center !== center) return false;
      if (status && document.status !== status) return false;
      if (from && (!date || date < from)) return false;
      if (to && (!date || date > to)) return false;
      if (onlyNew && !Number(document.is_new)) return false;
      if (onlyUpdated && !Number(document.is_updated)) return false;
      return true;
    })
    .sort((a, b) => {
      const aTime = new Date(getDocumentDate(a) || 0).getTime();
      const bTime = new Date(getDocumentDate(b) || 0).getTime();
      return state.sortDirection === "desc" ? bTime - aTime : aTime - bTime;
    });

  if (resetPage) state.currentPage = 1;
  renderTable();
}

function renderOverview() {
  const stats = state.stats || {};
  const lastSync = stats.lastSync?.finished_at || stats.lastSync?.started_at;
  const sourceCount = Array.isArray(stats.sources)
    ? stats.sources.filter((source) => Number(source.enabled)).length
    : stats.highPrioritySources || 0;

  const metrics = [
    ["Last Sync", formatRelative(lastSync), stats.lastSync?.status || "No sync run"],
    ["Total Documents", stats.totalDocuments ?? 0, "Stored in D1"],
    ["New Documents", stats.newDocuments ?? 0, "Current detection window"],
    ["Updated Documents", stats.updatedDocuments ?? 0, "Hash changes"],
    ["FDA Sources", sourceCount, "Enabled feeds"],
    ["Supporting Docs", stats.supportingDocumentsFound ?? 0, "Related files discovered"]
  ];

  elements.kpiGrid.innerHTML = metrics
    .map(
      ([label, value, detail]) => `
        <article class="metric-card">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
          <small>${escapeHtml(detail)}</small>
        </article>
      `
    )
    .join("");

  const recent = visibleForGlobalSearch(state.documents)
    .sort((a, b) => new Date(getDocumentDate(b) || 0) - new Date(getDocumentDate(a) || 0))
    .slice(0, 7);

  elements.activityMeta.textContent = `${recent.length} recent item${recent.length === 1 ? "" : "s"}`;
  elements.recentActivity.innerHTML = recent.length
    ? recent.map(renderActivityItem).join("")
    : renderInlineEmpty("No recent activity yet. Run a sync to populate the dashboard.");

  const priority = visibleForGlobalSearch(state.documents)
    .filter((document) => Number(document.is_new) || Number(document.is_updated))
    .slice(0, 4);

  elements.priorityUpdates.innerHTML = priority.length
    ? priority.map(renderPriorityItem).join("")
    : renderInlineEmpty("New or updated records will appear here after sync.");

  renderDocumentsBySource();
  renderActivityTrend();
  renderSourceReadiness(elements.overviewSources);
}

function visibleForGlobalSearch(documents) {
  const q = state.globalQuery.trim().toLowerCase();
  if (!q) return [...documents];
  return documents.filter((document) => {
    const metadata = parseMetadata(document);
    return [document.title, document.topic, metadata.sponsor, metadata.indication]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(q);
  });
}

function renderActivityItem(document) {
  return `
    <button class="activity-item title-button" type="button" data-document-id="${escapeHtml(document.id)}">
      <span class="activity-title">
        <strong>${escapeHtml(document.title)}</strong>
        ${changeBadges(document)}
      </span>
      <span class="activity-meta">${escapeHtml(sourceLabel(document.source_type))} / ${escapeHtml(formatDate(getDocumentDate(document)))}</span>
    </button>
  `;
}

function renderPriorityItem(document) {
  return `
    <button class="priority-item title-button" type="button" data-document-id="${escapeHtml(document.id)}">
      <span class="activity-title">
        <strong>${escapeHtml(document.title)}</strong>
        ${changeBadges(document)}
      </span>
      <span class="activity-meta">Impact scoring coming soon / ${escapeHtml(sourceLabel(document.source_type))}</span>
    </button>
  `;
}

function renderDocumentsBySource() {
  const bySource = state.stats?.bySource || [];
  const max = Math.max(1, ...bySource.map((item) => Number(item.total) || 0));
  elements.documentsBySource.innerHTML = bySource.length
    ? bySource
        .map((item) => {
          const total = Number(item.total) || 0;
          const width = Math.max(4, Math.round((total / max) * 100));
          return `
            <div class="chart-row">
              <div>
                <strong>${escapeHtml(sourceLabel(item.sourceType))}</strong>
                <div class="chart-bar"><span style="width:${width}%"></span></div>
              </div>
              <span class="badge neutral">${total}</span>
            </div>
          `;
        })
        .join("")
    : renderInlineEmpty("No source distribution available yet.");
}

function renderActivityTrend() {
  const sync = state.stats?.lastSync;
  elements.activityTrend.innerHTML = `
    <div class="trend-row">
      <strong>${escapeHtml(sync?.status || "No sync yet")}</strong>
      <span class="row-subtext">Last run: ${escapeHtml(formatRelative(sync?.finished_at || sync?.started_at))}</span>
      <span class="row-subtext">New: ${escapeHtml(sync?.items_new ?? 0)} / Updated: ${escapeHtml(sync?.items_updated ?? 0)}</span>
    </div>
  `;
}

function renderInlineEmpty(message) {
  return `<div class="state-message"><p>${escapeHtml(message)}</p></div>`;
}

function renderTable() {
  const total = state.filteredDocuments.length;
  const totalPages = Math.max(1, Math.ceil(total / state.pageSize));
  state.currentPage = Math.min(state.currentPage, totalPages);
  const start = (state.currentPage - 1) * state.pageSize;
  const pageItems = state.filteredDocuments.slice(start, start + state.pageSize);

  elements.sortIndicator.textContent = state.sortDirection;
  elements.tableMeta.textContent = `${total} item${total === 1 ? "" : "s"} matched`;
  elements.pageInfo.textContent = `Page ${state.currentPage} of ${totalPages}`;
  elements.prevPage.disabled = state.currentPage <= 1;
  elements.nextPage.disabled = state.currentPage >= totalPages;
  elements.pagination.classList.toggle("hidden", total === 0);

  if (!total) {
    elements.documentsTable.innerHTML = "";
    elements.tableWrap.classList.add("hidden");
    elements.emptyState.classList.remove("hidden");
    elements.emptyState.innerHTML = "<p>No documents match the current filters.</p>";
    return;
  }

  elements.emptyState.classList.add("hidden");
  elements.tableWrap.classList.remove("hidden");
  elements.documentsTable.innerHTML = pageItems.map(renderTableRow).join("");
}

function renderTableRow(document) {
  const metadata = parseMetadata(document);
  const topic = document.topic || metadata.sponsor || metadata.indication || "";
  const status = document.status || "unknown";

  return `
    <tr>
      <td>
        <div class="row-title">
          <button class="title-button" type="button" data-document-id="${escapeHtml(document.id)}">${escapeHtml(document.title)}</button>
          <span class="row-subtext">${escapeHtml(displayValue(topic, ""))}</span>
        </div>
      </td>
      <td>${escapeHtml(sourceLabel(document.source_type))}</td>
      <td>${escapeHtml(displayValue(document.fda_center))}</td>
      <td>${statusBadge(status)}</td>
      <td>${escapeHtml(formatDate(getDocumentDate(document)))}</td>
      <td><div class="badge-row">${changeBadges(document)}</div></td>
      <td>
        <div class="action-row">
          <a class="link-button" href="${escapeHtml(document.url)}" target="_blank" rel="noreferrer">Open FDA</a>
          ${document.pdf_url ? `<a class="link-button" href="${escapeHtml(document.pdf_url)}" target="_blank" rel="noreferrer">PDF</a>` : ""}
        </div>
      </td>
    </tr>
  `;
}

function statusBadge(status) {
  const className = status === "final" ? "final" : status === "draft" ? "draft" : "neutral";
  return `<span class="badge ${className}">${escapeHtml(displayValue(status))}</span>`;
}

function changeBadges(document) {
  const badges = [];
  if (Number(document.is_new)) badges.push('<span class="badge new">NEW</span>');
  if (Number(document.is_updated)) badges.push('<span class="badge updated">UPDATED</span>');
  if (!badges.length) badges.push('<span class="badge neutral">CHECKED</span>');
  return badges.join("");
}

function renderPlaceholder() {
  const view = views[state.view];
  elements.placeholderView.innerHTML = `
    <div class="placeholder-content">
      <div>
        <p class="eyebrow">Phase 2 source</p>
        <h2>${escapeHtml(view.title)}</h2>
        <p>${escapeHtml(view.subtitle)}</p>
      </div>
      <ul>
        <li>Confirm source URL and page structure.</li>
        <li>Add parser coverage in the Worker.</li>
        <li>Enable source in D1 once validated.</li>
      </ul>
    </div>
  `;
}

function renderSettings() {
  elements.settingsApiBase.value = state.apiBase;
  renderSourceReadiness(elements.sourceReadiness);
}

function renderSourceReadiness(target) {
  const sources = state.stats?.sources || [
    { name: "FDA Guidance Documents", sourceType: "guidance", enabled: 1 },
    { name: "FDA Press Announcements", sourceType: "press", enabled: 1 },
    { name: "Approved Cellular and Gene Therapy Products", sourceType: "approval", enabled: 1 },
    { name: "Advisory Committees", sourceType: "advisory", enabled: 0 },
    { name: "OCE Publications", sourceType: "oce_publication", enabled: 0 }
  ];

  target.innerHTML = sources
    .map(
      (source) => `
        <div class="source-row">
          <div>
            <strong>${escapeHtml(source.name)}</strong>
            <div class="row-subtext">${escapeHtml(source.sourceType || source.source_type || "")}</div>
          </div>
          <span class="badge ${Number(source.enabled) ? "final" : "neutral"}">${Number(source.enabled) ? "ENABLED" : "PLANNED"}</span>
        </div>
      `
    )
    .join("");
}

async function openDetailsPanel(id) {
  const localDocument = state.documents.find((document) => document.id === id);
  state.previousView = state.view === "detail" ? state.previousView : state.view;
  state.view = "detail";
  state.detail = null;
  setVisibleView();

  elements.detailTitle.textContent = localDocument?.title || "Loading document";
  elements.detailSubtitle.textContent = "Collecting FDA detail package";
  elements.detailSummary.textContent = "Loading regulatory details.";
  elements.supportingDocuments.innerHTML = renderInlineEmpty("Loading supporting documents.");

  try {
    const detail = normalizeDetailPayload(await apiFetch(`/api/documents/${encodeURIComponent(id)}`));
    state.detail = detail;
    renderDetails(detail);
    window.history.replaceState(null, "", `#documents/${encodeURIComponent(id)}`);
  } catch (error) {
    if (localDocument) {
      renderDetails({ document: localDocument, metadata: parseMetadata(localDocument), versions: [], supporting_documents: [] });
      showToast(error.message, "error");
      return;
    }
    elements.supportingDocuments.innerHTML = `<div class="state-message error"><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function normalizeDetailPayload(payload) {
  return {
    document: payload.document,
    metadata: payload.metadata || parseMetadata(payload.document),
    versions: payload.versions || [],
    supporting_documents: payload.supporting_documents || payload.supportingDocuments || []
  };
}

function closeDetailsPanel() {
  state.view = state.previousView || "overview";
  setActiveNav(state.view);
  setVisibleView();
  window.history.replaceState(null, "", window.location.pathname);
}

function renderDetails(detail) {
  const doc = detail.document;
  const metadata = detail.metadata || parseMetadata(doc);
  const supporting = detail.supporting_documents || [];
  const category = sourceLabel(doc.source_type);
  const properName = displayValue(metadata.properName, "");
  const subtitleParts = [
    properName,
    doc.fda_center,
    metadata.productCategory,
    formatDate(getDocumentDate(doc))
  ].filter((value) => displayValue(value, "") !== "");

  elements.pageTitle.textContent = "Document Detail";
  elements.pageSubtitle.textContent = "Regulatory package and source-level evidence.";
  elements.detailBreadcrumb.innerHTML = `${escapeHtml(category)} / ${escapeHtml(displayValue(doc.topic, "Document"))}`;
  elements.detailCategory.textContent = category;
  elements.detailTitle.textContent = doc.title;
  elements.detailSubtitle.textContent = subtitleParts.join(" / ") || "FDA document";
  elements.detailBadges.innerHTML = `${changeBadges(doc)}${statusBadge(doc.status || "unknown")}`;
  elements.detailSummary.textContent = displayValue(metadata.shortSummary || metadata.indication || doc.topic);
  elements.detailCollectionStatus.textContent = collectionStatusLabel(metadata.collectionStatus, supporting.length);
  elements.detailActions.innerHTML = `
    <a class="primary-button" href="${escapeHtml(doc.url)}" target="_blank" rel="noreferrer">Open FDA</a>
    ${doc.pdf_url ? `<a class="secondary-button" href="${escapeHtml(doc.pdf_url)}" target="_blank" rel="noreferrer">Open PDF</a>` : ""}
    <button class="secondary-button" type="button" id="exportDetail">Export</button>
  `;

  const fields = [
    ["Sponsor", metadata.sponsor || metadata.manufacturer],
    ["Manufacturer", metadata.manufacturer || metadata.sponsor],
    ["Indication", metadata.indication],
    ["FDA Center", doc.fda_center],
    ["Approval / Published Date", metadata.approvalDate || doc.published_date || getDocumentDate(doc)],
    ["Product Type", metadata.productCategory || doc.topic],
    ["STN / BLA / NDA", metadata.stn || metadata.applicationNumber],
    ["Status", doc.status]
  ];

  elements.detailCards.innerHTML = fields
    .map(([label, value]) => detailField(label, displayValue(value)))
    .join("");

  renderSupportingDocuments(supporting);
  renderVersionHistory(detail.versions || []);

  const exportButton = document.getElementById("exportDetail");
  if (exportButton) exportButton.addEventListener("click", () => exportDetail(detail));
}

function collectionStatusLabel(value, supportingCount) {
  if (value === "complete" || supportingCount > 0) return "Complete";
  if (value === "using_cached_fda_data") return "Using cached FDA data";
  if (value === "partial") return "Partial";
  return "Needs review";
}

function detailField(label, value) {
  return `
    <article class="detail-field">
      <span>${escapeHtml(label)}</span>
      <div>${escapeHtml(value)}</div>
    </article>
  `;
}

function renderSupportingDocuments(documents) {
  if (!documents.length) {
    elements.supportingDocuments.innerHTML = renderInlineEmpty(
      "No supporting documents identified yet. The crawler will keep checking this FDA page for new uploads."
    );
    return;
  }

  elements.supportingDocuments.innerHTML = documents.map(renderSupportingCard).join("");
}

function renderSupportingCard(item) {
  const metadata = parseMetadata(item);
  const fileType = displayValue(item.file_type || item.fileType, "HTML");
  const detectedAt = item.detected_at || metadata.detectedDate;
  return `
    <article class="support-card">
      <div class="support-card-header">
        <div class="support-icon">${escapeHtml(fileType === "PDF" ? "PDF" : "DOC")}</div>
        <div>
          <h3>${escapeHtml(supportTypeLabel(item.type))}</h3>
          <p>${escapeHtml(displayValue(item.title, supportTypeLabel(item.type)))}</p>
        </div>
      </div>
      <p>${escapeHtml(fileType)} document</p>
      <p>Detected from FDA product page${detectedAt ? ` / ${formatDate(detectedAt)}` : ""}</p>
      <div class="support-actions">
        <a class="link-button" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">Open</a>
        ${item.file_url ? `<a class="link-button" href="${escapeHtml(item.file_url)}" target="_blank" rel="noreferrer">Download</a>` : ""}
      </div>
    </article>
  `;
}

function renderVersionHistory(versions) {
  elements.detailVersions.innerHTML = versions.length
    ? versions
        .map(
          (version) => `
            <div class="version-item">
              <strong>${escapeHtml(displayValue(version.change_type))}</strong>
              <div class="row-subtext">${escapeHtml(formatDate(version.detected_at, { withTime: true }))}</div>
            </div>
          `
        )
        .join("")
    : '<div class="version-item"><span class="row-subtext">No version history returned yet.</span></div>';
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = message;
  elements.toastRegion.appendChild(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

function showLoading(active) {
  state.isLoading = active;
  elements.syncButton.disabled = active;
  elements.collectionStatus.textContent = active ? "Syncing" : "Ready";
  elements.tableLoading.classList.toggle("hidden", !active || state.view !== "guidances" && state.view !== "press" && state.view !== "approvals");
  if (active) {
    elements.tableError.classList.add("hidden");
    elements.emptyState.classList.add("hidden");
  }
}

function showError(message) {
  elements.collectionStatus.textContent = "Using cached FDA data";
  elements.tableError.classList.remove("hidden");
  elements.tableError.innerHTML = `<p>${escapeHtml(message)}</p>`;
  showToast(message, "error");
}

function setVisibleView() {
  const view = views[state.view];
  elements.pageTitle.textContent = view.title;
  elements.pageSubtitle.textContent = view.subtitle;

  elements.overviewView.classList.toggle("hidden", state.view !== "overview");
  elements.documentsView.classList.toggle("hidden", !["guidances", "press", "approvals"].includes(state.view));
  elements.detailView.classList.toggle("hidden", state.view !== "detail");
  elements.placeholderView.classList.toggle("hidden", !view.placeholder);
  elements.settingsView.classList.toggle("hidden", !view.settings);
}

async function refreshDashboard() {
  const view = views[state.view];
  setVisibleView();
  renderFilters();

  try {
    showLoading(true);
    await fetchStats();

    if (view.placeholder) {
      renderPlaceholder();
      renderSourceReadiness(elements.overviewSources);
      return;
    }

    if (view.settings) {
      renderSettings();
      return;
    }

    if (state.view === "detail" && state.detail) {
      renderDetails(state.detail);
      return;
    }

    const source = state.view === "overview" ? "all" : resolveActiveSource();
    await fetchDocuments(source);

    if (state.view === "overview") {
      renderOverview();
    } else {
      elements.tableTitle.textContent = view.title;
      renderTable();
    }

    updateSyncState();
  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
}

function updateSyncState() {
  const lastSync = state.stats?.lastSync;
  elements.sidebarSyncState.textContent = lastSync
    ? `${lastSync.status || "sync"} / ${formatRelative(lastSync.finished_at || lastSync.started_at)}`
    : "No sync yet";
}

function clearFilters() {
  elements.searchFilter.value = "";
  elements.centerFilter.value = "";
  elements.statusFilter.value = "";
  elements.fromFilter.value = "";
  elements.toFilter.value = "";
  elements.newFilter.checked = false;
  elements.updatedFilter.checked = false;
  if (!sourceEndpoints[views[state.view]?.source]) elements.sourceFilter.value = "all";
  applyFilters();
}

function exportReport() {
  const rows = state.filteredDocuments.length ? state.filteredDocuments : state.documents;
  const header = ["Title", "Source", "FDA Center", "Status", "Date", "Official URL"];
  const csvRows = [
    header,
    ...rows.map((document) => [
      document.title,
      sourceLabel(document.source_type),
      displayValue(document.fda_center),
      displayValue(document.status),
      formatDate(getDocumentDate(document)),
      document.url
    ])
  ];
  downloadCsv("regai-report.csv", csvRows);
}

function exportDetail(detail) {
  const document = detail.document;
  const metadata = detail.metadata || {};
  const rows = [
    ["Field", "Value"],
    ["Title", document.title],
    ["Source", sourceLabel(document.source_type)],
    ["Sponsor", displayValue(metadata.sponsor || metadata.manufacturer)],
    ["Indication", displayValue(metadata.indication)],
    ["FDA Center", displayValue(document.fda_center)],
    ["Status", displayValue(document.status)],
    ["Official URL", document.url]
  ];
  downloadCsv(`${document.id || "regai-document"}.csv`, rows);
}

function downloadCsv(filename, rows) {
  const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function setActiveNav(viewName) {
  const navView = viewName === "detail" ? state.previousView : viewName;
  document.querySelectorAll(".nav-tab").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === navView);
  });
}

function bindEvents() {
  elements.settingsApiBase.value = state.apiBase;

  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      state.previousView = state.view;
      state.currentPage = 1;
      state.detail = null;
      setActiveNav(state.view);
      refreshDashboard();
    });
  });

  elements.globalSearch.addEventListener("input", () => {
    state.globalQuery = elements.globalSearch.value;
    if (state.view === "overview") renderOverview();
    if (["guidances", "press", "approvals"].includes(state.view)) applyFilters();
  });

  elements.saveSettings.addEventListener("click", () => {
    state.apiBase = elements.settingsApiBase.value.trim();
    localStorage.setItem("regai_api_base", state.apiBase);
    showToast("Settings saved.");
    refreshDashboard();
  });

  [elements.searchFilter, elements.centerFilter, elements.statusFilter, elements.fromFilter, elements.toFilter, elements.newFilter, elements.updatedFilter].forEach((input) => {
    input.addEventListener("input", () => applyFilters());
  });

  elements.sourceFilter.addEventListener("input", async () => {
    if (state.view === "overview") {
      await fetchDocuments(resolveActiveSource());
      renderOverview();
      return;
    }
    applyFilters();
  });

  elements.clearFilters.addEventListener("click", clearFilters);
  elements.exportReport.addEventListener("click", exportReport);

  elements.dateSortButton.addEventListener("click", () => {
    state.sortDirection = state.sortDirection === "desc" ? "asc" : "desc";
    applyFilters(false);
  });

  elements.prevPage.addEventListener("click", () => {
    state.currentPage = Math.max(1, state.currentPage - 1);
    renderTable();
  });

  elements.nextPage.addEventListener("click", () => {
    state.currentPage += 1;
    renderTable();
  });

  elements.syncButton.addEventListener("click", async () => {
    try {
      showLoading(true);
      const selectedSource = resolveActiveSource();
      const body = selectedSource === "all" ? {} : { sourceTypes: [selectedSource] };
      const summary = await apiFetch("/api/sync", { method: "POST", body: JSON.stringify(body) });
      showToast(`Sync ${summary.status}: ${summary.sourceSummaries.length} source(s) processed.`);
      await refreshDashboard();
    } catch (error) {
      showError(error.message);
    } finally {
      showLoading(false);
    }
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-document-id]");
    if (!button) return;
    openDetailsPanel(button.dataset.documentId);
  });

  elements.backToList.addEventListener("click", closeDetailsPanel);
}

bindEvents();
refreshDashboard();
