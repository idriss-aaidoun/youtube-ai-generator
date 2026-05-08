const form = document.getElementById("generation-form");
const resultRoot = document.getElementById("result");
const resultPanel = document.getElementById("result-panel");
const statusText = document.getElementById("status-text");
const videoListRoot = document.getElementById("video-list");
const submitButton = form.querySelector('button[type="submit"]');
const loadingPhases = [
  "Analyse du sujet",
  "Construction de l'angle",
  "Rédaction du script",
  "Création des visuels",
  "Montage, SEO et publication",
];

let loadingTimer = null;

document.body.classList.add("is-ready");

function setStatus(message) {
  statusText.textContent = message;
}

function clearNode(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function createSection(title, value) {
  const container = document.createElement("div");
  container.className = "section-item";

  const label = document.createElement("span");
  label.textContent = title;

  const body = document.createElement("strong");
  body.textContent = value;

  container.append(label, body);
  return container;
}

function createSummaryChip(label, value) {
  const container = document.createElement("div");
  container.className = "summary-chip";

  const title = document.createElement("span");
  title.textContent = label;

  const body = document.createElement("strong");
  body.textContent = value;

  container.append(title, body);
  return container;
}

function createLoadingCard() {
  const card = document.createElement("article");
  card.className = "result-card loading-card";

  const header = document.createElement("div");
  header.className = "loading-header";

  const spinner = document.createElement("span");
  spinner.className = "loading-spinner";
  spinner.setAttribute("aria-hidden", "true");

  const title = document.createElement("strong");
  title.textContent = "Génération en cours";

  header.append(spinner, title);

  const paragraph = document.createElement("p");
  paragraph.className = "loading-copy";
  paragraph.textContent = "Le pipeline construit l'idée, le script, la voix, les visuels, le montage et la publication.";

  const progress = document.createElement("div");
  progress.className = "loading-progress";

  const progressFill = document.createElement("span");
  progressFill.className = "loading-progress-fill";
  progress.appendChild(progressFill);

  const steps = document.createElement("div");
  steps.className = "loading-steps";

  for (const step of ["Idée", "Script", "Audio", "Visuels", "Montage", "SEO", "Publication"]) {
    const item = document.createElement("span");
    item.className = "loading-step";
    item.textContent = step;
    steps.appendChild(item);
  }

  card.append(header, paragraph, progress, steps);
  return card;
}

async function readApiResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    const cleaned = text.replace(/\s+/g, " ").trim();
    throw new Error(cleaned || `La génération a échoué (HTTP ${response.status}).`);
  }
}

function startLoadingState() {
  if (loadingTimer !== null) {
    window.clearInterval(loadingTimer);
  }

  submitButton.disabled = true;
  submitButton.setAttribute("aria-busy", "true");
  resultPanel.classList.add("is-loading");
  clearNode(resultRoot);
  resultRoot.appendChild(createLoadingCard());

  let phaseIndex = 0;
  setStatus(`${loadingPhases[phaseIndex]}...`);

  loadingTimer = window.setInterval(() => {
    phaseIndex = Math.min(loadingPhases.length - 1, phaseIndex + 1);
    setStatus(`${loadingPhases[phaseIndex]}...`);
  }, 900);
}

function stopLoadingState() {
  if (loadingTimer !== null) {
    window.clearInterval(loadingTimer);
    loadingTimer = null;
  }

  submitButton.disabled = false;
  submitButton.removeAttribute("aria-busy");
  resultPanel.classList.remove("is-loading");
}

const TREND_BREAKDOWN_LABELS = {
  topic_profile: "Profil thématique",
  search_intent: "Intention de recherche",
  timeliness: "Actualité",
  evergreen: "Evergreen",
  virality: "Viralité",
  audience_fit: "Audience",
  competition_risk: "Risque concurrence",
  specificity_bonus: "Bonus précision",
};

function toTextList(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => `${item}`.trim())
    .filter(Boolean);
}

function formatTrendBreakdownValue(key, value) {
  if (typeof value !== "number") {
    return `${value}`;
  }

  const sign = key === "competition_risk" ? "-" : "+";
  return `${sign}${Math.abs(value)}`;
}

function createTrendList(title, items, emptyLabel) {
  const container = document.createElement("div");
  container.className = "trend-list-block";

  const label = document.createElement("span");
  label.textContent = title;

  const list = document.createElement("ul");
  list.className = "trend-list";

  const entries = toTextList(items);
  if (!entries.length) {
    const empty = document.createElement("li");
    empty.className = "trend-list-empty";
    empty.textContent = emptyLabel;
    list.appendChild(empty);
  } else {
    for (const item of entries.slice(0, 4)) {
      const entry = document.createElement("li");
      entry.textContent = item;
      list.appendChild(entry);
    }
  }

  container.append(label, list);
  return container;
}

function createTrendBreakdown(scoreBreakdown) {
  const container = document.createElement("div");
  container.className = "trend-breakdown";

  const entries = Object.entries(scoreBreakdown || {});
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "trend-breakdown-empty";
    empty.textContent = "Aucun détail de score disponible.";
    container.appendChild(empty);
    return container;
  }

  for (const [key, value] of entries) {
    const chip = createSummaryChip(
      TREND_BREAKDOWN_LABELS[key] || key.replace(/_/g, " "),
      formatTrendBreakdownValue(key, value),
    );
    container.appendChild(chip);
  }

  return container;
}

function createTrendSection(summary) {
  const section = document.createElement("section");
  section.className = "trend-section";

  const header = document.createElement("div");
  header.className = "trend-section-header";

  const headerCopy = document.createElement("div");
  const label = document.createElement("span");
  label.className = "section-label";
  label.textContent = "Lecture de tendance";

  const title = document.createElement("h4");
  title.textContent = "Pourquoi ce sujet ressort maintenant";

  const body = document.createElement("p");
  body.className = "trend-summary";
  body.textContent = summary.trend_summary || "Aucune explication de tendance n'est disponible pour ce sujet.";

  headerCopy.append(label, title, body);

  const band = document.createElement("div");
  band.className = "trend-band";
  band.append(
    createSummaryChip("Score", `${summary.trend_score || 0}/100`),
    createSummaryChip("Catégorie", summary.trend_category || "Sujet général"),
    createSummaryChip("Stade", summary.trend_stage || "stable"),
    createSummaryChip("Format", summary.trend_format || "format court"),
    createSummaryChip("Mots-clés", toTextList(summary.trend_keywords).slice(0, 3).join(", ") || "n/a"),
    createSummaryChip("Phrases", toTextList(summary.trend_phrases).slice(0, 2).join(" • ") || "n/a"),
  );

  const columns = document.createElement("div");
  columns.className = "trend-columns";
  columns.append(
    createTrendList("Signaux lus", summary.trend_signals, "Aucun signal détecté."),
    createTrendList("Opportunités", summary.trend_opportunities, "Aucune opportunité détectée."),
    createTrendList("Risques", summary.trend_risks, "Aucun risque majeur détecté."),
  );

  const breakdownTitle = document.createElement("span");
  breakdownTitle.className = "trend-breakdown-title";
  breakdownTitle.textContent = "Décomposition du score";

  const breakdown = createTrendBreakdown(summary.trend_breakdown);

  header.append(headerCopy);
  section.append(header, band, columns, breakdownTitle, breakdown);
  return section;
}

function createHistoryCard(video) {
  const card = document.createElement("article");
  card.className = "history-card";

  const title = document.createElement("h3");
  title.textContent = video.title;

  const description = document.createElement("p");
  description.textContent = video.topic;

  const metaRow = document.createElement("div");
  metaRow.className = "meta-row";

  const metaValues = [
    ["SEO", `${video.seo_score}`],
    ["Statut", video.publication_status],
    ["Langue", video.language],
    ["Voix", video.voice],
  ];

  for (const [labelText, valueText] of metaValues) {
    const pill = document.createElement("span");
    pill.className = "meta-pill";
    pill.textContent = `${labelText}: ${valueText}`;
    metaRow.appendChild(pill);
  }

  const footer = document.createElement("p");
  footer.textContent = `Créé le ${video.created_at || "n/a"}`;

  card.append(title, description, metaRow, footer);
  return card;
}

function createResultCard(payload) {
  const { pipeline, video } = payload;
  const summary = pipeline.summary;
  const thumbnail = pipeline.thumbnail || {};

  const card = document.createElement("article");
  card.className = "result-card";

  const title = document.createElement("h3");
  title.textContent = summary.title;

  const paragraph = document.createElement("p");
  paragraph.textContent = summary.primary_angle;

  const trendSection = createTrendSection(summary);

  const metrics = document.createElement("div");
  metrics.className = "summary-grid";
  metrics.append(
    createSummaryChip("Trend score", `${summary.trend_score || 0}/100`),
    createSummaryChip("Trend category", summary.trend_category || "Sujet général"),
    createSummaryChip("Trend format", summary.trend_format || "format court"),
    createSummaryChip("SEO score", `${summary.seo_score}/100`),
    createSummaryChip("Scènes", `${summary.scene_count}`),
    createSummaryChip("Audio", summary.audio_status),
    createSummaryChip("Audio provider", summary.audio_provider || "placeholder"),
    createSummaryChip("Script source", summary.script_source || "local_template"),
    createSummaryChip("Visual provider", summary.visual_provider || "local_placeholder"),
    createSummaryChip("Visual images", `${summary.visual_image_count || 0}`),
    createSummaryChip("Video provider", summary.video_provider || "imageio_ffmpeg"),
    createSummaryChip("Thumbnail provider", summary.thumbnail_provider || "thumbnail_composite"),
    createSummaryChip("Thumbnail source", summary.thumbnail_source_image_provider || "local_placeholder"),
    createSummaryChip("Thumbnail upload", summary.thumbnail_upload_status || "missing_thumbnail"),
    createSummaryChip("Chapitres", `${summary.publication_chapter_count || 0}`),
    createSummaryChip("Hashtags", `${summary.publication_hashtag_count || 0}`),
    createSummaryChip("Chapitres source", summary.publication_chapter_source || "auto"),
    createSummaryChip("Hashtags source", summary.publication_hashtag_source || "seo"),
    createSummaryChip("Publication provider", summary.publication_provider || "local_plan"),
    createSummaryChip("Publication", summary.publication_status),
  );

  const sectionTitle = document.createElement("p");
  sectionTitle.textContent = "Sections du script";

  const sections = document.createElement("div");
  sections.className = "section-list";
  for (const section of pipeline.script.sections) {
    sections.appendChild(createSection(section.heading, section.summary));
  }

  const artifactsTitle = document.createElement("p");
  artifactsTitle.textContent = "Artefacts générés";

  const artifacts = document.createElement("div");
  artifacts.className = "artifact-list";
  const artifactItems = [
    ["Audio", video.audio_path],
    ["Storyboard", video.storyboard_path],
    ["Sous-titres", video.subtitle_path],
    ["Miniature", summary.thumbnail_path || thumbnail.artifact_path],
    ["Vidéo MP4", video.montage_path],
    ["Dossier", video.artifact_dir],
  ];

  for (const [labelText, valueText] of artifactItems) {
    const item = document.createElement("div");
    item.className = "artifact-item";

    const label = document.createElement("span");
    label.textContent = labelText;

    const body = document.createElement("strong");
    body.textContent = valueText;

    item.append(label, body);
    artifacts.appendChild(item);
  }

  const tagsTitle = document.createElement("p");
  tagsTitle.textContent = "Tags SEO";

  const tags = document.createElement("div");
  tags.className = "tag-row";
  for (const tag of pipeline.seo.tags) {
    const item = document.createElement("div");
    item.className = "tag-item";
    item.textContent = tag;
    tags.appendChild(item);
  }

  if (pipeline.publication.youtube_url) {
    const publicationLink = document.createElement("a");
    publicationLink.href = pipeline.publication.youtube_url;
    publicationLink.textContent = pipeline.publication.youtube_url;
    publicationLink.target = "_blank";
    publicationLink.rel = "noreferrer";
    publicationLink.className = "tag-item";
    tags.appendChild(publicationLink);
  }

  const previewTitle = document.createElement("p");
  previewTitle.textContent = "Extrait du script";

  const preview = document.createElement("pre");
  preview.textContent = pipeline.script.full_text;

  card.append(
    title,
    paragraph,
    trendSection,
    metrics,
    sectionTitle,
    sections,
    artifactsTitle,
    artifacts,
    tagsTitle,
    tags,
    previewTitle,
    preview,
  );

  return card;
}

function createErrorCard(message) {
  const card = document.createElement("article");
  card.className = "result-card error-card";

  const title = document.createElement("strong");
  title.textContent = "Erreur";

  const paragraph = document.createElement("p");
  paragraph.textContent = message;

  card.append(title, paragraph);
  return card;
}

async function refreshVideos() {
  const response = await fetch("/api/videos");
  const payload = await response.json();

  clearNode(videoListRoot);

  if (!payload.items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Aucun brouillon enregistré pour le moment.";
    videoListRoot.appendChild(empty);
    return;
  }

  for (const video of payload.items) {
    videoListRoot.appendChild(createHistoryCard(video));
  }
}

async function submitGeneration(event) {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.subject = (payload.topic || payload.subject || payload.title || "").trim();
  payload.title = (payload.title || "").trim();
  payload.topic = (payload.topic || payload.subject || "").trim();
  payload.description = (payload.description || "").trim();
  payload.duration_minutes = Number(payload.duration_minutes || 3);

  setStatus("Préparation du pipeline...");
  startLoadingState();

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await readApiResponse(response);

    if (!response.ok) {
      throw new Error(data.error || "La génération a échoué.");
    }

    stopLoadingState();
    clearNode(resultRoot);
    resultRoot.appendChild(createResultCard(data));
    setStatus(`Génération terminée: ${data.pipeline.summary.title} · tendance ${data.pipeline.summary.trend_score || 0}/100 (${data.pipeline.summary.trend_stage || "stable"})`);
    await refreshVideos();
  } catch (error) {
    stopLoadingState();
    clearNode(resultRoot);
    resultRoot.appendChild(createErrorCard(error.message));
    setStatus("Erreur pendant la génération.");
  }
}

form.addEventListener("submit", submitGeneration);
refreshVideos().catch((error) => {
  clearNode(videoListRoot);
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = `Impossible de charger l'historique: ${error.message}`;
  videoListRoot.appendChild(empty);
});
