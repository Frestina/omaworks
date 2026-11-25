// The search on the front page. See SPEC.md, "The website".
//
// It reads catalog-index.json, which the build writes from the catalog, and
// makes no other request. Names and authors come from the catalog and are
// someone else's text, so every value goes into the page as text, never as
// HTML. A result shows no status: the plugin's page has the statuses, each
// next to its reports.
"use strict";

const PLAIN_ID = /^[a-z0-9][a-z0-9._-]{0,99}$/;
const REPO_PATH = /^repos\/[a-z0-9-]+\/[a-z0-9._~-]+\/$/;
const RELEASE = /^\d{1,4}\.\d{1,4}\.\d{1,4}(-(beta|rc)\d{1,4})?$/;
const MAX_RESULTS = 50;

function text(value) {
  return typeof value === "string" ? value : "";
}

function releases(value) {
  return Array.isArray(value) ? value.filter((v) => typeof v === "string" && RELEASE.test(v)) : [];
}

// The index as a list of entries. Anything that doesn't fit is left out.
function entries(index) {
  const list = [];
  for (const item of (index && index.plugins) || []) {
    if (!Array.isArray(item) || typeof item[0] !== "string" || !PLAIN_ID.test(item[0])) continue;
    const id = item[0];
    list.push({
      id,
      name: text(item[1]) || id,
      author: text(item[2]),
      versions: releases(item[3]),
      path: `plugins/${id}/`,
      outside: false,
    });
  }
  for (const item of (index && index.repos) || []) {
    if (!Array.isArray(item) || typeof item[0] !== "string") continue;
    if (typeof item[1] !== "string" || !REPO_PATH.test(item[1])) continue;
    list.push({
      id: item[0],
      name: item[0],
      author: "",
      versions: releases(item[2]),
      path: item[1],
      outside: true,
    });
  }
  for (const entry of list) {
    entry.hay = [entry.id.toLowerCase(), entry.name.toLowerCase(), entry.author.toLowerCase()];
  }
  return list;
}

// Lower is better, -1 is no match.
function score(entry, q) {
  const [id, name, author] = entry.hay;
  if (id === q || name === q) return 0;
  if (id.startsWith(q) || name.startsWith(q)) return 1;
  if (id.includes("." + q) || id.includes("-" + q) || name.includes(" " + q)) return 2;
  if (id.includes(q) || name.includes(q)) return 3;
  if (author.includes(q)) return 4;
  return -1;
}

// The query as typed, lowercase, with a GitHub URL cut down to owner/repo.
function normalize(query) {
  return text(query)
    .trim()
    .toLowerCase()
    .replace(/^(https?:\/\/)?(www\.)?github\.com\//, "")
    .replace(/(\.git)?\/?$/, "");
}

// Every match, best first. Plugins with reports come before those without.
function search(list, query) {
  const q = normalize(query);
  if (!q) return [];
  const found = [];
  for (const entry of list) {
    const s = score(entry, q);
    if (s >= 0) found.push([s, entry.versions.length ? 0 : 1, entry.id, entry]);
  }
  found.sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
  return found.map((f) => f[3]);
}

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}

function result(entry) {
  const item = element("li");
  const link = element("a");
  link.href = entry.path;
  link.append(element("span", "name", entry.name));
  item.append(link);
  if (entry.name !== entry.id) item.append(element("code", "", entry.id));
  if (entry.author) item.append(element("span", "muted", `by ${entry.author}`));
  if (entry.outside) item.append(element("span", "tag", "not in the marketplace"));
  if (entry.versions.length) {
    item.append(element("span", "muted", `Reports on Omarchy ${entry.versions.join(", ")}`));
  } else {
    item.append(element("span", "status status-none", "No reports yet"));
  }
  return item;
}

function start() {
  const input = document.getElementById("q");
  const results = document.getElementById("results");
  const status = document.getElementById("search-status");
  const notFound = document.getElementById("not-found");
  if (!input || !results || !status) return;
  let list = null;
  let shown = [];

  function update() {
    results.replaceChildren();
    if (notFound) notFound.hidden = true;
    if (list === null) return;
    const q = normalize(input.value);
    if (!q) {
      status.textContent = `${list.length} plugins. Type a name, an ID or an author.`;
      shown = [];
      return;
    }
    const found = search(list, input.value);
    shown = found.slice(0, MAX_RESULTS);
    for (const entry of shown) results.append(result(entry));
    if (!found.length) {
      status.textContent = "No plugin matches.";
      if (notFound) notFound.hidden = false;
    } else if (found.length > shown.length) {
      status.textContent = `Showing ${shown.length} of ${found.length}. Type more to narrow it down.`;
    } else {
      status.textContent = found.length === 1 ? "1 plugin matches." : `${found.length} plugins match.`;
    }
  }

  input.addEventListener("input", update);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && shown.length) window.location.href = shown[0].path;
  });

  status.textContent = "Loading the plugin list…";
  fetch(input.dataset.index)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((index) => {
      list = entries(index);
      update();
    })
    .catch(() => {
      status.textContent = "The plugin list couldn't be loaded. Reload the page to try again.";
    });
}

if (typeof document !== "undefined") start();
if (typeof module !== "undefined") module.exports = { entries, normalize, search };
