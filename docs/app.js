/* Radar PhD — PWA senza build. Legge docs/data/*.json; stato utente in localStorage. */
(function () {
  "use strict";

  // ---------- stato ----------
  const D = { positions: [], unis: [], alerts: [], meta: {} };
  const ui = { q: "", uni: "Tutte", uniTab: "come" };
  const view = document.getElementById("view");

  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem("radar." + key); return v === null ? fallback : JSON.parse(v); }
      catch (e) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem("radar." + key, JSON.stringify(value)); } catch (e) { /* storage non disponibile */ }
    },
  };

  // ---------- utilità ----------
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^(https?:|mailto:)/i.test(String(u || "")) ? String(u) : "#");
  const DASH = "—";

  const pad = (n) => String(n).padStart(2, "0");
  const isoLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const today = () => isoLocal(new Date());
  const parseDay = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(y, m - 1, d); };
  const daysUntil = (iso) => Math.round((parseDay(iso) - parseDay(today())) / 86400000);
  const fmtDay = new Intl.DateTimeFormat("it-IT", { day: "numeric", month: "short", year: "numeric" });
  const fmtDate = (iso) => (iso ? fmtDay.format(parseDay(iso)).replace(".", "") : DASH);
  const fmtHead = new Intl.DateTimeFormat("it-IT", { weekday: "long", day: "numeric", month: "long" });
  const fmtTime = new Intl.DateTimeFormat("it-IT", { hour: "2-digit", minute: "2-digit" });

  function relTime(ts) {
    if (!ts) return DASH;
    const s = Math.max(0, (Date.now() - new Date(ts).getTime()) / 1000);
    if (s < 60) return "ora";
    if (s < 3600) return `${Math.floor(s / 60)} min fa`;
    if (s < 86400) return `${Math.floor(s / 3600)} h fa`;
    const d = Math.floor(s / 86400);
    return d === 1 ? "ieri" : `${d} gg fa`;
  }

  // "MM-DD" -> prossima occorrenza (oggi compreso) in ISO
  function nextRecurring(mmdd) {
    const t = today();
    const y = Number(t.slice(0, 4));
    const cand = `${y}-${mmdd}`;
    return cand >= t ? cand : `${y + 1}-${mmdd}`;
  }

  // ---------- dominio ----------
  const uniById = (id) => D.unis.find((u) => u.id === id);
  const uniName = (id) => (uniById(id) ? uniById(id).name : id === "UK" ? "Altri atenei UK" : id);
  const uniShort = (id) => (id === "UK" ? "UK" : id);

  function sourceName(url) {
    for (const u of D.unis) for (const s of u.sources || []) if (s.url === url) return s.name;
    try { return new URL(url).hostname.replace(/^www\./, ""); } catch (e) { return ""; }
  }

  function status(p) {
    if (!p.deadline) return { cls: "open", label: "Aperta" };
    const d = daysUntil(p.deadline);
    if (d < 0) return { cls: "past", label: "Scaduta" };
    if (d < 30) return { cls: "soon", label: d === 0 ? "Scade oggi" : `Scade tra ${d} gg` };
    return { cls: "open", label: "Aperta" };
  }
  const isPast = (p) => p.deadline && daysUntil(p.deadline) < 0;
  const isSoon = (p) => p.deadline && daysUntil(p.deadline) >= 0 && daysUntil(p.deadline) < 30;
  const isNew = (p) => p.first_seen && isoLocal(new Date(p.first_seen)) === today();

  function deadlineHtml(iso) {
    if (!iso) return `<span class="deadline muted">Scadenza ${DASH}</span>`;
    const d = daysUntil(iso);
    const cls = d < 0 ? "past" : d < 30 ? "soon" : "";
    return `<span class="deadline ${cls}">${esc(fmtDate(iso))}</span>`;
  }

  function uniDeadlines(u) {
    return (u.deadlines || []).map((d) => ({ ...d, when: d.date || (d.recurring ? nextRecurring(d.recurring) : null) }));
  }

  function nextDeadline(u) {
    const t = today();
    const dates = uniDeadlines(u).map((d) => d.when)
      .concat(D.positions.filter((p) => p.uni === u.id).map((p) => p.deadline))
      .filter((x) => x && x >= t).sort();
    return dates[0] || null;
  }

  const activeKeywords = () => store.get("kw.active", []);
  const allKeywords = () => {
    const base = D.meta.keywords || [];
    const extra = store.get("kw.custom", []);
    return base.concat(extra.filter((k) => !base.includes(k)));
  };
  const matchesKeywords = (p, kws) => {
    if (!kws.length) return true;
    const hay = (p.title + " " + (p.snippet || "") + " " + (p.keywords || []).join(" ")).toLowerCase();
    return kws.some((k) => hay.includes(k));
  };

  const lastSeenAlert = () => store.get("alerts.seen", "");
  const hasUnread = () => D.alerts.some((a) => a.created_at > lastSeenAlert());

  // ---------- icone ----------
  const I = {
    search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    bell: '<svg viewBox="0 0 24 24"><path d="M6 16V11a6 6 0 1112 0v5l2 2H4l2-2z"/><path d="M10 20a2 2 0 004 0"/></svg>',
    back: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>',
    ext: '<svg viewBox="0 0 24 24"><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/></svg>',
    mark: '<svg viewBox="0 0 24 24"><path d="M6 4h12v17l-6-4-6 4z"/></svg>',
    markOn: '<svg viewBox="0 0 24 24"><path class="fill" d="M6 4h12v17l-6-4-6 4z"/></svg>',
    mail: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    cal: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
    plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
    page: '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h6"/></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  };

  // ---------- componenti ----------
  function posCard(p) {
    const st = status(p);
    return `<a class="card" href="#/p/${esc(p.id)}">
      <div class="head">${isNew(p) ? '<i class="newdot" title="Nuova"></i>' : ""}
        <span class="src">${esc(uniShort(p.uni))} · ${esc(sourceName(p.source_url))}</span>
        <span class="badge ${st.cls}">${esc(st.label)}</span></div>
      <h3>${esc(p.title)}</h3>
      <div class="foot"><span class="sub">${esc(uniName(p.uni))}</span>${deadlineHtml(p.deadline)}</div>
    </a>`;
  }

  function contactRows(u) {
    const cs = (u && u.contacts) || [];
    if (!cs.length) return `<p class="note">Nessun contatto pubblicato sulle pagine lette. Controlla le fonti.</p>`;
    return cs.map((c) => `<div class="contact">
        <div class="who"><b>${esc(c.name || c.role)}</b>
          <span>${c.name ? esc(c.role) + (c.email ? " · " : "") : ""}${c.email ? esc(c.email) : ""}${c.phone ? " · " + esc(c.phone) : ""}</span></div>
        ${c.email ? `<a class="btn" href="mailto:${esc(c.email)}">${I.mail}Scrivi email</a>` : ""}
      </div>`).join("");
  }

  // ---------- viste ----------
  function vRadar() {
    const meta = D.meta.updated_at ? new Date(D.meta.updated_at) : null;
    const kws = activeKeywords();
    const base = D.positions.filter((p) => matchesKeywords(p, kws));
    const q = ui.q.trim().toLowerCase();
    const list = base
      .filter((p) => ui.uni === "Tutte" || p.uni === ui.uni)
      .filter((p) => !q || (p.title + " " + (p.snippet || "")).toLowerCase().includes(q))
      .sort((a, b) => (isPast(a) - isPast(b)) || (a.deadline || "9999").localeCompare(b.deadline || "9999"));
    const chips = ["Tutte"].concat(D.unis.map((u) => u.id));
    if (D.positions.some((p) => p.uni === "UK")) chips.push("UK");
    const count = (id) => base.filter((p) => id === "Tutte" || p.uni === id).length;
    return `
      <header class="top">
        <div><div class="meta">${esc(fmtHead.format(new Date()))}${meta ? " · Aggiornato " + esc(fmtTime.format(meta)) : ""}</div>
        <h1>Radar PhD</h1></div>
        <a class="iconbtn" href="#/avvisi" aria-label="Avvisi">${I.bell}${hasUnread() ? '<i class="dot"></i>' : ""}</a>
      </header>
      <label class="search">${I.search}<input id="q" type="search" placeholder="Cerca titolo o descrizione" value="${esc(ui.q)}" autocomplete="off"></label>
      <div class="tiles">
        <div class="tile"><b>${base.filter((p) => !isPast(p)).length}</b><span>Aperte</span></div>
        <div class="tile soon"><b>${base.filter(isSoon).length}</b><span>Scade &lt; 30 gg</span></div>
        <div class="tile"><b>${base.filter(isNew).length}</b><span>Nuove oggi</span></div>
      </div>
      ${kws.length ? `<div class="kwbar"><span>Filtro parole chiave: ${esc(kws.join(", "))}</span><a href="#/avvisi">Modifica</a></div>` : ""}
      <div class="chips" role="group" aria-label="Filtra per ateneo">
        ${chips.map((c) => `<button class="chip" data-uni="${esc(c)}" aria-pressed="${ui.uni === c}">${esc(c)}<span class="n">${count(c)}</span></button>`).join("")}
      </div>
      <div id="list">${list.length ? list.map(posCard).join("") :
        `<div class="empty">Nessuna posizione${q || ui.uni !== "Tutte" || kws.length ? " con questi filtri" : " trovata finora"}.</div>`}</div>`;
  }

  function vDetail(id) {
    const p = D.positions.find((x) => x.id === id);
    if (!p) return `<div class="bar"><button class="iconbtn" data-action="back" aria-label="Indietro">${I.back}</button></div>
      <div class="empty">Posizione non trovata (forse rimossa dall'ultimo aggiornamento).</div>`;
    const u = uniById(p.uni);
    const st = status(p);
    const saved = store.get("saved", []).includes(p.id);
    return `<div class="detail">
      <div class="bar"><button class="iconbtn" data-action="back" aria-label="Indietro">${I.back}</button>
        <div class="right">
          <button class="iconbtn" data-action="save" data-id="${esc(p.id)}" aria-pressed="${saved}" aria-label="${saved ? "Rimuovi dai salvati" : "Salva"}">${saved ? I.markOn : I.mark}</button>
          <a class="iconbtn" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener" aria-label="Apri annuncio originale">${I.ext}</a>
        </div></div>
      <div class="unirow">${esc(uniName(p.uni))} <span class="badge ${st.cls}">${esc(st.label)}</span></div>
      <h1>${esc(p.title)}</h1>
      ${p.snippet && p.snippet !== p.title ? `<p class="snippet">${esc(p.snippet)}</p>` : ""}
      <div class="grid4">
        <div><small>Scadenza</small><b>${esc(fmtDate(p.deadline))}</b></div>
        <div><small>Inizio</small><b>${DASH}</b></div>
        <div><small>Durata</small><b>${DASH}</b></div>
        <div><small>Finanziamento</small><b>${DASH}</b></div>
      </div>
      <a class="btn primary" style="width:100%;margin-top:10px" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener">${I.ext}Apri l'annuncio originale</a>
      <h2 class="sec">Come candidarsi</h2>
      <div class="panel">${u && u.steps && u.steps.length
        ? `<ol class="steps">${u.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
           <p class="note" style="margin-top:10px">Procedura generale di ${esc(u.name)}: l'annuncio può indicare passi specifici.</p>`
        : `<p class="note">Segui le istruzioni dell'annuncio originale.</p>`}</div>
      <h2 class="sec">Chi contattare</h2>
      <div class="panel">${u ? contactRows(u) : `<p class="note">Vedi i contatti indicati nell'annuncio.</p>`}
        ${p.deadline && !isPast(p) ? `<div class="btnrow">
          <button class="btn" data-action="ics" data-id="${esc(p.id)}">${I.cal}Aggiungi al calendario</button></div>` : ""}</div>
      <p class="srcfoot">Fonte: <a href="${esc(safeUrl(p.source_url))}" target="_blank" rel="noopener">${esc(sourceName(p.source_url))}</a>
        · controllato ${esc(relTime(p.last_checked))}</p>
    </div>`;
  }

  const GROUPS = [
    ["direct", "Posizione diretta", "Ti candidi a un annuncio specifico e vieni assunto come dottorando presso un professore."],
    ["doctoral_school", "Scuola dottorale + supervisore", "Domanda alla scuola dottorale entro le sue scadenze; serve un supervisore che ti accetti."],
    ["uk_admission", "Ammissione + borsa UK", "Domanda di ammissione al dottorato; il finanziamento (studentship o borsa) ha spesso scadenze anticipate."],
    ["us_department", "Ammissione di dipartimento USA", "Un ciclo all'anno: domanda al dipartimento in autunno, ingresso a settembre."],
  ];
  const MODEL_BADGE = {
    direct: ["direct", "Posizione diretta"], doctoral_school: ["cycle", "Scuola dottorale"],
    uk_admission: ["cycle", "Ammissione UK"], us_department: ["cycle", "Ciclo annuale USA"],
  };

  function vAtenei() {
    return `<header class="top"><div><div class="meta">${D.unis.length} atenei monitorati</div><h1>Atenei</h1></div></header>
      ${GROUPS.map(([model, title, expl]) => {
        const us = D.unis.filter((u) => u.model === model);
        if (!us.length) return "";
        return `<section class="group"><h2>${esc(title)}</h2><p class="expl">${esc(expl)}</p>
          ${us.map((u) => {
            const open = D.positions.filter((p) => p.uni === u.id && !isPast(p)).length;
            const nd = nextDeadline(u);
            return `<a class="card unirow-card" href="#/ateneo/${esc(u.id)}">
              <div class="txt"><b>${esc(u.name)}</b><span>${esc((u.departments || []).join(" · "))}</span></div>
              <div class="right"><span class="badge ${open ? "open" : "direct"}">${open ? open + " aperte" : "nessuna"}</span>
                <small>${nd ? "prossima " + esc(fmtDate(nd)) : u.rolling ? "tutto l'anno" : "scadenza " + DASH}</small></div>
            </a>`;
          }).join("")}</section>`;
      }).join("")}`;
  }

  function vAteneo(id) {
    const u = uniById(id);
    if (!u) return `<div class="bar"><button class="iconbtn" data-action="back" aria-label="Indietro">${I.back}</button></div><div class="empty">Ateneo non trovato.</div>`;
    const [bcls, blabel] = MODEL_BADGE[u.model] || ["direct", u.model];
    const pc = u.photo_credit;
    const credit = pc ? `Foto: <a href="${esc(safeUrl(pc.url))}" target="_blank" rel="noopener">${esc(pc.author)}</a>, ${
      pc.license_url ? `<a href="${esc(safeUrl(pc.license_url))}" target="_blank" rel="noopener">${esc(pc.license)}</a>` : esc(pc.license)}, via Wikimedia Commons${pc.modified ? " (" + esc(pc.modified) + ")" : ""}` : "";
    const tabs = [["come", "Come funziona"], ["contatti", "Contatti"], ["fonti", "Fonti"]];
    return `<div class="hero" style="background-image:url('${esc(u.photo)}')">
        <button class="iconbtn back" data-action="back" aria-label="Indietro">${I.back}</button>
        <div class="inner"><div class="loc">${esc(u.city || "")}${u.city ? " · " : ""}${esc((u.departments || []).join(" · "))}</div>
          <h1>${esc(u.name)}</h1><span class="badge ${bcls}">${esc(blabel)}</span>
          ${credit ? `<div class="credit">${credit}</div>` : ""}</div>
      </div>
      <div class="seg" role="tablist">${tabs.map(([k, l]) => `<button role="tab" data-tab="${k}" aria-selected="${ui.uniTab === k}">${l}</button>`).join("")}</div>
      <div id="tabbody">${uniTab(u)}</div>`;
  }

  function uniTab(u) {
    if (ui.uniTab === "contatti") {
      return `<div class="panel" style="margin-top:12px">${contactRows(u)}</div>`;
    }
    if (ui.uniTab === "fonti") {
      const extra = [...new Set([u.summary_source, u.steps_source].concat((u.deadlines || []).map((d) => d.source),
        (u.contacts || []).map((c) => c.source)).filter(Boolean))];
      return `<h2 class="sec">Pagine monitorate</h2><div class="panel">${(u.sources || []).length ? u.sources.map((s) =>
          `<div class="srcrow"><a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener">${esc(s.name)}</a>
           <small>${s.type === "listing" ? "Elenco annunci" : "Pagina informativa"} · controllato ${esc(relTime(s.last_checked))}</small></div>`).join("")
        : `<p class="note">Nessuna pagina monitorata.</p>`}</div>
        <h2 class="sec">Dati di questa scheda</h2><div class="panel">${extra.map((x) =>
          `<div class="srcrow"><a href="${esc(safeUrl(x))}" target="_blank" rel="noopener">${esc(x.replace(/^https?:\/\/(www\.)?/, ""))}</a></div>`).join("")}</div>`;
    }
    const dls = uniDeadlines(u);
    const pos = D.positions.filter((p) => p.uni === u.id)
      .sort((a, b) => (isPast(a) - isPast(b)) || (a.deadline || "9999").localeCompare(b.deadline || "9999"));
    return `${u.summary ? `<div class="panel" style="margin-top:12px"><p>${esc(u.summary)}</p></div>` : ""}
      ${(u.steps || []).length ? `<h2 class="sec">Passi</h2><div class="panel"><ol class="steps">${u.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></div>` : ""}
      ${(u.prepare || []).length ? `<h2 class="sec">Da preparare</h2><div class="panel"><ul class="bullets">${u.prepare.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>` : ""}
      <h2 class="sec">Scadenze</h2><div class="panel">${dls.length ? dls.map((d) => `<div class="dl"><span>${esc(d.label)}</span>
          ${d.when ? `<span>${deadlineHtml(d.when)}${d.recurring && !d.date ? '<small class="muted"> (ogni anno)</small>' : ""}</span>` : `<span class="muted">${DASH}</span>`}</div>`).join("")
        : `<p class="note">Nessuna scadenza letta sulle pagine ufficiali.</p>`}</div>
      <h2 class="sec">Posizioni trovate (${pos.length})</h2>
      ${pos.length ? pos.map(posCard).join("") : `<div class="empty">Nessuna posizione trovata finora.</div>`}`;
  }

  const KIND = {
    new_position: ["Nuova posizione", I.plus], deadline_soon: ["Scadenza", I.clock], page_changed: ["Pagina cambiata", I.page],
  };

  function vAvvisi() {
    const seen = lastSeenAlert();
    const newest = D.alerts.reduce((m, a) => (a.created_at > m ? a.created_at : m), seen);
    if (newest !== seen) store.set("alerts.seen", newest); // aprire la pagina segna come letti
    const active = activeKeywords();
    const kws = allKeywords();
    const target = (a) => {
      const p = D.positions.find((x) => x.url === a.url);
      return p ? `href="#/p/${esc(p.id)}"` : `href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener"`;
    };
    return `<header class="top"><div><div class="meta">${D.alerts.length} avvisi recenti</div><h1>Avvisi</h1></div></header>
      ${D.alerts.length ? D.alerts.slice(0, 60).map((a) => {
        const [label, icon] = KIND[a.kind] || ["Avviso", I.bell];
        return `<a class="card alert ${a.created_at > seen ? "unread" : ""}" ${target(a)}>
          <span class="ic ${esc(a.kind)}" title="${esc(label)}">${icon}</span>
          <span class="txt">${esc(a.text)}<small>${esc(label)} · ${esc(relTime(a.created_at))}</small></span></a>`;
      }).join("") : `<div class="empty">Nessun avviso per ora.</div>`}
      <h2 class="sec">Parole chiave</h2>
      <div class="panel">
        <p class="note">Attivane una o più per filtrare la lista nel Radar. Nessuna attiva = tutte le posizioni.</p>
        <div class="kwchips">${kws.map((k) => `<button class="chip" data-kw="${esc(k)}" aria-pressed="${active.includes(k)}">${esc(k)}</button>`).join("")}</div>
        <form class="addkw" id="addkw"><input id="kwin" placeholder="Nuova parola chiave" maxlength="40" autocomplete="off">
          <button class="btn" type="submit">${I.plus}Aggiungi</button></form>
        ${active.length ? `<p style="margin:10px 0 0"><a href="#" data-action="kwclear">Disattiva tutte</a></p>` : ""}
      </div>
      <h2 class="sec">Frequenza e regole</h2>
      <div class="panel"><p class="note">Il radar controlla le pagine ufficiali ogni 6 ore. In questa versione le parole chiave filtrano solo
        la vista in app; le notifiche Telegram seguono <span class="mono">config/sources.yaml</span>.</p></div>`;
  }

  // ---------- calendario (.ics generato nel browser) ----------
  function downloadIcs(p) {
    const icsEsc = (s) => String(s).replace(/\\/g, "\\\\").replace(/[,;]/g, (c) => "\\" + c).replace(/\n/g, "\\n");
    const day = p.deadline.replace(/-/g, "");
    const next = isoLocal(new Date(parseDay(p.deadline).getTime() + 86400000)).replace(/-/g, "");
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
    const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Radar PhD//IT", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
      `UID:${p.id}@radar-phd`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${day}`, `DTEND;VALUE=DATE:${next}`,
      `SUMMARY:${icsEsc("Scadenza PhD: " + p.title)}`, `DESCRIPTION:${icsEsc(uniName(p.uni) + "\n" + p.url)}`,
      `URL:${p.url}`, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
    a.download = `scadenza-${p.id}.ics`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // ---------- router ----------
  function route() {
    const h = location.hash.replace(/^#/, "") || "/";
    let m, html, tab = "radar";
    if ((m = h.match(/^\/p\/([\w-]+)$/))) html = vDetail(m[1]);
    else if (h === "/atenei") { html = vAtenei(); tab = "atenei"; }
    else if ((m = h.match(/^\/ateneo\/([\w-]+)$/))) { html = vAteneo(decodeURIComponent(m[1])); tab = "atenei"; }
    else if (h === "/avvisi") { html = vAvvisi(); tab = "avvisi"; }
    else html = vRadar();
    view.innerHTML = html;
    document.querySelectorAll(".tabbar a").forEach((a) => a.classList.toggle("active", a.dataset.tab === tab));
    document.querySelector(".tabbar .dot").hidden = !hasUnread();
  }

  function rerenderList() { // ridisegna solo la home senza perdere il focus della ricerca
    const pos = document.getElementById("q") ? document.getElementById("q").selectionStart : null;
    view.innerHTML = vRadar();
    const q = document.getElementById("q");
    if (q && pos !== null) { q.focus(); q.setSelectionRange(pos, pos); }
  }

  view.addEventListener("input", (e) => {
    if (e.target.id === "q") { ui.q = e.target.value; rerenderList(); }
  });

  view.addEventListener("click", (e) => {
    const t = e.target.closest("[data-uni],[data-action],[data-tab],[data-kw]");
    if (!t) return;
    if (t.dataset.uni) { ui.uni = t.dataset.uni; rerenderList(); return; }
    if (t.dataset.tab && t.getAttribute("role") === "tab") {
      ui.uniTab = t.dataset.tab;
      document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-selected", b === t));
      const u = uniById(decodeURIComponent(location.hash.split("/")[2] || ""));
      if (u) document.getElementById("tabbody").innerHTML = uniTab(u);
      return;
    }
    if (t.dataset.kw) {
      const k = t.dataset.kw;
      const act = activeKeywords();
      store.set("kw.active", act.includes(k) ? act.filter((x) => x !== k) : act.concat(k));
      route(); return;
    }
    const a = t.dataset.action;
    if (a === "back") { if (history.length > 1) history.back(); else location.hash = "#/"; }
    else if (a === "save") {
      const s = store.get("saved", []), id = t.dataset.id;
      store.set("saved", s.includes(id) ? s.filter((x) => x !== id) : s.concat(id));
      route();
    } else if (a === "ics") {
      const p = D.positions.find((x) => x.id === t.dataset.id);
      if (p) downloadIcs(p);
    } else if (a === "kwclear") { e.preventDefault(); store.set("kw.active", []); route(); }
  });

  view.addEventListener("submit", (e) => {
    if (e.target.id !== "addkw") return;
    e.preventDefault();
    const k = document.getElementById("kwin").value.trim().toLowerCase();
    if (!k) return;
    const custom = store.get("kw.custom", []);
    if (!allKeywords().includes(k)) store.set("kw.custom", custom.concat(k));
    const act = activeKeywords();
    if (!act.includes(k)) store.set("kw.active", act.concat(k));
    route();
  });

  window.addEventListener("hashchange", () => {
    if (!/^#\/ateneo\//.test(location.hash)) ui.uniTab = "come";
    route(); window.scrollTo(0, 0);
  });

  // ---------- avvio ----------
  async function load() {
    const get = (f) => fetch("data/" + f, { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(f); return r.json(); });
    try {
      const [positions, unis, alerts, meta] = await Promise.all(
        ["positions.json", "universities.json", "alerts.json", "meta.json"].map(get));
      Object.assign(D, { positions, unis, alerts, meta });
    } catch (err) {
      view.innerHTML = `<header class="top"><div><h1>Radar PhD</h1></div></header>
        <div class="empty">Dati non disponibili. Controlla la connessione e riprova.</div>`;
      return;
    }
    route();
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  }
  load();
})();
