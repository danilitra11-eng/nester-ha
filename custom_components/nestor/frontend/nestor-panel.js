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
    tgNotLinked: "Not connected",
    home: "Home", month: "This month", requests: "requests", actionsDone: "things done for you", alertsN: "heads-ups", fixesN: "problems caught", autosN: "new automations", saved: "estimated savings",
    recent: "Recent messages from Nestor", none: "Nothing yet.",
    health: "Home check-up", check: "Check now", allGood: "✓ Everything looks fine.", unavailable: "Not responding", lowBattery: "Low battery", broken: "Not working", updates: "Updates available",
    alerts: "Alerts", alertsHelp: "What Nestor tells you about without being asked.",
    r: { safety: "🚨 Leaks, smoke, gas, CO (urgent, even in quiet hours)", left_open: "🚪 Garage/doors left open when away or at night", lights_left_on: "💡 Lights left on when everyone leaves", window_climate: "🪟 Window open while the AC runs", doctor: "🩺 Daily home check-up", suggestions: "💡 Weekly automation ideas", reports: "📊 Monthly report", doorbell: "🔔 Doorbell with camera description" },
    phones: "Send to these phones (Home Assistant app)", noPhones: "No phones with the Home Assistant app found. Telegram and Home Assistant notifications are still used.", test: "Send a test",
    vacation: "Vacation mode", vacationHelp: "Lights come and go in the evening so the house looks lived-in.", on: "On", offWord: "Off",
    family: "Family & guests", familyHelp: "Limit what each person may control. Names must match their Home Assistant user name or Telegram name.",
    person: "Name", blockedLbl: "Not allowed to control", addPerson: "Add person",
    people: "Connected on Telegram", remove: "Remove", guestLbl: "guest until",
    invite: "Invite a guest", inviteHelp: "A babysitter, dog sitter or neighbour gets temporary access on Telegram, with only the basics.", hours: "Hours of access", guestName: "Guest name", createCode: "Create guest code",
    memory: "What Nestor remembers", memoryHelp: "Nestor learns preferences when you tell it things like \"I like the bedroom at 70\". Delete anything here.", forget: "Forget",
    locked: "🔒 Available on {plan}", upgrade: "Upgrade"  },
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
    tgNotLinked: "No conectado",
    home: "Casa", month: "Este mes", requests: "pedidos", actionsDone: "acciones por ti", alertsN: "avisos", fixesN: "problemas detectados", autosN: "automatizaciones nuevas", saved: "ahorro estimado",
    recent: "Mensajes recientes de Nestor", none: "Nada todavía.",
    health: "Revisión de la casa", check: "Revisar ahora", allGood: "✓ Todo se ve bien.", unavailable: "No responden", lowBattery: "Batería baja", broken: "Sin funcionar", updates: "Actualizaciones disponibles",
    alerts: "Avisos", alertsHelp: "Lo que Nestor te cuenta sin que se lo pidas.",
    r: { safety: "🚨 Fugas, humo, gas, CO (urgente, incluso en silencio)", left_open: "🚪 Garaje/puertas abiertas sin nadie o de noche", lights_left_on: "💡 Luces encendidas cuando todos salen", window_climate: "🪟 Ventana abierta con el clima encendido", doctor: "🩺 Revisión diaria", suggestions: "💡 Ideas de automatización semanales", reports: "📊 Informe mensual", doorbell: "🔔 Timbre con descripción de la cámara" },
    phones: "Enviar a estos teléfonos (app de Home Assistant)", noPhones: "No se encontraron teléfonos con la app. Se usan Telegram y las notificaciones de Home Assistant.", test: "Enviar prueba",
    vacation: "Modo vacaciones", vacationHelp: "Las luces se encienden y apagan por la tarde para que la casa parezca habitada.", on: "Activado", offWord: "Desactivado",
    family: "Familia e invitados", familyHelp: "Limita lo que cada persona puede controlar. El nombre debe coincidir con su usuario de Home Assistant o de Telegram.",
    person: "Nombre", blockedLbl: "No puede controlar", addPerson: "Agregar persona",
    people: "Conectados en Telegram", remove: "Quitar", guestLbl: "invitado hasta",
    invite: "Invitar a alguien", inviteHelp: "Una niñera, cuidador de perros o vecino recibe acceso temporal en Telegram, solo lo básico.", hours: "Horas de acceso", guestName: "Nombre", createCode: "Crear código",
    memory: "Lo que Nestor recuerda", memoryHelp: "Nestor aprende preferencias cuando le dices cosas como \"me gusta el cuarto a 21\". Borra lo que quieras.", forget: "Olvidar",
    locked: "🔒 Disponible en {plan}", upgrade: "Mejorar plan"  },
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
    tgNotLinked: "לא מחובר",
    home: "בית", month: "החודש", requests: "בקשות", actionsDone: "פעולות שעשיתי בשבילך", alertsN: "התראות", fixesN: "תקלות שזוהו", autosN: "אוטומציות חדשות", saved: "חיסכון משוער",
    recent: "הודעות אחרונות מ-Nestor", none: "עוד אין.",
    health: "בדיקת בריאות לבית", check: "בדוק עכשיו", allGood: "✓ הכל נראה תקין.", unavailable: "לא מגיבים", lowBattery: "סוללה חלשה", broken: "לא עובדים", updates: "עדכונים זמינים",
    alerts: "התראות", alertsHelp: "על מה Nestor מעדכן אותך בלי שתבקש.",
    r: { safety: "🚨 נזילה, עשן, גז, פחמן חד-חמצני (דחוף, גם בשעות שקט)", left_open: "🚪 מוסך/דלתות פתוחים כשאין אף אחד או בלילה", lights_left_on: "💡 אורות דולקים כשכולם יוצאים", window_climate: "🪟 חלון פתוח כשהמזגן עובד", doctor: "🩺 בדיקת בריאות יומית", suggestions: "💡 רעיונות לאוטומציות כל שבוע", reports: "📊 דוח חודשי", doorbell: "🔔 פעמון עם תיאור מהמצלמה" },
    phones: "לשלוח לטלפונים האלה (אפליקציית Home Assistant)", noPhones: "לא נמצאו טלפונים עם האפליקציה. עדיין נשלח לטלגרם ולהתראות של Home Assistant.", test: "שלח בדיקה",
    vacation: "מצב חופשה", vacationHelp: "אורות נדלקים ונכבים בערב כדי שהבית ייראה מאוכלס.", on: "פועל", offWord: "כבוי",
    family: "משפחה ואורחים", familyHelp: "הגבל מה כל אחד רשאי להפעיל. השם צריך להתאים לשם המשתמש שלו ב-Home Assistant או בטלגרם.",
    person: "שם", blockedLbl: "אסור להפעיל", addPerson: "הוסף אדם",
    people: "מחוברים בטלגרם", remove: "הסר", guestLbl: "אורח עד",
    invite: "הזמן אורח", inviteHelp: "בייביסיטר, מטפל לכלב או שכן מקבלים גישה זמנית בטלגרם, רק לדברים הבסיסיים.", hours: "שעות גישה", guestName: "שם האורח", createCode: "צור קוד לאורח",
    memory: "מה Nestor זוכר", memoryHelp: "Nestor לומד העדפות כשאתה אומר לו דברים כמו \"אני אוהב את חדר השינה על 22\". אפשר למחוק כל דבר כאן.", forget: "שכח",
    locked: "🔒 זמין במסלול {plan}", upgrade: "שדרג"  },
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
        <div class="tabs"><button data-tab="chat">${t.chat}</button> <button data-tab="home">🏠 ${t.home}</button> <button data-tab="settings">⚙︎ ${t.settings}</button>
        <button data-help="1">❓</button></div></header>
      <div id="chatv" style="display:flex;flex-direction:column;flex:1;min-height:0">
        <div id="log"></div>
        <form><button type="button" class="btn mic">🎤</button><input type="text" autocomplete="off" placeholder="${c.ph}">
          <button type="button" class="btn newc">${c.newc}</button><button class="primary">${c.send}</button></form></div>
      <div id="homev" class="settings" style="display:none"></div>
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
    r.querySelector("#homev").style.display = tab === "home" ? "flex" : "none";
    if (tab === "settings") this._renderSettings();
    if (tab === "home") this._renderHome();
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
      <div class="card"><h2>${t.tg}</h2><p class="help">${t.tgHelp}</p><div id="tg"></div></div>
      <div class="card"><h2>${t.family}</h2><div id="family"></div></div>
      <div class="card"><h2>${t.memory}</h2><div id="memory"></div></div>`;
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
    this._renderFamily();
    this._renderMemory();
  }

  has(feature) { return (this._settings.features || []).includes(feature); }
  lockedHtml(plan) { return `<p class="warn">${this.t.locked.replace("{plan}", plan)}</p>`; }

  async _renderHome() {
    const t = this.t, admin = this._settings.is_admin, o = this._settings.options;
    const box = this.shadowRoot.querySelector("#homev");
    box.innerHTML = `
      <div class="card"><h2>📊 ${t.month}</h2><div id="report">…</div></div>
      <div class="card"><h2>🩺 ${t.health}</h2><div id="health"></div></div>
      <div class="card"><h2>🔔 ${t.alerts}</h2><p class="help">${t.alertsHelp}</p><div id="alerts"></div></div>
      <div class="card"><h2>🧳 ${t.vacation}</h2><p class="help">${t.vacationHelp}</p><div id="vac"></div></div>`;
    // report
    const rep = await this.ws({ type: "nestor/report" });
    const m = rep.month, cur = { USD: "$", EUR: "€", GBP: "£", ILS: "₪" }[rep.currency] || "";
    box.querySelector("#report").innerHTML = `<div class="row" style="gap:18px">
      <span><b>${m.commands}</b> ${t.requests}</span><span><b>${m.actions}</b> ${t.actionsDone}</span>
      <span><b>${m.alerts}</b> ${t.alertsN}</span><span><b>${m.fixes}</b> ${t.fixesN}</span>
      <span><b>${m.automations}</b> ${t.autosN}</span><span><b>${m.kwh_saved} kWh ≈ ${cur}${m.money_saved}</b> ${t.saved}</span></div>
      <p class="help" style="margin-top:12px">${t.recent}</p><div id="recent"></div>`;
    const recent = box.querySelector("#recent");
    if (!rep.recent_notifications.length) recent.textContent = t.none;
    rep.recent_notifications.slice().reverse().forEach(n => { const d = document.createElement("div"); d.className = "help"; d.textContent = `${new Date(n.at * 1000).toLocaleString()} — ${n.text}`; recent.appendChild(d); });
    // health
    const hb = box.querySelector("#health");
    if (!this.has("doctor")) hb.innerHTML = this.lockedHtml("Family");
    else {
      hb.innerHTML = `<button class="btn" id="chk">${t.check}</button><div id="hres" style="margin-top:10px"></div>`;
      const run = async () => {
        const h = await this.ws({ type: "nestor/health" }); const res = hb.querySelector("#hres"); res.innerHTML = "";
        const rows = [[t.unavailable, h.unavailable.map(x => x.name)], [t.lowBattery, h.low_battery.map(x => `${x.name} (${x.level}%)`)],
                      [t.broken, h.broken_integrations.map(x => x.title)], [t.updates, h.updates_available ? [String(h.updates_available)] : []]];
        const issues = rows.filter(r => r[1].length);
        if (!issues.length) { res.innerHTML = `<p class="ok">${t.allGood}</p>`; return; }
        issues.forEach(([label, items]) => { const p = document.createElement("p"); p.textContent = `• ${label}: ${items.slice(0, 8).join(", ")}${items.length > 8 ? "…" : ""}`; res.appendChild(p); });
      };
      hb.querySelector("#chk").onclick = run; run();
    }
    // alerts
    const ab = box.querySelector("#alerts");
    const rules = this._settings.alert_rules;
    rules.forEach(rule => {
      const l = document.createElement("label"); l.style.display = "flex"; l.style.gap = "8px"; l.style.padding = "4px 0";
      l.innerHTML = `<input type="checkbox" value="${rule}" ${o.alerts.includes(rule) ? "checked" : ""} ${admin ? "" : "disabled"}><span></span>`;
      l.querySelector("span").textContent = t.r[rule] || rule; ab.appendChild(l);
    });
    const phones = await this.ws({ type: "nestor/notify_targets" });
    const ph = document.createElement("div");
    ph.innerHTML = `<p class="help" style="margin-top:12px">${t.phones}</p>` + (phones.available.length ? "" : `<p class="help">${t.noPhones}</p>`);
    phones.available.forEach(svc => { const l = document.createElement("label"); l.style.display = "flex"; l.style.gap = "8px";
      l.innerHTML = `<input type="checkbox" class="phone" value="${svc}" ${phones.selected.includes(svc) ? "checked" : ""} ${admin ? "" : "disabled"}><span></span>`;
      l.querySelector("span").textContent = svc.replace("mobile_app_", ""); ph.appendChild(l); });
    ab.appendChild(ph);
    if (admin) {
      const row = document.createElement("div"); row.className = "row";
      row.innerHTML = `<button class="primary" id="saveA">${t.save}</button><button class="btn" id="testN">${t.test}</button>`;
      ab.appendChild(row);
      row.querySelector("#saveA").onclick = (e) => this._save({ alerts: [...ab.querySelectorAll("input:not(.phone):checked")].map(i => i.value),
        notify_targets: phones.available.length ? [...ab.querySelectorAll("input.phone:checked")].map(i => i.value) : null }, e.target);
      row.querySelector("#testN").onclick = () => this.ws({ type: "nestor/notify/test" });
    }
    // vacation
    const vb = box.querySelector("#vac");
    if (!this.has("vacation")) vb.innerHTML = this.lockedHtml("Pro");
    else {
      vb.innerHTML = `<label class="row"><input type="checkbox" id="vacOn" ${this._settings.options.vacation_mode ? "checked" : ""}> <b>${t.vacation}</b></label>`;
      vb.querySelector("#vacOn").onchange = (e) => this._save({ vacation_mode: e.target.checked });
    }
  }

  _renderFamily() {
    const t = this.t, admin = this._settings.is_admin, o = this._settings.options;
    const box = this.shadowRoot.querySelector("#family");
    if (!this.has("profiles")) { box.innerHTML = this.lockedHtml("Family"); return; }
    const groups = this._settings.device_groups;
    const profiles = JSON.parse(JSON.stringify(o.profiles || {}));
    box.innerHTML = `<p class="help">${t.familyHelp}</p><div id="plist"></div>
      ${admin ? `<div class="row"><input type="text" id="pname" placeholder="${t.person}"><button class="btn" id="padd">${t.addPerson}</button><button class="primary" id="psave">${t.save}</button></div>` : ""}
      <p class="help" style="margin-top:14px"><b>${t.people}</b></p><div id="tgpeople"></div>
      <p class="help" style="margin-top:14px"><b>${t.invite}</b> — ${t.inviteHelp}</p><div id="guest"></div>`;
    const list = box.querySelector("#plist");
    const paint = () => {
      list.innerHTML = "";
      Object.entries(profiles).forEach(([name, p]) => {
        const d = document.createElement("div"); d.className = "voice"; d.style.flexWrap = "wrap";
        d.innerHTML = `<b style="min-width:110px"></b><span class="help">${t.blockedLbl}:</span>`;
        d.querySelector("b").textContent = name;
        groups.forEach(g => { const l = document.createElement("label"); l.style.fontSize = "13px";
          l.innerHTML = `<input type="checkbox" ${p.blocked?.includes(g) ? "checked" : ""} ${admin ? "" : "disabled"}> ${t.p[g] || g}`;
          l.querySelector("input").onchange = (e) => { p.blocked = p.blocked || []; if (e.target.checked) p.blocked.push(g); else p.blocked = p.blocked.filter(x => x !== g); };
          d.appendChild(l); });
        if (admin) { const rm = document.createElement("button"); rm.className = "btn"; rm.textContent = t.remove; rm.onclick = () => { delete profiles[name]; paint(); }; d.appendChild(rm); }
        list.appendChild(d);
      });
    };
    paint();
    if (admin) {
      box.querySelector("#padd").onclick = () => { const n = box.querySelector("#pname").value.trim(); if (n && !profiles[n]) { profiles[n] = { blocked: [] }; box.querySelector("#pname").value = ""; paint(); } };
      box.querySelector("#psave").onclick = (e) => this._save({ profiles }, e.target);
    }
    // people on Telegram
    const tp = box.querySelector("#tgpeople");
    const people = this._status?.telegram?.people || [];
    if (!people.length) tp.textContent = t.none;
    people.forEach(pp => { const d = document.createElement("div"); d.className = "row";
      const until = pp.access_until ? ` (${t.guestLbl} ${new Date(pp.access_until * 1000).toLocaleString()})` : "";
      d.innerHTML = `<span></span>${admin ? `<button class="btn">${t.remove}</button>` : ""}`;
      d.querySelector("span").textContent = (pp.profile || pp.name || pp.chat_id) + until;
      if (admin) d.querySelector("button").onclick = async () => { await this.ws({ type: "nestor/telegram/unlink_chat", chat_id: pp.chat_id }); await this._refreshStatus(); this._renderFamily(); };
      tp.appendChild(d); });
    // guests
    const g = box.querySelector("#guest");
    if (!this.has("guests")) { g.innerHTML = this.lockedHtml("Pro"); return; }
    if (!admin) { g.innerHTML = `<p class="help">${t.adminOnly}</p>`; return; }
    g.innerHTML = `<div class="row"><input type="text" id="gname" placeholder="${t.guestName}"><label>${t.hours} <input type="text" id="ghours" value="48" style="width:70px"></label>
      <button class="primary" id="gcode">${t.createCode}</button></div><div id="gout"></div>`;
    g.querySelector("#gcode").onclick = async () => {
      try {
        const r = await this.ws({ type: "nestor/telegram/pair", role: "guest", profile: g.querySelector("#gname").value.trim() || "Guest", guest_hours: parseInt(g.querySelector("#ghours").value, 10) || 48 });
        const s2 = t.tgSteps; const bot = r.bot_username ? "@" + r.bot_username : "the Nestor bot";
        g.querySelector("#gout").innerHTML = `<ol><li>${s2[0]}</li><li>${s2[1].replace("{bot}", `<b>${bot}</b>`)}</li><li>${s2[2]}<div class="code">${r.code}</div></li></ol>`;
      } catch (e) { g.querySelector("#gout").innerHTML = `<p class="warn">${e.message || e}</p>`; }
    };
  }

  async _renderMemory() {
    const t = this.t;
    const box = this.shadowRoot.querySelector("#memory");
    if (!this.has("memory")) { box.innerHTML = this.lockedHtml("Family"); return; }
    const { facts } = await this.ws({ type: "nestor/memory" });
    box.innerHTML = `<p class="help">${t.memoryHelp}</p>`;
    if (!facts.length) box.insertAdjacentHTML("beforeend", `<p>${t.none}</p>`);
    facts.slice().reverse().forEach(f => { const d = document.createElement("div"); d.className = "voice";
      d.innerHTML = `<span></span><button class="btn">${t.forget}</button>`;
      d.querySelector("span").textContent = f.text + (f.person ? ` — ${f.person}` : "");
      d.querySelector("button").onclick = async () => { await this.ws({ type: "nestor/memory/forget", id: f.id }); this._renderMemory(); };
      box.appendChild(d); });
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
