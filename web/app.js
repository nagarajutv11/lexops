const app = document.querySelector("#app");
let meta = {
  short_disclaimer: "Not legal advice. Human review required for reliance.",
  disclaimer: "",
  contract_types: ["MSA", "NDA", "DPA", "Reseller", "SOW", "Vendor terms"],
};
let filter = "";
let modal = null;
let editOpen = false;
let viewRound = null;
let viewDealId = null;
let activityPage = 0;
let tracesOpen = false;
const ACTIVITY_PAGE = 5;
let pollTimer = 0;
let shownDeal = null;
let lastDealKey = "";
let dealEpoch = 0;

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function when(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_err) {
      /* keep status text */
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response;
}

function route() {
  const hash = location.hash || "#/";
  const match = hash.match(/^#\/deals\/(\d+)$/);
  return match ? { name: "deal", id: Number(match[1]) } : { name: "list" };
}

function banner() {
  return `<div class="banner">${esc(meta.short_disclaimer)}</div>`;
}

function statusChip(status, label) {
  return `<span class="status ${esc(status)}">${esc(label)}</span>`;
}

async function boot() {
  try {
    meta = await api("/api/meta");
  } catch (_err) {
    /* page still renders with the built-in disclaimer */
  }
  window.addEventListener("hashchange", render);
  render();
}

function render() {
  clearTimeout(pollTimer);
  const page = route();
  if (page.name === "deal") renderDeal(page.id);
  else {
    dealEpoch += 1;
    shownDeal = null;
    lastDealKey = "";
    renderList();
  }
}

async function renderList() {
  app.innerHTML = `<div class="app"><p class="quiet">Loading deals…</p></div>`;
  let data;
  try {
    const query = filter ? `?status=${encodeURIComponent(filter)}` : "";
    data = await api(`/api/deals${query}`);
  } catch (err) {
    app.innerHTML = `<div class="app"><p class="error">${esc(err.message)}</p></div>`;
    return;
  }
  const counts = data.counts;
  const chips = [
    ["", "All", null],
    ["in_review", "In review", counts.in_review],
    ["waiting_on_counsel", "Waiting on counsel", counts.waiting_on_counsel],
    ["changes_requested", "Changes requested", counts.changes_requested],
    ["approved", "Approved", counts.approved],
    ["rejected", "Rejected", counts.rejected],
  ];
  if (counts.blocked) chips.push(["blocked", "Blocked", counts.blocked]);
  if (counts.needs_human) chips.push(["needs_human", "Parse failed", counts.needs_human]);
  const rows = data.deals.map((deal) => `
    <tr class="clickable" data-id="${deal.id}">
      <td>${esc(deal.customer)}</td>
      <td>${esc(deal.contract_type)}</td>
      <td>${esc(deal.round_number)}</td>
      <td>${statusChip(deal.status, deal.status_label)}</td>
      <td>${deal.tier ? esc("Tier " + deal.tier) : "—"}</td>
      <td>${deal.score === null || deal.score === undefined ? "—" : esc(deal.score)}</td>
      <td>${esc(when(deal.updated_at))}</td>
    </tr>
  `).join("");
  app.innerHTML = `
    <div class="app">
      <header class="top">
        <div>
          <h1 class="brand">Lex<span>Ops</span></h1>
          <p class="quiet">Submit a pasted clause. The deal page opens as soon as it is saved, and extraction starts after that.</p>
        </div>
        <button class="btn" id="new-deal">New deal</button>
      </header>
      ${banner()}
      <div class="filters row" id="filters">
        ${chips.map(([id, label, count]) => `
          <button class="chip ${filter === id ? "active" : ""}" data-filter="${esc(id)}">
            ${esc(label)}${count === null ? "" : ` <strong>${esc(count)}</strong>`}
          </button>
        `).join("")}
      </div>
      <div class="card">
        ${data.deals.length ? `
          <table>
            <thead>
              <tr>
                <th>Customer</th><th>Contract type</th><th>Round</th>
                <th>Status</th><th>Tier</th><th>Score</th><th>Updated</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        ` : `<p class="empty">${filter ? "No deals in this status." : "No deals yet."}</p>`}
      </div>
    </div>
    ${modal ? formHtml(modal) : ""}
  `;
  document.querySelector("#new-deal").onclick = () => {
    modal = { mode: "new" };
    render();
  };
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.onclick = () => {
      filter = button.dataset.filter;
      render();
    };
  });
  document.querySelectorAll("tr.clickable").forEach((row) => {
    row.onclick = () => {
      modal = null;
      location.hash = `#/deals/${row.dataset.id}`;
    };
  });
  bindForm();
}

function formHtml(state) {
  const locked = state.mode === "update";
  const types = meta.contract_types.map((type) => `
    <option value="${esc(type)}" ${type === state.contract_type ? "selected" : ""}>${esc(type)}</option>
  `).join("");
  return `
    <div class="modal" id="modal">
      <form class="sheet" id="deal-form">
        <h2>${locked ? "Submit customer's update" : "New deal"}</h2>
        <label for="customer">Customer</label>
        <input id="customer" name="customer" type="text" value="${esc(state.customer || "")}" ${locked ? "readonly" : ""} required>
        <label for="contract_type">Contract type</label>
        <select id="contract_type" name="contract_type" ${locked ? "disabled" : ""}>${types}</select>
        <label for="contract_text">Contract text</label>
        <textarea id="contract_text" name="contract_text" required placeholder="Paste the agreement or the clause you received"></textarea>
        <p class="help">Paste the clause. Submit saves the deal and opens it. Extraction starts after that.</p>
        ${state.error ? `<p class="error">${esc(state.error)}</p>` : ""}
        <div class="form-actions">
          <button type="button" class="btn-ghost" id="cancel-form">Cancel</button>
          <button class="btn" type="submit">Submit</button>
        </div>
      </form>
    </div>
  `;
}

function bindForm() {
  const form = document.querySelector("#deal-form");
  if (!form || !modal) return;
  document.querySelector("#cancel-form").onclick = () => {
    modal = null;
    render();
  };
  document.querySelector("#modal").onclick = (event) => {
    if (event.target.id === "modal") {
      modal = null;
      render();
    }
  };
  form.onsubmit = async (event) => {
    event.preventDefault();
    const submit = form.querySelector("button[type=submit]");
    submit.disabled = true;
    submit.textContent = "Saving…";
    const data = new FormData(form);
    const body = {
      contract_text: data.get("contract_text"),
    };
    try {
      let deal;
      if (modal.mode === "update") {
        deal = await api(`/api/deals/${modal.dealId}/rounds`, { method: "POST", body: JSON.stringify(body) });
      } else {
        deal = await api("/api/deals", {
          method: "POST",
          body: JSON.stringify({
            customer: data.get("customer"),
            contract_type: data.get("contract_type"),
            ...body,
          }),
        });
      }
      modal = null;
      editOpen = false;
      location.hash = `#/deals/${deal.id}`;
      render();
    } catch (err) {
      modal.error = err.message;
      render();
    }
  };
}

function dealStillOpen(deal) {
  return deal.round.status === "in_review";
}

function scheduleDealPoll(id, deal) {
  clearTimeout(pollTimer);
  if (!dealStillOpen(deal)) return;
  pollTimer = setTimeout(() => pollDeal(id), 1200);
}

async function pollDeal(id) {
  if (route().name !== "deal" || route().id !== id) return;
  if (modal || editOpen) {
    pollTimer = setTimeout(() => pollDeal(id), 1200);
    return;
  }
  const epoch = ++dealEpoch;
  let deal;
  try {
    deal = await api(`/api/deals/${id}`);
  } catch (_err) {
    if (epoch === dealEpoch && route().name === "deal" && route().id === id) {
      pollTimer = setTimeout(() => pollDeal(id), 1200);
    }
    return;
  }
  if (epoch !== dealEpoch || route().name !== "deal" || route().id !== id) return;
  if (modal || editOpen) {
    pollTimer = setTimeout(() => pollDeal(id), 1200);
    return;
  }
  const key = JSON.stringify(deal);
  shownDeal = deal;
  if (key !== lastDealKey) {
    const y = window.scrollY;
    paintDeal(id, deal);
    window.scrollTo(0, y);
    lastDealKey = key;
  }
  scheduleDealPoll(id, deal);
}

async function renderDeal(id) {
  const epoch = ++dealEpoch;
  clearTimeout(pollTimer);
  if (viewDealId !== id) {
    viewRound = null;
    viewDealId = id;
    editOpen = false;
    activityPage = 0;
    tracesOpen = false;
    shownDeal = null;
    lastDealKey = "";
  }
  if (shownDeal && shownDeal.id === id) {
    paintDeal(id, shownDeal);
    lastDealKey = JSON.stringify(shownDeal);
  } else {
    app.innerHTML = `<div class="app"><p class="quiet">Loading deal…</p></div>`;
  }
  let deal;
  try {
    deal = await api(`/api/deals/${id}`);
  } catch (err) {
    if (epoch !== dealEpoch) return;
    if (!document.querySelector("#back")) {
      app.innerHTML = `<div class="app"><button class="back" id="back">Back</button><p class="error">${esc(err.message)}</p></div>`;
      document.querySelector("#back").onclick = () => { location.hash = "#/"; };
    }
    return;
  }
  if (epoch !== dealEpoch || route().name !== "deal" || route().id !== id) return;
  const key = JSON.stringify(deal);
  const editing = document.querySelector("#deal-form, #redline-form, #traces-modal");
  shownDeal = deal;
  if (key !== lastDealKey && !editing) {
    const y = document.querySelector("#back") ? window.scrollY : 0;
    paintDeal(id, deal);
    if (y) window.scrollTo(0, y);
    lastDealKey = key;
  }
  scheduleDealPoll(id, deal);
}

function paintDeal(id, deal) {
  const current = deal.round;
  const round = [current, ...deal.earlier_rounds].find((item) => item.round_number === viewRound) || current;
  const viewingPast = round.round_number !== current.round_number;
  const actions = viewingPast ? {} : current.actions;
  app.innerHTML = `
    <div class="app">
      <button class="back" id="back">Back to deals</button>
      <div class="title-row">
        <h1 class="title">${esc(deal.customer)}</h1>
        <button class="btn-ghost" id="show-traces" type="button">Show traces</button>
      </div>
      <p class="sample">${roundNote(round)}</p>
      ${viewingPast ? `<p class="flag">Showing round ${esc(round.round_number)}. The current round is ${esc(current.round_number)}. <button type="button" class="back" id="current-round">Back to current round</button></p>` : ""}
      <div class="meta">
        <span class="pill">${esc(deal.contract_type)}</span>
        <span class="pill">Round ${esc(round.round_number)}</span>
        ${statusChip(round.status, round.status_label)}
        ${round.tier ? `<span class="pill">Tier ${esc(round.tier)}</span>` : ""}
        ${round.band ? `<span class="pill">${esc(round.band)}</span>` : ""}
        ${round.score !== null && round.score !== undefined ? `<span class="pill">Score ${esc(round.score)}</span>` : ""}
        ${round.turnaround_days ? `<span class="pill">${esc(round.turnaround_days)} business days</span>` : ""}
        ${round.path_label ? `<span class="pill">${esc(round.path_label)}</span>` : ""}
      </div>
      ${banner()}
      ${round.status === "in_review" || round.status === "needs_human" ? stepsHtml(round.steps) : ""}
      ${round.block_reasons.length ? `<ul class="reasons">${round.block_reasons.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}
      <div class="actions">
        ${actions.edit_redline ? `<button class="btn-ghost" id="edit">Edit redline</button>` : ""}
        ${actions.approve ? `<button class="btn" id="approve">Approve</button>` : ""}
        ${actions.changes ? `<button class="btn-ghost" id="changes">Changes requested</button>` : ""}
        ${actions.reject ? `<button class="btn-danger" id="reject">Reject</button>` : ""}
        ${actions.submit_update ? `<button class="btn" id="update">Submit update</button>` : ""}
        ${actions.ceo_signoff ? `<button class="btn" id="ceo">Record CEO sign-off</button>` : ""}
      </div>
      <div class="columns">
        <div>${workHtml(deal, round)}</div>
        <div>${decisionHtml(deal, round)}</div>
      </div>
    </div>
    ${modal ? formHtml(modal) : ""}
    ${tracesOpen ? tracesHtml(round) : ""}
  `;
  document.querySelector("#back").onclick = () => { location.hash = "#/"; };
  document.querySelector("#show-traces").onclick = () => {
    tracesOpen = true;
    renderDeal(id);
  };
  const tracesModal = document.querySelector("#traces-modal");
  if (tracesModal) {
    document.querySelector("#close-traces").onclick = () => {
      tracesOpen = false;
      renderDeal(id);
    };
    tracesModal.onclick = (event) => {
      if (event.target.id === "traces-modal") {
        tracesOpen = false;
        renderDeal(id);
      }
    };
  }
  const currentRound = document.querySelector("#current-round");
  if (currentRound) {
    currentRound.onclick = () => {
      viewRound = null;
      editOpen = false;
      tracesOpen = false;
      renderDeal(id);
    };
  }
  bindAction(deal, "edit", () => { editOpen = !editOpen; renderDeal(id); });
  bindAction(deal, "approve", () => postAction(id, "/approve"));
  bindAction(deal, "changes", () => postAction(id, "/changes"));
  bindAction(deal, "reject", () => postAction(id, "/reject"));
  bindAction(deal, "ceo", () => postAction(id, "/ceo-signoff"));
  const update = document.querySelector("#update");
  if (update) {
    update.onclick = () => {
      modal = {
        mode: "update",
        dealId: deal.id,
        customer: deal.customer,
        contract_type: deal.contract_type,
      };
      renderDeal(id);
    };
  }
  const editForm = document.querySelector("#redline-form");
  if (editForm) {
    editForm.onsubmit = async (event) => {
      event.preventDefault();
      const data = new FormData(editForm);
      try {
        await api(`/api/deals/${id}/redline`, {
          method: "POST",
          body: JSON.stringify({
            redline_text: data.get("redline_text"),
            liability_cap_redline: data.get("liability_cap_redline") === "on",
          }),
        });
        editOpen = false;
        renderDeal(id);
      } catch (err) {
        editForm.insertAdjacentHTML("beforeend", `<p class="error">${esc(err.message)}</p>`);
      }
    };
    document.querySelector("#cancel-edit").onclick = () => {
      editOpen = false;
      renderDeal(id);
    };
  }
  document.querySelectorAll("[data-round]").forEach((button) => {
    button.onclick = () => {
      viewRound = Number(button.dataset.round);
      editOpen = false;
      tracesOpen = false;
      renderDeal(id);
    };
  });
  const prev = document.querySelector("#activity-prev");
  const next = document.querySelector("#activity-next");
  if (prev) {
    prev.onclick = () => {
      activityPage = Math.max(0, activityPage - 1);
      renderDeal(id);
    };
  }
  if (next) {
    next.onclick = () => {
      activityPage += 1;
      renderDeal(id);
    };
  }
  bindForm();
}

function bindAction(_deal, id, action) {
  const button = document.querySelector(`#${id}`);
  if (button) button.onclick = action;
}

async function postAction(id, path) {
  try {
    await api(`/api/deals/${id}${path}`, { method: "POST" });
    editOpen = false;
    renderDeal(id);
  } catch (err) {
    alert(err.message);
  }
}

const TRACE_LABELS = {
  saved: "Saved",
  extracting: "Extracting",
  checking_playbook: "Checking playbook",
  drafting_redline: "Drafting redline",
  routing: "Routing",
  end: "End",
};

function tracesHtml(round) {
  const traces = [...(round.traces || [])].reverse();
  const rows = traces.length
    ? traces.map((item) => {
      const level = item.level === "error" ? "error" : "info";
      return `
      <li class="${level}">
        <strong>${esc(TRACE_LABELS[item.step] || item.step)}</strong>
        <span class="trace-level">${level === "error" ? "Error" : "Info"}</span>
        <p>${esc(item.detail)}</p>
        <time>${esc(when(item.at))}</time>
      </li>
    `;
    }).join("")
    : `<p class="quiet">No traces yet for this round.</p>`;
  return `
    <div class="modal" id="traces-modal">
      <div class="sheet traces-sheet">
        <h2>Traces · Round ${esc(round.round_number)}</h2>
        <p class="quiet">Latest first.</p>
        <ul class="traces">${rows}</ul>
        <div class="form-actions">
          <button type="button" class="btn" id="close-traces">Close</button>
        </div>
      </div>
    </div>
  `;
}

function roundNote(round) {
  if (!round.extracted && round.status === "in_review") {
    return "This deal is saved. Extraction is running on the pasted text.";
  }
  if (round.status === "needs_human") {
    return "Extraction failed. The supervisor did not send this deal to Playbook.";
  }
  if (round.status === "approved") {
    return "Standard language. This round was auto-approved.";
  }
  if (round.status === "waiting_on_counsel") {
    return "The redline is ready. This round is waiting on counsel.";
  }
  if (round.status === "blocked") {
    return "This round stopped before a decision.";
  }
  if (round.playbook_status && !round.redline) {
    return "The supervisor sent this extract to Playbook.";
  }
  return "Extraction ran on the pasted text for this round.";
}

function stepsHtml(steps) {
  return `<div class="steps">${steps.map((step) => `<span class="step ${esc(step.state)}">${esc(step.label)}</span>`).join("")}</div>`;
}

function redlineHtml(deal, round) {
  const edit = editOpen && round.actions.edit_redline ? `
    <form id="redline-form">
      <label for="redline_text">Redline</label>
      <textarea id="redline_text" name="redline_text" required>${esc(round.redline)}</textarea>
      <label class="check">
        <input type="checkbox" name="liability_cap_redline" ${round.liability_cap_redline ? "checked" : ""}>
        <span>This redline changes the liability cap.</span>
      </label>
      <div class="form-actions">
        <button type="button" class="btn-ghost" id="cancel-edit">Cancel</button>
        <button class="btn" type="submit">Save</button>
      </div>
    </form>
  ` : "";
  return `
    <section class="card panel">
      <h2>Redline</h2>
      <p class="quiet">Suggested markup for this round, and the memo counsel can download.</p>
      ${round.redline ? `<div class="redline">${esc(round.redline)}</div>` : `<p class="quiet">Waiting for the redline.</p>`}
      ${edit}
      ${round.memo_name ? `<p><a href="/api/deals/${deal.id}/rounds/${round.id}/memo">Download memo</a></p>` : ""}
      ${meta.disclaimer ? `<p class="disclaimer">${esc(meta.disclaimer)}</p>` : ""}
    </section>
  `;
}

const FAMILY = {
  term: "Term",
  termination: "Termination",
  liability_cap: "Liability cap",
  indemnification: "Indemnification",
  governing_law: "Governing law",
};

function extractionHtml(round) {
  const fields = (round.extraction || []).map((field) => `
    <div class="field"><span>${esc(field.field)}</span><div>${field.error ? `<em>${esc(field.error)}</em>` : esc(field.value)}</div></div>
  `).join("");
  const clauses = (round.clauses || []).length ? `
    <table class="clauses">
      <thead><tr><th>Category</th><th>Quoted span</th><th>Location</th></tr></thead>
      <tbody>
        ${round.clauses.map((clause) => `
          <tr>
            <td>${esc(FAMILY[clause.category] || clause.category)}</td>
            <td>${esc(clause.text)}</td>
            <td>${esc(clause.location)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  ` : "";
  const raw = round.raw_json ? `
    <details class="raw">
      <summary>Model JSON</summary>
      <pre>${esc(round.raw_json)}</pre>
    </details>
  ` : "";
  const waiting = !round.extracted && round.status === "in_review";
  const body = fields
    ? fields
    : `<p class="quiet">${waiting
      ? "Extraction is running. The five clause families show up here when it finishes."
      : "Five clause families appear here after the deal is stored. This panel does not give a legal conclusion."}</p>`;
  return `
    <section class="card panel">
      <h2>Extraction</h2>
      ${body}
      ${clauses}
      ${raw}
    </section>
  `;
}

function workHtml(deal, round) {
  return `
    <section class="card panel">
      <h2>Submitted text</h2>
      <div class="submitted">${esc(round.contract_text)}</div>
    </section>
    ${extractionHtml(round)}
    <section class="card panel">
      <h2>Playbook</h2>
      ${round.playbook.length ? round.playbook.map((item) => `
        <div class="family">
          <h3>${esc(item.family)}</h3>
          <p><strong>Preferred.</strong> ${esc(item.preferred)}</p>
          <p><strong>Fallback.</strong> ${esc(item.fallback)}</p>
          <p><strong>Walk-away.</strong> ${esc(item.walk_away)}</p>
          <span class="cite">${esc(item.citation_title)} · ${esc(item.chunk_id)}</span>
        </div>
      `).join("") : `<p class="quiet">${round.playbook_status === "not_in_playbook" ? "Not in the playbook." : "Waiting for the playbook match."}</p>`}
    </section>
    ${activityHtml(deal)}
  `;
}

function dealActivity(deal) {
  const items = [];
  for (const round of [deal.round, ...deal.earlier_rounds]) {
    for (const item of [...round.activity].reverse()) {
      items.push({ ...item, round_number: round.round_number });
    }
  }
  return items;
}

function activityHtml(deal) {
  const items = dealActivity(deal);
  const pages = Math.max(1, Math.ceil(items.length / ACTIVITY_PAGE));
  if (activityPage > pages - 1) activityPage = pages - 1;
  if (activityPage < 0) activityPage = 0;
  const start = activityPage * ACTIVITY_PAGE;
  const slice = items.slice(start, start + ACTIVITY_PAGE);
  const rows = slice.length
    ? slice.map((item) => `
      <li>
        <button type="button" class="round-link" data-round="${item.round_number}">Round ${esc(item.round_number)}</button>
        <strong>${esc(item.actor)}</strong> ${esc(item.action)}
        <time>${esc(when(item.at))}</time>
      </li>
    `).join("")
    : `<li class="quiet">No activity yet.</li>`;
  const pager = pages > 1 ? `
    <div class="pager">
      <button type="button" class="btn-ghost" id="activity-prev" ${activityPage === 0 ? "disabled" : ""}>Previous</button>
      <span>${start + 1}–${start + slice.length} of ${items.length}</span>
      <button type="button" class="btn-ghost" id="activity-next" ${activityPage >= pages - 1 ? "disabled" : ""}>Next</button>
    </div>
  ` : "";
  return `
    <section class="card panel">
      <h2>Activity</h2>
      <p class="quiet">Every round of this deal, newest first.</p>
      ${pager}
      <ul class="activity">${rows}</ul>
    </section>
  `;
}

function decisionHtml(deal, round) {
  const facts = deal.memory.facts.length
    ? deal.memory.facts.map((fact) => `<p><span class="kind">${esc(fact.kind)}</span>${esc(fact.text)}</p>`).join("")
    : `<p class="quiet">No prior history for this customer.</p>`;
  const rounds = [deal.round, ...deal.earlier_rounds];
  const roundList = rounds.map((item) => `
      <button class="round ${item.round_number === round.round_number ? "active" : ""}" data-round="${item.round_number}" type="button">
        Round ${esc(item.round_number)}${item.round_number === deal.round.round_number ? " · Current" : ""} · ${esc(item.status_label)} · ${esc(when(item.updated_at))}
      </button>
    `).join("");
  return `
    ${redlineHtml(deal, round)}
    <section class="card panel">
      <h2>Decision</h2>
      <div class="field"><span>Score</span><div>${round.score === null || round.score === undefined ? "—" : esc(round.score)}</div></div>
      <div class="field"><span>Band</span><div>${esc(round.band || "—")}</div></div>
      <div class="field"><span>Tier</span><div>${round.tier ? esc("Tier " + round.tier) : "—"}</div></div>
      <div class="field"><span>Route</span><div>${esc(round.route_reason || "The route is still running.")}</div></div>
    </section>
    <section class="card panel">
      <h2>This customer · ${esc(deal.counterparty_id)}</h2>
      ${deal.memory.posture ? `<p>${esc(deal.memory.posture)}</p>` : ""}
      <p class="quiet">Context for this customer. It does not turn Approve on.</p>
      ${facts}
    </section>
    <section class="card panel">
      <h2>Envelope</h2>
      <p>${round.envelope_sent_at ? `Sent ${esc(when(round.envelope_sent_at))}` : "Not sent."}</p>
    </section>
    <section class="card panel">
      <h2>Rounds</h2>
      <p class="quiet">Every submission of this deal. Open one to show that version.</p>
      ${roundList}
    </section>
  `;
}

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (tracesOpen) {
    tracesOpen = false;
    render();
    return;
  }
  if (modal) {
    modal = null;
    render();
  }
});

boot();
