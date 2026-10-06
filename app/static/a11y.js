/* DEVALAND ACCESSIBILITY BAR, multilingual (en ro de fr es it pl, from <html lang>). Own component, no external service.
   Source of truth: /opt/devaland/shared/a11y/. Copied (not edited) into each site that uses it.
   Original Romanian notes follow.
   BARA DE ACCESIBILITATE DEVALAND - componenta proprie, fara serviciu extern.
   ⛔Romos.ro ruleaza UserWay (serviciu comercial gazduit, legat de contul lor).
   Aceasta e scrisa de noi: niciun octet nu pleaca in afara paginii.
   ⭐Se pune pe orice site al nostru: nu stie nimic despre continutul paginii. */
(function () {
  "use strict";
  // Texts per page language (html lang). Romanian is the original; unknown languages fall back to English.
  var L = {
    ro: {modes:["Contrast mare","Contrast negativ","Alb-negru","Fundal luminos","Subliniază linkurile","Spațiere între litere","Font lizibil","Oprește animațiile","Ascunde imaginile"],
         btn:"Meniu de accesibilitate. Scurtătură: Control plus U", title:"Meniu de accesibilitate (Ctrl+U)", panel:"Meniu de accesibilitate", close:"Închide meniul de accesibilitate",
         bigger:"Text mai mare", smaller:"Text mai mic", size:"Mărime text", normal:"normal", reset:"Resetează toate setările",
         note:"Setările rămân salvate pe acest dispozitiv. Această bară este o facilitate suplimentară: pagina este construită accesibilă și fără ea.",
         table:"Tabel mai lat decat ecranul. Derulati orizontal, sau folositi sagetile stanga si dreapta."},
    en: {modes:["High contrast","Inverted colours","Greyscale","Light background","Underline links","Letter spacing","Readable font","Stop animations","Hide images"],
         btn:"Accessibility menu. Shortcut: Control plus U", title:"Accessibility menu (Ctrl+U)", panel:"Accessibility menu", close:"Close the accessibility menu",
         bigger:"Larger text", smaller:"Smaller text", size:"Text size", normal:"normal", reset:"Reset all settings",
         note:"Settings stay saved on this device. This bar is an extra: the page is built to be accessible without it.",
         table:"Table wider than the screen. Scroll sideways, or use the left and right arrow keys."},
    de: {modes:["Hoher Kontrast","Invertierte Farben","Graustufen","Heller Hintergrund","Links unterstreichen","Buchstabenabstand","Lesbare Schrift","Animationen stoppen","Bilder ausblenden"],
         btn:"Menü Barrierefreiheit. Tastenkürzel: Strg plus U", title:"Menü Barrierefreiheit (Strg+U)", panel:"Menü Barrierefreiheit", close:"Menü Barrierefreiheit schließen",
         bigger:"Größerer Text", smaller:"Kleinerer Text", size:"Textgröße", normal:"normal", reset:"Alle Einstellungen zurücksetzen",
         note:"Die Einstellungen bleiben auf diesem Gerät gespeichert. Diese Leiste ist eine Zusatzhilfe: die Seite ist auch ohne sie barrierefrei gebaut.",
         table:"Tabelle breiter als der Bildschirm. Seitlich scrollen oder die Pfeiltasten links und rechts verwenden."},
    fr: {modes:["Contraste élevé","Couleurs inversées","Niveaux de gris","Fond clair","Souligner les liens","Espacement des lettres","Police lisible","Arrêter les animations","Masquer les images"],
         btn:"Menu d'accessibilité. Raccourci : Ctrl plus U", title:"Menu d'accessibilité (Ctrl+U)", panel:"Menu d'accessibilité", close:"Fermer le menu d'accessibilité",
         bigger:"Texte plus grand", smaller:"Texte plus petit", size:"Taille du texte", normal:"normale", reset:"Réinitialiser tous les réglages",
         note:"Les réglages restent enregistrés sur cet appareil. Cette barre est un complément : la page est conçue pour être accessible sans elle.",
         table:"Tableau plus large que l'écran. Faites défiler horizontalement ou utilisez les flèches gauche et droite."},
    es: {modes:["Alto contraste","Colores invertidos","Escala de grises","Fondo claro","Subrayar enlaces","Espaciado de letras","Fuente legible","Detener animaciones","Ocultar imágenes"],
         btn:"Menú de accesibilidad. Atajo: Control más U", title:"Menú de accesibilidad (Ctrl+U)", panel:"Menú de accesibilidad", close:"Cerrar el menú de accesibilidad",
         bigger:"Texto más grande", smaller:"Texto más pequeño", size:"Tamaño del texto", normal:"normal", reset:"Restablecer todos los ajustes",
         note:"Los ajustes se guardan en este dispositivo. Esta barra es una ayuda adicional: la página está construida para ser accesible sin ella.",
         table:"Tabla más ancha que la pantalla. Desplácese horizontalmente o use las flechas izquierda y derecha."},
    it: {modes:["Contrasto elevato","Colori invertiti","Scala di grigi","Sfondo chiaro","Sottolinea i link","Spaziatura lettere","Carattere leggibile","Ferma le animazioni","Nascondi immagini"],
         btn:"Menu accessibilità. Scorciatoia: Ctrl più U", title:"Menu accessibilità (Ctrl+U)", panel:"Menu accessibilità", close:"Chiudi il menu accessibilità",
         bigger:"Testo più grande", smaller:"Testo più piccolo", size:"Dimensione testo", normal:"normale", reset:"Ripristina tutte le impostazioni",
         note:"Le impostazioni restano salvate su questo dispositivo. Questa barra è un aiuto in più: la pagina è costruita per essere accessibile anche senza.",
         table:"Tabella più larga dello schermo. Scorri in orizzontale o usa le frecce sinistra e destra."},
    pl: {modes:["Wysoki kontrast","Odwrócone kolory","Skala szarości","Jasne tło","Podkreśl linki","Odstępy między literami","Czytelna czcionka","Zatrzymaj animacje","Ukryj obrazy"],
         btn:"Menu dostępności. Skrót: Ctrl plus U", title:"Menu dostępności (Ctrl+U)", panel:"Menu dostępności", close:"Zamknij menu dostępności",
         bigger:"Większy tekst", smaller:"Mniejszy tekst", size:"Rozmiar tekstu", normal:"normalny", reset:"Przywróć wszystkie ustawienia",
         note:"Ustawienia zostają zapisane na tym urządzeniu. Ten pasek to dodatek: strona jest zbudowana jako dostępna także bez niego.",
         table:"Tabela szersza niż ekran. Przewiń w bok lub użyj strzałek w lewo i w prawo."}
  };
  var LG = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  var T = L[LG] || L.en;
  window.__A11Y_T__ = T;
  var KEY = "devaland-a11y";
  var H = document.documentElement;

  // eticheta, clasa pe <html>, pictograma
  var MODES = [
    [T.modes[0],        "a11y-contrast", "◐"],
    [T.modes[1],     "a11y-invert",   "◑"],
    [T.modes[2],            "a11y-gray",     "▧"],
    [T.modes[3],       "a11y-light",    "☀"],
    [T.modes[4], "a11y-links",    "⎯"],
    [T.modes[5],"a11y-spacing",  "↔"],
    [T.modes[6],         "a11y-readable", "T"],
    [T.modes[7],   "a11y-noanim",   "⏸"],
    [T.modes[8],    "a11y-noimg",    "▨"]
  ];
  // ⛔Contrastul si negativul se bat cap in cap: pornirea unuia il stinge pe celalalt.
  var EXCLUSIVE = [["a11y-contrast", "a11y-invert", "a11y-gray", "a11y-light"]];
  var MIN = -2, MAX = 5;             // pasi de marime, 4% fiecare
  var state = { modes: [], zoom: 0 };

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) { var o = JSON.parse(raw);
        if (o && Array.isArray(o.modes)) state.modes = o.modes;
        if (o && typeof o.zoom === "number") state.zoom = o.zoom; }
    } catch (e) { /* mod privat, cookie-uri blocate: mergem mai departe */ }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }
  function apply() {
    MODES.forEach(function (m) { H.classList.toggle(m[1], state.modes.indexOf(m[1]) > -1); });
    state.zoom = Math.max(MIN, Math.min(MAX, state.zoom));
    H.style.fontSize = state.zoom ? (100 + state.zoom * 4) + "%" : "";
    var btns = document.querySelectorAll(".a11y-grid button[data-mode]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", state.modes.indexOf(btns[i].dataset.mode) > -1);
    }
    var z = document.getElementById("a11y-zoom");
    if (z) z.textContent = (state.zoom === 0 ? T.normal : (state.zoom > 0 ? "+" : "") + state.zoom);
  }
  function toggleMode(cls) {
    var i = state.modes.indexOf(cls);
    if (i > -1) { state.modes.splice(i, 1); }
    else {
      EXCLUSIVE.forEach(function (grp) {
        if (grp.indexOf(cls) > -1) {
          grp.forEach(function (other) {
            var j = state.modes.indexOf(other); if (j > -1) state.modes.splice(j, 1);
          });
        }
      });
      state.modes.push(cls);
    }
    apply(); save();
  }

  function build() {
    var btn = document.createElement("button");
    btn.className = "a11y-btn"; btn.type = "button";
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "a11y-panel");
    btn.setAttribute("aria-label", T.btn);
    btn.title = T.title;
    btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
      '<circle cx="12" cy="4" r="2"/>' +
      '<path d="M12 7c-2.6 0-5.1-.5-6.9-1.1a1 1 0 0 0-.6 1.9C6 8.3 8 8.8 10 9v3.2L7.6 20a1 1 0 0 0 1.9.6L11.6 14h.8l2.1 6.6a1 1 0 0 0 1.9-.6L14 12.2V9c2-.2 4-.7 5.5-1.2a1 1 0 0 0-.6-1.9C17.1 6.5 14.6 7 12 7z"/>' +
      '</svg>';

    var p = document.createElement("div");
    p.className = "a11y-panel"; p.id = "a11y-panel";
    p.setAttribute("role", "dialog"); p.setAttribute("aria-modal", "false");
    p.setAttribute("aria-label", T.panel); p.hidden = true;

    var h = '<div class="a11y-head"><h2>' + T.title + '</h2>' +
      '<button class="a11y-close" type="button" aria-label="' + T.close + '">&#10005;</button></div>' +
      '<div class="a11y-body"><ul class="a11y-grid">';
    h += '<li><button type="button" data-zoom="1"><span class="a11y-ico" aria-hidden="true">A+</span>' + T.bigger + '</button></li>';
    h += '<li><button type="button" data-zoom="-1"><span class="a11y-ico" aria-hidden="true">A-</span>' + T.smaller + '</button></li>';
    MODES.forEach(function (m) {
      h += '<li><button type="button" data-mode="' + m[1] + '" aria-pressed="false">' +
           '<span class="a11y-ico" aria-hidden="true">' + m[2] + '</span>' + m[0] + '</button></li>';
    });
    h += '</ul><p class="a11y-note">' + T.size + ': <strong id="a11y-zoom">' + T.normal + '</strong></p>' +
      '<button class="a11y-reset" type="button">' + T.reset + '</button>' +
      '<p class="a11y-note">' + T.note + '</p></div>';
    p.innerHTML = h;

    document.body.appendChild(btn); document.body.appendChild(p);

    function open(o) {
      p.hidden = false;
      requestAnimationFrame(function(){ p.classList.toggle("open", o); });
      btn.setAttribute("aria-expanded", String(o));
      if (o) { p.querySelector(".a11y-close").focus(); }
      else { btn.focus(); setTimeout(function(){ if(!p.classList.contains("open")) p.hidden = true; }, 240); }
    }
    btn.addEventListener("click", function () { open(!p.classList.contains("open")); });
    p.querySelector(".a11y-close").addEventListener("click", function () { open(false); });
    p.querySelector(".a11y-reset").addEventListener("click", function () {
      state = { modes: [], zoom: 0 }; apply(); save();
    });
    p.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.mode) toggleMode(b.dataset.mode);
      else if (b.dataset.zoom) { state.zoom += parseInt(b.dataset.zoom, 10); apply(); save(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && !e.shiftKey && !e.altKey && (e.key === "u" || e.key === "U")) {
        e.preventDefault(); open(!p.classList.contains("open"));
      }
      if (e.key === "Escape" && p.classList.contains("open")) open(false);
    });
  }

  function init() { load(); build(); apply(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

/* ⛔ADAUGAT 01.09.2026. Tabelele au `display:block; overflow-x:auto`, deci se pot derula cu
   degetul. Dar o regiune derulabila care NU este focusabila de la tastatura este inaccesibila:
   un utilizator care navigheaza cu Tab nu ajunge niciodata la coloanele ascunse. WCAG 2.1.1.
   ⭐Se rezolva pe TIP, pentru orice tabel, inclusiv cele care nu s-au scris inca. */
(function () {
  "use strict";
  function markScrollable() {
    var t = document.querySelectorAll("table");
    for (var i = 0; i < t.length; i++) {
      var el = t[i];
      var scrolls = el.scrollWidth > el.clientWidth + 1;
      if (scrolls) {
        if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "0");
        if (!el.hasAttribute("role")) el.setAttribute("role", "region");
        if (!el.hasAttribute("aria-label")) {
          var cap = el.querySelector("caption");
          el.setAttribute("aria-label",
            (cap ? cap.textContent.trim() + ". " : "") +
            ((window.__A11Y_T__ || {}).table || "Table wider than the screen. Scroll sideways, or use the left and right arrow keys."));
        }
        el.classList.add("tbl-scroll");
      } else {
        el.removeAttribute("tabindex"); el.classList.remove("tbl-scroll");
      }
    }
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", markScrollable);
  else markScrollable();
  window.addEventListener("resize", markScrollable);
  window.addEventListener("load", markScrollable);
})();
