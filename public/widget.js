/**
 * Snajps chattwidget — det enda kunden klistrar in på sin sajt:
 *
 *   <script src="https://<vår domän>/widget.js"
 *           data-nyckel="pk_<kund>_…" async></script>
 *
 * Principer, i den ordning de betyder något:
 *
 * 1. INGA HEMLIGHETER. data-nyckel är en publik adressbokspost (lib/tenants).
 *    Domän-allowlisten upprätthålls av webbläsaren via CSP frame-ancestors på
 *    /embed-sidan — läcker nyckeln renderas iframen ändå inte på fel domän.
 * 2. KUNDENS SIDA FÅR ALDRIG GÅ SÖNDER. Allt ligger i en IIFE, varje fel
 *    fångas, och värsta utfallet är att knappen inte visas eller att panelen
 *    visar en vänlig felruta. Inget kastas vidare till kundens sida.
 * 3. INGET BEROENDE. Ren DOM, inlinade stilar, ingen bundler — filen ska gå
 *    att läsa rakt upp och ned av den som undrar vad den gör på ens sajt.
 *
 * Chatten själv bor i iframen (/embed/<nyckel>, egen origin hos oss) — det
 * här skriptet ritar bara knappen och panelen och lyssnar på två meddelanden
 * därifrån: "snajp:redo" (med accentfärgen) och "snajp:stang".
 */
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script || window.__snajpWidget) {
    return;
  }
  window.__snajpWidget = true;

  var nyckel = script.getAttribute("data-nyckel");
  if (!nyckel) {
    // Utvecklarens fel, inte besökarens — sägs i konsolen och ingen annanstans.
    console.warn("Snajp-widget: attributet data-nyckel saknas i script-taggen.");
    return;
  }

  var origin;
  try {
    origin = new URL(script.src).origin;
  } catch (fel) {
    return;
  }

  var Z = "2147483000"; // under webbläsarens egna ytor, över kundens sajt
  var oppen = false;
  var redo = false;

  // -- Panelen (skapas direkt, iframen laddar i bakgrunden) -----------------
  // Eager med flit: första klicket ska öppna en färdig chatt, inte en
  // laddindikator, och "snajp:redo" hinner färga knappen innan någon klickar.

  var panel = document.createElement("div");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Kundtjänstchatt");
  panel.style.cssText =
    "position:fixed;z-index:" + Z + ";right:20px;bottom:92px;" +
    "width:380px;max-width:calc(100vw - 40px);" +
    "height:min(640px, calc(100dvh - 120px));" +
    "border-radius:16px;overflow:hidden;background:#fff;" +
    "box-shadow:0 12px 48px rgba(15,23,42,.28);" +
    "opacity:0;transform:translateY(8px);pointer-events:none;" +
    "transition:opacity .18s ease,transform .18s ease;";

  var iframe = document.createElement("iframe");
  iframe.src = origin + "/embed/" + encodeURIComponent(nyckel);
  iframe.title = "Kundtjänstchatt";
  iframe.style.cssText = "width:100%;height:100%;border:0;display:block;";

  // Felrutan: visas i panelen om iframen aldrig blev redo. Kundens sida ska
  // få ett vänligt besked, inte en tom vit ruta och inte en krasch.
  var felruta = document.createElement("div");
  felruta.style.cssText =
    "display:none;height:100%;box-sizing:border-box;padding:32px 28px;" +
    "font:15px/1.6 system-ui,-apple-system,'Segoe UI',sans-serif;color:#334155;";
  felruta.innerHTML =
    "<p style='margin:0 0 8px;font-weight:600;color:#0f172a'>Chatten kunde inte laddas</p>" +
    "<p style='margin:0'>Försök gärna igen om en liten stund, eller kontakta oss via " +
    "mejl eller telefon så hjälper vi dig den vägen.</p>";

  panel.appendChild(iframe);
  panel.appendChild(felruta);

  // -- Knappen --------------------------------------------------------------

  var knapp = document.createElement("button");
  knapp.type = "button";
  knapp.setAttribute("aria-label", "Öppna chatten");
  knapp.setAttribute("aria-expanded", "false");
  knapp.style.cssText =
    "position:fixed;z-index:" + Z + ";right:20px;bottom:20px;" +
    "width:56px;height:56px;border:0;border-radius:50%;cursor:pointer;" +
    "background:#1e293b;color:#fff;display:flex;align-items:center;" +
    "justify-content:center;box-shadow:0 6px 24px rgba(15,23,42,.30);" +
    "transition:transform .12s ease;padding:0;";
  // Pratbubbla respektive kryss — båda ligger i knappen, ett i taget synligt.
  knapp.innerHTML =
    "<svg aria-hidden='true' width='26' height='26' viewBox='0 0 24 24' fill='none' " +
    "stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" +
    "<path d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/></svg>";
  var bubbla = knapp.innerHTML;
  var kryss =
    "<svg aria-hidden='true' width='24' height='24' viewBox='0 0 24 24' fill='none' " +
    "stroke='currentColor' stroke-width='2' stroke-linecap='round'>" +
    "<line x1='6' y1='6' x2='18' y2='18'/><line x1='18' y1='6' x2='6' y2='18'/></svg>";

  knapp.addEventListener("mouseenter", function () {
    knapp.style.transform = "scale(1.06)";
  });
  knapp.addEventListener("mouseleave", function () {
    knapp.style.transform = "scale(1)";
  });

  // -- Öppna/stäng ----------------------------------------------------------

  var mobil = window.matchMedia ? window.matchMedia("(max-width: 480px)") : null;

  function visa() {
    oppen = true;
    // På en liten skärm tar panelen hela ytan — en 380px-ruta bredvid en
    // 56px-knapp på en 375px-skärm är ingen chatt, det är ett pussel.
    if (mobil && mobil.matches) {
      panel.style.right = "0";
      panel.style.bottom = "0";
      panel.style.width = "100vw";
      panel.style.maxWidth = "100vw";
      panel.style.height = "100dvh";
      panel.style.borderRadius = "0";
    }
    if (!redo) {
      iframe.style.display = "none";
      felruta.style.display = "block";
    }
    panel.style.pointerEvents = "auto";
    panel.style.opacity = "1";
    panel.style.transform = "translateY(0)";
    knapp.innerHTML = kryss;
    knapp.setAttribute("aria-label", "Stäng chatten");
    knapp.setAttribute("aria-expanded", "true");
  }

  function dolj() {
    oppen = false;
    panel.style.pointerEvents = "none";
    panel.style.opacity = "0";
    panel.style.transform = "translateY(8px)";
    if (mobil && mobil.matches) {
      // Återställ skrivbordsgeometrin så en rotering inte lämnar fel form.
      panel.style.right = "20px";
      panel.style.bottom = "92px";
      panel.style.width = "380px";
      panel.style.maxWidth = "calc(100vw - 40px)";
      panel.style.height = "min(640px, calc(100dvh - 120px))";
      panel.style.borderRadius = "16px";
    }
    knapp.innerHTML = bubbla;
    knapp.setAttribute("aria-label", "Öppna chatten");
    knapp.setAttribute("aria-expanded", "false");
  }

  knapp.addEventListener("click", function () {
    if (oppen) {
      dolj();
    } else {
      visa();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && oppen) {
      dolj();
    }
  });

  // -- Meddelanden från iframen --------------------------------------------
  // Bara från VÅR origin — allt annat på kundens sida ignoreras.

  window.addEventListener("message", function (event) {
    if (event.origin !== origin || !event.data || typeof event.data !== "object") {
      return;
    }
    if (event.data.typ === "snajp:redo") {
      redo = true;
      iframe.style.display = "block";
      felruta.style.display = "none";
      if (typeof event.data.farg === "string" && event.data.farg.length < 64) {
        knapp.style.background = event.data.farg;
      }
    }
    if (event.data.typ === "snajp:stang") {
      dolj();
    }
  });

  // -- Montering ------------------------------------------------------------

  function montera() {
    try {
      document.body.appendChild(panel);
      document.body.appendChild(knapp);
    } catch (fel) {
      // Princip 2: kundens sida rör vi aldrig vid ett fel.
    }
  }

  if (document.body) {
    montera();
  } else {
    document.addEventListener("DOMContentLoaded", montera);
  }
})();
