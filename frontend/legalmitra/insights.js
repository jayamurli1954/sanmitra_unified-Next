import { getInsightById, insights } from "./insights-data.js?v=legalmitra-ai-v8";

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderCards() {
  const list = document.getElementById("insights-page-list");
  if (!list) return;
  list.innerHTML = insights.map((item) => `
    <a class="insight-page-card" href="./article.html?id=${encodeURIComponent(item.id)}">
      <img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}">
      <span>${escapeHtml(item.category)} - ${escapeHtml(item.readTime)}</span>
      <h2>${escapeHtml(item.title)}</h2>
      <p>${escapeHtml(item.summary)}</p>
      <strong>Read article</strong>
    </a>
  `).join("");
}

function renderList(items = []) {
  if (!items.length) return "";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderTable(table) {
  if (!table?.columns?.length || !table?.rows?.length) return "";
  return `
    <div class="legal-article-table-wrap">
      <table class="legal-article-table">
        <thead>
          <tr>${table.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${table.rows.map((row) => `
            <tr>${table.columns.map((column) => `<td>${escapeHtml(row[column] || "")}</td>`).join("")}</tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAnchors(anchors = []) {
  if (!anchors.length) return "";
  return `
    <section class="legal-article-anchor-box">
      <h2>Statutory and Practice Anchors</h2>
      <div class="legal-article-table-wrap">
        <table class="legal-article-table">
          <thead>
            <tr><th>Reference</th><th>Relevance</th></tr>
          </thead>
          <tbody>
            ${anchors.map((anchor) => `
              <tr>
                <td>${escapeHtml(anchor.reference)}</td>
                <td>${escapeHtml(anchor.point)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderMetadata(article) {
  const metadata = [
    ["Author", article.author],
    ["Reviewed by", article.reviewedBy],
    ["Practice area", article.practiceArea],
    ["Last updated", article.lastUpdated || article.date],
    ["Reading time", article.readTime],
  ].filter(([, value]) => value);

  if (!metadata.length) return "";

  return `
    <dl class="legal-article-meta-grid">
      ${metadata.map(([label, value]) => `
        <div>
          <dt>${escapeHtml(label)}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `).join("")}
    </dl>
    ${renderTags(article.tags)}
  `;
}

function renderTags(tags = []) {
  if (!tags.length) return "";
  return `<div class="legal-article-tags">${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>`;
}

function renderEditorialInsight(insight) {
  if (!insight) return "";
  return `
    <section class="legal-article-insight">
      <h2>${escapeHtml(insight.heading || "Editorial Insight")}</h2>
      ${insight.body.map((para) => `<p>${escapeHtml(para)}</p>`).join("")}
    </section>
  `;
}

function renderSection(section, index) {
  return `
    <section>
      <h2>${index + 1}. ${escapeHtml(section.heading)}</h2>
      ${section.body.map((para) => `<p>${escapeHtml(para)}</p>`).join("")}
      ${renderList(section.points)}
      ${renderTable(section.table)}
      ${section.note ? `<aside class="legal-article-note"><strong>Practice note</strong><p>${escapeHtml(section.note)}</p></aside>` : ""}
    </section>
  `;
}

function renderShareTools(article) {
  return `
    <section class="legal-article-share" aria-label="Share article">
      <div>
        <strong>Share this article</strong>
        <span>Send it to WhatsApp, email, system share, or save a PDF for Drive.</span>
      </div>
      <div class="legal-article-share-actions">
        <button class="share-native" type="button" data-share-action="native" aria-label="Share article" title="Share">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><path d="m8.6 13.5 6.8 4"></path><path d="m15.4 6.5-6.8 4"></path></svg>
        </button>
        <button class="share-whatsapp" type="button" data-share-action="whatsapp" aria-label="Share on WhatsApp" title="WhatsApp">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20.5 4.4 16A8.8 8.8 0 1 1 8 19.6Z"></path><path d="M9.2 8.8c.2-.5.4-.5.7-.5h.5c.2 0 .4 0 .6.4l.7 1.6c.1.3 0 .5-.1.7l-.4.5c-.1.2-.2.3-.1.5.4.8 1.1 1.5 2 2 .2.1.4.1.5-.1l.7-.8c.2-.2.4-.2.7-.1l1.5.7c.3.1.4.3.4.6 0 .7-.5 1.5-1.1 1.7-.6.3-2.7.3-5-1.7-2-1.7-2.8-3.8-2.7-4.5.1-.4.4-.8.5-1Z"></path></svg>
        </button>
        <button class="share-email" type="button" data-share-action="email" aria-label="Share by email" title="Email">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="m4 7 8 6 8-6"></path></svg>
        </button>
        <button class="share-x" type="button" data-share-action="x" aria-label="Share on X" title="X">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4l12.5 16H20L7.5 4H4Z"></path><path d="M4 20 10.8 13"></path><path d="M13.2 11 20 4"></path></svg>
        </button>
        <button class="share-linkedin" type="button" data-share-action="linkedin" aria-label="Share on LinkedIn" title="LinkedIn">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 10v8"></path><path d="M6.5 6v.1"></path><path d="M11 18v-8"></path><path d="M11 13.6c0-2.4 1.3-3.9 3.3-3.9 1.9 0 3.2 1.2 3.2 3.7V18"></path><rect x="3" y="3" width="18" height="18" rx="3"></rect></svg>
        </button>
        <button class="share-drive" type="button" data-share-action="drive" aria-label="Open Google Drive" title="Google Drive">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.8 4h6.4L21 14h-6.4Z"></path><path d="M8.8 4 3 14l3.2 5.5L12 9.5Z"></path><path d="M6.2 19.5h11.6L21 14H9.4Z"></path></svg>
        </button>
        <button class="share-copy" type="button" data-share-action="copy" aria-label="Copy article link" title="Copy link">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"></rect><rect x="4" y="4" width="12" height="12" rx="2"></rect></svg>
        </button>
        <button class="share-pdf" type="button" data-share-action="print" aria-label="Save article as PDF" title="Save PDF">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M5 19h14"></path></svg>
        </button>
      </div>
      <p id="share-status" role="status" aria-live="polite"></p>
      <span class="legal-share-title" hidden>${escapeHtml(article.title)}</span>
      <span class="legal-share-summary" hidden>${escapeHtml(article.summary)}</span>
    </section>
  `;
}

function renderArticle() {
  const target = document.getElementById("article-page-root");
  if (!target) return;
  const params = new URLSearchParams(window.location.search);
  const article = getInsightById(params.get("id"));
  document.title = `${article.title} | LegalMitra`;
  target.innerHTML = `
    <article class="legal-article-page">
      <header class="legal-article-hero">
        <a href="./insights.html">Back to Insights</a>
        <span>${escapeHtml(article.category)} - ${escapeHtml(article.date)} - ${escapeHtml(article.readTime)}</span>
        <h1>${escapeHtml(article.title)}</h1>
        <p>${escapeHtml(article.dek)}</p>
        ${renderMetadata(article)}
      </header>
      <img class="legal-article-image" src="${escapeHtml(article.image)}" alt="${escapeHtml(article.title)}">
      <div class="legal-article-body">
        ${renderShareTools(article)}
        <section class="legal-article-summary-box">
          <h2>Editorial Summary</h2>
          <p>${escapeHtml(article.summary)}</p>
          ${renderList(article.keyTakeaways)}
        </section>
        ${renderAnchors(article.statuteAnchors)}
        ${renderEditorialInsight(article.editorialInsight)}
        ${article.sections.map(renderSection).join("")}
        <section class="legal-article-sources">
          <h2>Source Credits</h2>
          <p>LegalMitra articles must show source credits so readers can verify the legal foundation before relying on the note.</p>
          <ul>
            ${article.sources.map((source) => `
              <li><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.label)}</a></li>
            `).join("")}
          </ul>
        </section>
        <section class="legal-article-disclaimer">
          <h2>Professional Review Note</h2>
          <p>${escapeHtml(article.disclaimer)}</p>
        </section>
      </div>
    </article>
  `;
}

async function copyArticleLink() {
  const url = window.location.href;
  return copyText(url);
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  const input = document.createElement("input");
  input.value = text;
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  const copied = document.execCommand("copy");
  input.remove();
  return copied;
}

function getLinkedInPostText(title, summary, url) {
  return `${title}\n\n${summary}\n\nRead here: ${url}`;
}

function setShareStatus(message) {
  const status = document.getElementById("share-status");
  if (status) status.textContent = message;
}

document.addEventListener("click", async (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const button = target?.closest("[data-share-action]");
  if (!button) return;

  event.preventDefault();
  event.stopPropagation();
  const action = button.getAttribute("data-share-action");
  const title = document.querySelector(".legal-share-title")?.textContent || document.title;
  const summary = document.querySelector(".legal-share-summary")?.textContent || "";
  const url = window.location.href;
  const text = `${title}\n\n${summary}\n\n${url}`;

  try {
    if (action === "native") {
      if (navigator.share) {
        await navigator.share({ title, text: summary, url });
        setShareStatus("Share sheet opened.");
      } else {
        await copyArticleLink();
        setShareStatus("System share is not available here. Link copied instead.");
      }
      return;
    }

    if (action === "whatsapp") {
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
      setShareStatus("WhatsApp share opened.");
      return;
    }

    if (action === "email") {
      window.location.href = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(text)}`;
      setShareStatus("Email draft opened.");
      return;
    }

    if (action === "x") {
      window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`, "_blank", "noopener");
      setShareStatus("X share opened.");
      return;
    }

    if (action === "linkedin") {
      const copied = await copyText(getLinkedInPostText(title, summary, url));
      window.open("https://www.linkedin.com/feed/?shareActive=true", "_blank", "noopener");
      setShareStatus(copied ? "LinkedIn opened. Article text and link copied; paste it in the post box." : "LinkedIn opened. Copy the article link manually if paste is empty.");
      return;
    }

    if (action === "drive") {
      copyArticleLink().catch(() => undefined);
      window.open("https://drive.google.com/drive/my-drive", "_blank", "noopener");
      setShareStatus("Link copied. Google Drive opened; upload the saved PDF or store the copied article link.");
      return;
    }

    if (action === "copy") {
      const copied = await copyArticleLink();
      setShareStatus(copied ? "Article link copied." : "Could not copy link automatically.");
      return;
    }

    if (action === "print") {
      setShareStatus("Use the print dialog to save as PDF or save to Google Drive if your browser supports it.");
      window.print();
    }
  } catch (error) {
    setShareStatus("Sharing could not be completed. Please copy the link manually.");
  }
});

renderCards();
renderArticle();
