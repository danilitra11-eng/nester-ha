// Nestor sidebar panel: chat + settings (voice, quiet hours, permissions, Telegram).
const HELP = "https://github.com/danilitra11-eng/nester-ha/tree/main/docs/guides";

const CHAT = {
  en: { ph: "What can I do for you?", send: "Send", newc: "New chat", hello: "Good day, I'm {name}. How may I help?" },
  es: { ph: "¿Qué puedo hacer por ti?", send: "Enviar", newc: "Nuevo chat", hello: "Hola, soy {name}. ¿En qué puedo ayudarte?" },
  fr: { ph: "Que puis-je faire pour vous ?", send: "Envoyer", newc: "Nouvelle discussion", hello: "Bonjour, je suis {name}. Comment puis-je vous aider ?" },
  de: { ph: "Was kann ich für dich tun?", send: "Senden", newc: "Neuer Chat", hello: "Guten Tag, ich bin {name}. Wie kann ich helfen?" },
  it: { ph: "Cosa posso fare per te?", send: "Invia", newc: "Nuova chat", hello: "Buongiorno, sono {name}. Come posso aiutarti?" },
  pt: { ph: "O que posso fazer por você?", send: "Enviar", newc: "Nova conversa", hello: "Olá, sou {name}. Como posso ajudar?" },
  ru: { ph: "Чем могу помочь?", send: "Отправить", newc: "Новый чат", hello: "Здравствуйте, я {name}. Чем могу помочь?" },
  he: { ph: "מה תרצה שאעשה?", send: "שלח", newc: "שיחה חדשה", hello: "שלום, אני {name}. במה אוכל לעזור?" },
  zh: { ph: "需要我做什么？", send: "发送", newc: "新对话", hello: "您好，我是 {name}。有什么可以帮您？" },
  ja: { ph: "何をしましょうか？", send: "送信", newc: "新しい会話", hello: "こんにちは、{name}です。ご用件は？" },
};
const SR_LANG = { en: "en-US", es: "es-US", fr: "fr-FR", de: "de-DE", it: "it-IT", pt: "pt-BR", ru: "ru-RU", he: "he-IL", zh: "zh-CN", ja: "ja-JP" };

const UI = {
  en: { chat: "Chat", settings: "Settings", help: "Help", plan: "Plan", left: "left this month",
    general: "General", name: "Name", personality: "Personality", language: "Language",
    pers: { butler: "Butler", friendly: "Friendly", brief: "Brief" }, auto: "Automatic",
    voice: "Voice", voiceHelp: "Tap ▶ to listen, then Select. These are the voices installed in Home Assistant.",
    sample: "Good evening. The living room lights are off and the front door is locked.",
    select: "Select", selected: "Selected", hadefault: "Home Assistant's default voice",
    speak: "Read replies aloud here", quiet: "Quiet hours", quietHelp: "No talking out loud between these times.",
    from: "From", to: "To", off: "Off", save: "Save", saved: "Saved ✓",
    perms: "Permissions", permsHelp: "What Nestor may control or change. Only Home Assistant administrators can change this.",
    adminOnly: "Ask a Home Assistant administrator to change permissions.",
    secWarn: "Anyone who can talk to Nestor could unlock doors or disarm the alarm.",
    p: { lights: "💡 Lights", switches: "🔌 Switches", climate: "❄️ Climate & fans", covers: "🪟 Blinds & garage doors",
         media: "📺 TV & media", vacuum: "🧹 Robot vacuum & mower", scenes: "✨ Scenes & scripts",
         security: "🔒 Locks & alarm", structure: "🏠 Edit rooms, floors & names", design: "🎨 Dashboards & themes" },
    va: "Use Nestor as my voice assistant (phone app, watch, speakers)",
    tg: "Telegram", tgHelp: "Talk to Nestor from anywhere, by text or voice message.",
    tgConnect: "Connect Telegram", tgDisconnect: "Disconnect", tgLinked: "Connected",
    tgSteps: ["Open Telegram on your phone.", "Search for {bot} and open it.", "Tap Start, then send this code:", "Wait for the message \"Connected\". The code works for 10 minutes."],
    tgNotLinked: "Not connected" },
  es: { chat: "Chat", settings: "Ajustes", help: "Ayuda", plan: "Plan", left: "restantes este mes",
    general: "General", name: "Nombre", personality: "Personalidad", language: "Idioma",
    pers: { butler: "Mayordomo", friendly: "Amigable", brief: "Breve" }, auto: "Automático",
    voice: "Voz", voiceHelp: "Toca ▶ para escuchar y luego Elegir. Son las voces instaladas en Home Assistant.",
    sample: "Buenas noches. Las luces de la sala están apagadas y la puerta principal está cerrada.",
    select: "Elegir", selected: "Elegida", hadefault: "Voz predeterminada de Home Assistant",
    speak: "Leer las respuestas en voz alta aquí", quiet: "Horas de silencio", quietHelp: "No habla en voz alta entre estas horas.",
    from: "Desde", to: "Hasta", off: "Desactivado", save: "Guardar", saved: "Guardado ✓",
    perms: "Permisos", permsHelp: "Lo que Nestor puede controlar o cambiar. Solo los administradores pueden cambiarlo.",
    adminOnly: "Pide a un administrador de Home Assistant que cambie los permisos.",
    secWarn: "Cualquiera que hable con Nestor podría abrir puertas o desactivar la alarma.",
    p: { lights: "💡 Luces", switches: "🔌 Interruptores", climate: "❄️ Clima y ventiladores", covers: "🪟 Persianas y garaje",
         media: "📺 TV y medios", vacuum: "🧹 Aspiradora y cortacésped", scenes: "✨ Escenas y scripts",
         security: "🔒 Cerraduras y alarma", structure: "🏠 Editar habitaciones, pisos y nombres", design: "🎨 Paneles y temas" },
    va: "Usar Nestor como mi asistente de voz (app, reloj, altavoces)",
    tg: "Telegram", tgHelp: "Habla con Nestor desde cualquier lugar, por texto o mensaje de voz.",
    tgConnect: "Conectar Telegram", tgDisconnect: "Desconectar", tgLinked: "Conectado",
    tgSteps: ["Abre Telegram en tu teléfono.", "Busca {bot} y ábrelo.", "Toca Iniciar y envía este código:", "Espera el mensaje \"Conectado\". El código dura 10 minutos."],
    tgNotLinked: "No conectado" },
  he: { chat: "צ'אט", settings: "הגדרות", help: "עזרה", plan: "מסלול", left: "נותרו החודש",
    general: "כללי", name: "שם", personality: "אישיות", language: "שפה",
    pers: { butler: "משרת", friendly: "חברי", brief: "קצר" }, auto: "אוטומטי",
    voice: "קול", voiceHelp: "לחץ ▶ כדי לשמוע, ואז בחר. אלה הקולות שמותקנים ב-Home Assistant.",
    sample: "ערב טוב. האורות בסלון כבויים והדלת הראשית נעולה.",
    select: "בחר", selected: "נבחר", hadefault: "הקול שמוגדר כברירת מחדל ב-Home Assistant",
    speak: "להקריא תשובות כאן", quiet: "שעות שקט", quietHelp: "בשעות האלה הוא לא מדבר בקול.",
    from: "מ-", to: "עד", off: "כבוי", save: "שמור", saved: "נשמר ✓",
    perms: "הרשאות", permsHelp: "מה Nestor רשאי להפעיל או לשנות. רק מנהל של Home Assistant יכול לשנות את זה.",
    adminOnly: "בקש ממנהל Home Assistant לשנות הרשאות.",
    secWarn: "כל מי שמדבר עם Nestor יוכל לפתוח דלתות או לנטרל את האזעקה.",
    p: { lights: "💡 אורות", switches: "🔌 מתגים", climate: "❄️ מיזוג ומאווררים", covers: "🪟 תריסים ומוסך",
         media: "📺 טלוויזיה ומדיה", vacuum: "🧹 שואב ומכסחה", scenes: "✨ סצנות וסקריפטים",
         security: "🔒 מנעולים ואזעקה", structure: "🏠 עריכת חדרים, קומות ושמות", design: "🎨 דשבורדים ועיצוב" },
    va: "להשתמש ב-Nestor כעוזר הקולי שלי (אפליקציה, שעון, רמקולים)",
    tg: "טלגרם", tgHelp: "לדבר עם Nestor מכל מקום, בטקסט או בהודעה קולית.",
    tgConnect: "חבר טלגרם", tgDisconnect: "נתק", tgLinked: "מחובר",
    tgSteps: ["פתח את טלגרם בטלפון.", "חפש את {bot} ופתח אותו.", "לחץ Start ושלח את הקוד הזה:", "חכה להודעה \"מחובר\". הקוד תקף ל-10 דקות."],
    tgNotLinked: "לא מחובר" },
};

const CSS = `
:host { display:block; height:100%; background:var(--primary-background-color); color:var(--primary-text-color);
  font-family:var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
.wrap { display:flex; flex-direction:column; height:100%; max-width:820px; margin:0 auto; }
header { display:flex; align-items:center; gap:10px; padding:12px 16px; border-bottom:1px solid var(--divider-color); }
.menu { background:none; border:0; color:inherit; font-size:22px; cursor:pointer; padding:4px 8px; }
.orb { width:30px; height:30px; border-radius:50%; flex:none; background:radial-gradient(circle at 35% 35%, #ffe7a8, #d4a84b 45%, #6b4f12); }
.orb.busy { animation:p 1s ease-in-out infinite; } @keyframes p { 50% { transform:scale(1.15); } }
h1 { font-size:18px; margin:0; } .sub { font-size:12px; color:var(--secondary-text-color); }
.sub.bad { color:var(--error-color); } .sp { flex:1; }
.tabs button, .btn { border:1px solid var(--divider-color); background:var(--card-background-color); color:inherit;
  border-radius:10px; padding:7px 12px; cursor:pointer; font:inherit; font-size:14px; }
.tabs button.on { border-color:var(--primary-color); color:var(--primary-color); }
.primary { background:var(--primary-color); color:var(--text-primary-color, #fff); border:0; border-radius:10px; padding:10px 16px; cursor:pointer; font:inherit; }
#log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:10px; }
.msg { max-width:85%; padding:10px 14px; border-radius:14px; white-space:pre-wrap; word-wrap:break-word; line-height:1.45; }
.me { align-self:flex-end; background:var(--primary-color); color:var(--text-primary-color, #fff); }
.bot { align-self:flex-start; background:var(--card-background-color); border:1px solid var(--divider-color); }
.act { font-size:12px; color:var(--secondary-text-color); margin-top:6px; }
form { display:flex; gap:8px; padding:12px 16px 18px; border-top:1px solid var(--divider-color); }
input[type=text], input[type=time], select { background:var(--card-background-color); color:inherit; border:1px solid var(--divider-color);
  border-radius:10px; padding:10px 12px; font:inherit; min-width:0; }
form input { flex:1; }
.mic.on { background:var(--error-color); color:#fff; }
.settings { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:16px; }
.card { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:14px; padding:16px; }
.card h2 { font-size:16px; margin:0 0 4px; } .help { color:var(--secondary-text-color); font-size:13px; margin:0 0 12px; }
.row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:8px 0; } .row label { min-width:110px; }
.voices { display:flex; flex-direction:column; gap:6px; max-height:320px; overflow-y:auto; }
.voice { display:flex; align-items:center; gap:8px; padding:6px 8px; border:1px solid var(--divider-color); border-radius:10px; }
.voice.on { border-color:var(--primary-color); } .voice span { flex:1; }
.perm { display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr)); gap:6px; }
.perm label { display:flex; gap:8px; align-items:center; padding:6px; }
.warn { color:var(--warning-color, #f0b429); font-size:13px; }
.code { font-size:32px; letter-spacing:6px; font-weight:700; padding:8px 0; }
ol { margin:6px 0; padding-inline-start:20px; } .ok { color:var(--success-color, #3fb950); }
a { color:var(--primary-color); }
`;

class NestorPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._cid = Math.random().toString(36).slice(2);
    this._tab = "chat";
    this._started = false;
  }
  set hass(hass) { this._hass = hass; if (!this._started) { this._started = true; this._init(); } }
  set narrow(v) { this._narrow = v; const m = this.shadowRoot.querySelector(".menu"); if (m) m.style.display = v ? "" : "none"; }

  get lang() {
    const conf = this._settings?.options?.language;
    const base = (conf && conf !== "auto" ? conf : (this._hass?.language || navigator.language || "en")).split("-")[0];
    return base;
  }
  get t() { return UI[this.lang] || UI.en; }
  get c() { return CHAT[this.lang] || CHAT.en; }
  ws(msg) { return this._hass.callWS(msg); }

  async _init() {
    this._settings = await this.ws({ type: "nestor/settings" });
    this._render();
    this._hello();
    this._refreshStatus();
  }

  _render() {
    const t = this.t, c = this.c;
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="wrap" dir="${this.lang === "he" ? "rtl" : "ltr"}">
      <header><button class="menu" title="Menu">☰</button><div class="orb"></div>
        <div><h1></h1><div class="sub" id="status">…</div></div><div class="sp"></div>
        <div class="tabs"><button data-tab="chat">${t.chat}</button> <button data-tab="settings">⚙︎ ${t.settings}</button>
        <button data-help="1">❓</button></div></header>
      <div id="chatv" style="display:flex;flex-direction:column;flex:1;min-height:0">
        <div id="log"></div>
        <form><button type="button" class="btn mic">🎤</button><input type="text" autocomplete="off" placeholder="${c.ph}">
          <button type="button" class="btn newc">${c.newc}</button><button class="primary">${c.send}</button></form></div>
      <div id="setv" class="settings" style="display:none"></div></div>`;
    const r = this.shadowRoot;
    r.querySelector("h1").textContent = this._settings.options.assistant_name;
    r.querySelector(".menu").style.display = this._narrow ? "" : "none";
    r.querySelector(".menu").onclick = () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
    r.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => this._show(b.dataset.tab));
    r.querySelector("[data-help]").onclick = () => window.open(HELP, "_blank");
    r.querySelector("form").onsubmit = (e) => { e.preventDefault(); const i = r.querySelector("form input"); const v = i.value.trim(); if (v) { i.value = ""; this._send(v); } };
    r.querySelector(".newc").onclick = () => { this.ws({ type: "nestor/reset", conversation_id: this._cid }); this._cid = Math.random().toString(36).slice(2); r.querySelector("#log").innerHTML = ""; this._hello(); };
    this._setupMic();
    this._show(this._tab);
  }

  _show(tab) {
    this._tab = tab;
    const r = this.shadowRoot;
    r.querySelectorAll("[data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
    r.querySelector("#chatv").style.display = tab === "chat" ? "flex" : "none";
    r.querySelector("#setv").style.display = tab === "settings" ? "flex" : "none";
    if (tab === "settings") this._renderSettings();
  }

  _hello() { this._add(this.c.hello.replace("{name}", this._settings.options.assistant_name), "bot"); }

  _add(text, who, actions) {
    const log = this.shadowRoot.querySelector("#log");
    const d = document.createElement("div"); d.className = "msg " + who; d.textContent = text;
    if (actions && actions.length) {
      const a = document.createElement("div"); a.className = "act";
      a.textContent = actions.map(x => (x.ok ? "✓ " : "✗ ") + (x.tool === "call_service" && x.input
        ? `${x.input.domain}.${x.input.service} → ${(x.input.entity_ids || []).join(", ")}` : x.tool)).join("\n");
      d.appendChild(a);
    }
    log.appendChild(d); log.scrollTop = log.scrollHeight;
  }

  async _send(text) {
    const r = this.shadowRoot; this._add(text, "me"); r.querySelector(".orb").classList.add("busy");
    try {
      const res = await this.ws({ type: "nestor/chat", text, conversation_id: this._cid, ui_language: this.lang });
      this._add(res.reply, "bot", res.actions);
      if (res.audio_url) new Audio(res.audio_url).play().catch(() => {});
      if (res.settings_changed) { this._settings = await this.ws({ type: "nestor/settings" }); r.querySelector("h1").textContent = this._settings.options.assistant_name; }
      if (res.quota_remaining != null) this._refreshStatus();
    } catch (e) { this._add("⚠️ " + (e.message || e), "bot"); }
    r.querySelector(".orb").classList.remove("busy");
  }

  _setupMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const mic = this.shadowRoot.querySelector(".mic");
    if (!SR) { mic.style.display = "none"; return; }
    const rec = new SR(); rec.interimResults = false;
    rec.onresult = (e) => { const v = e.results[0][0].transcript; if (v) this._send(v); };
    rec.onend = () => mic.classList.remove("on");
    mic.onclick = () => { rec.lang = SR_LANG[this.lang] || "en-US"; mic.classList.add("on"); try { rec.start(); } catch (e) {} };
  }

  async _refreshStatus() {
    const el = this.shadowRoot.querySelector("#status");
    try {
      const s = await this.ws({ type: "nestor/status", ui_language: this.lang });
      this._status = s;
      if (s.ok) { el.textContent = `${this.t.plan}: ${s.plan} · ${s.quota_remaining} ${this.t.left}`; el.className = "sub"; }
      else { el.textContent = s.message; el.className = "sub bad"; }
    } catch (e) { el.textContent = "—"; }
  }

  async _save(changes, btn) {
    try {
      const res = await this.ws({ type: "nestor/settings/update", changes });
      this._settings.options = res.options;
      if (btn) { const old = btn.textContent; btn.textContent = this.t.saved; setTimeout(() => btn.textContent = old, 1500); }
      this.shadowRoot.querySelector("h1").textContent = res.options.assistant_name;
    } catch (e) { alert(e.message || e); }
  }

  async _renderSettings() {
    const t = this.t, o = this._settings.options, admin = this._settings.is_admin;
    const box = this.shadowRoot.querySelector("#setv");
    const langs = this._settings.languages.map(l => `<option value="${l}" ${l === o.language ? "selected" : ""}>${l === "auto" ? t.auto : l}</option>`).join("");
    const pers = this._settings.personalities.map(p => `<option value="${p}" ${p === o.personality ? "selected" : ""}>${t.pers[p] || p}</option>`).join("");
    const q = o.quiet_hours || {};
    box.innerHTML = `
      <div class="card"><h2>${t.general}</h2>
        <div class="row"><label>${t.name}</label><input type="text" id="name" maxlength="40"></div>
        <div class="row"><label>${t.personality}</label><select id="pers">${pers}</select></div>
        <div class="row"><label>${t.language}</label><select id="lang">${langs}</select></div>
        <div class="row"><label><input type="checkbox" id="speak" ${o.speak_replies ? "checked" : ""}> ${t.speak}</label></div>
        <button class="primary" id="saveGen">${t.save}</button></div>
      <div class="card"><h2>${t.quiet}</h2><p class="help">${t.quietHelp}</p>
        <div class="row"><label><input type="checkbox" id="qOn" ${o.quiet_hours ? "checked" : ""}> ${t.quiet}</label>
          ${t.from} <input type="time" id="qS" value="${q.start || "22:00"}"> ${t.to} <input type="time" id="qE" value="${q.end || "07:00"}"></div>
        <button class="primary" id="saveQ">${t.save}</button></div>
      <div class="card"><h2>${t.voice}</h2><p class="help">${t.voiceHelp}</p><div class="voices" id="voices">…</div></div>
      <div class="card"><h2>${t.perms}</h2><p class="help">${admin ? t.permsHelp : t.adminOnly}</p>
        <div class="perm" id="perm"></div><p class="warn" id="secw" style="display:none">⚠️ ${t.secWarn}</p>
        <div class="row"><label><input type="checkbox" id="va" ${o.make_voice_assistant ? "checked" : ""} ${admin ? "" : "disabled"}> ${t.va}</label></div>
        ${admin ? `<button class="primary" id="saveP">${t.save}</button>` : ""}</div>
      <div class="card"><h2>${t.tg}</h2><p class="help">${t.tgHelp}</p><div id="tg"></div></div>`;
    box.querySelector("#name").value = o.assistant_name;
    box.querySelector("#saveGen").onclick = (e) => this._save({ assistant_name: box.querySelector("#name").value, personality: box.querySelector("#pers").value,
      language: box.querySelector("#lang").value, speak_replies: box.querySelector("#speak").checked }, e.target);
    box.querySelector("#saveQ").onclick = (e) => this._save({ quiet_hours: box.querySelector("#qOn").checked
      ? { start: box.querySelector("#qS").value, end: box.querySelector("#qE").value } : null }, e.target);

    const perm = box.querySelector("#perm");
    this._settings.permissions.forEach(p => {
      const l = document.createElement("label");
      l.innerHTML = `<input type="checkbox" value="${p}" ${o.permissions.includes(p) ? "checked" : ""} ${admin ? "" : "disabled"}> <span></span>`;
      l.querySelector("span").textContent = t.p[p] || p; perm.appendChild(l);
    });
    const secw = box.querySelector("#secw");
    const upd = () => secw.style.display = perm.querySelector('[value="security"]').checked ? "" : "none";
    perm.onchange = upd; upd();
    if (admin) box.querySelector("#saveP").onclick = (e) => this._save({
      permissions: [...perm.querySelectorAll("input:checked")].map(i => i.value), make_voice_assistant: box.querySelector("#va").checked }, e.target);

    this._renderVoices();
    this._renderTelegram();
  }

  async _renderVoices() {
    const t = this.t, o = this._settings.options, admin = this._settings.is_admin;
    const box = this.shadowRoot.querySelector("#voices");
    const { engines } = await this.ws({ type: "nestor/voices" });
    const items = [{ engine: null, voice: null, label: t.hadefault }];
    engines.forEach(e => e.voices.length ? e.voices.forEach(v => items.push({ engine: e.engine_id, voice: v.voice_id, label: `${v.name} · ${e.name}` }))
      : items.push({ engine: e.engine_id, voice: null, label: e.name }));
    box.innerHTML = "";
    items.forEach(it => {
      const on = (it.engine || null) === (o.tts_engine || null) && (it.voice || null) === (o.tts_voice || null);
      const row = document.createElement("div"); row.className = "voice" + (on ? " on" : "");
      row.innerHTML = `<button class="btn play">▶</button><span></span><button class="btn pick" ${admin ? "" : "disabled"}>${on ? t.selected : t.select}</button>`;
      row.querySelector("span").textContent = it.label;
      row.querySelector(".play").onclick = async () => {
        const r = await this.ws({ type: "nestor/voice/preview", text: t.sample, engine: it.engine, voice: it.voice });
        if (r.url) new Audio(r.url).play().catch(() => {});
      };
      row.querySelector(".pick").onclick = async () => { await this._save({ tts_engine: it.engine, tts_voice: it.voice }); this._renderVoices(); };
      box.appendChild(row);
    });
  }

  async _renderTelegram(code) {
    const t = this.t, admin = this._settings.is_admin;
    const box = this.shadowRoot.querySelector("#tg");
    let st = this._status?.telegram;
    try { st = (await this.ws({ type: "nestor/status", ui_language: this.lang })).telegram; } catch (e) {}
    const bot = st?.bot_username ? "@" + st.bot_username : "the Nestor bot";
    if (st?.linked) {
      box.innerHTML = `<p class="ok">✓ ${t.tgLinked}${st.chats ? ` (${st.chats})` : ""}</p>${admin ? `<button class="btn" id="tgOff">${t.tgDisconnect}</button>` : ""}`;
      if (admin) box.querySelector("#tgOff").onclick = async () => { await this.ws({ type: "nestor/telegram/unpair" }); this._renderTelegram(); };
      return;
    }
    if (code) {
      const s = t.tgSteps;
      box.innerHTML = `<ol><li>${s[0]}</li><li>${s[1].replace("{bot}", `<b>${bot}</b>`)}</li><li>${s[2]}<div class="code">${code}</div></li><li>${s[3]}</li></ol>
        <button class="btn" id="tgCheck">↻</button>`;
      box.querySelector("#tgCheck").onclick = () => this._renderTelegram();
      return;
    }
    box.innerHTML = `<p>${t.tgNotLinked}</p>${admin ? `<button class="primary" id="tgOn">${t.tgConnect}</button>` : `<p class="help">${t.adminOnly}</p>`}`;
    if (admin) box.querySelector("#tgOn").onclick = async () => {
      try { const r = await this.ws({ type: "nestor/telegram/pair" }); this._renderTelegram(r.code); }
      catch (e) { box.insertAdjacentHTML("beforeend", `<p class="warn">${e.message || e}</p>`); }
    };
  }
}
customElements.define("nestor-panel", NestorPanel);
