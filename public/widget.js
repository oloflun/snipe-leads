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
    "opacity:0;transform:translateY(8px);pointer-events:none;visibility:hidden;" +
    // visibility, inte bara opacity: ett genomskinligt element ligger kvar i
    // tillgänglighetsträdet, och en skärmläsare hittade alltså en dold
    // "Kundtjänstchatt"-dialog mitt på kundens sida. Fördröjningen gör att
    // den försvinner FÖRST när uttoningen är klar.
    "transition:opacity .18s ease,transform .18s ease,visibility 0s linear .18s;";

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

  // -- Inbjudan -------------------------------------------------------------
  // Bubblan som FRÅGAR om den får hjälpa till, i stället för att vänta på ett
  // klick. Mönstret är Skatteverkets: en fetad rad och en inbjudan under,
  // med ett eget kryss så att den går att avfärda UTAN att öppna chatten.
  //
  // Texten kommer ur kundens tenant-konfiguration via "snajp:redo" — skriptet
  // är gemensamt och ska inte bära en enda kunds mening. Kommer ingen text
  // ritas ingen bubbla, och knappen står ensam som förut.
  //
  // Den visas EN gång per session. En besökare som kryssat bort den har
  // svarat, och att fråga igen vid nästa sidbyte vore att inte lyssna.

  var INBJUDAN_NYCKEL = "snajp.widget.inbjudan.avfardad";
  var inbjudan = null;
  var inbjudanTimer = null;

  function avfardad() {
    try {
      return window.sessionStorage.getItem(INBJUDAN_NYCKEL) === "1";
    } catch (fel) {
      // Privat läge eller blockerade kakor: hellre visa än krascha.
      return false;
    }
  }

  function minnsAvfardad() {
    try {
      window.sessionStorage.setItem(INBJUDAN_NYCKEL, "1");
    } catch (fel) {
      // Utan lagring visas den igen vid nästa sidladdning. Acceptabelt.
    }
  }

  function doljInbjudan(permanent) {
    if (inbjudanTimer) {
      window.clearTimeout(inbjudanTimer);
      inbjudanTimer = null;
    }
    if (!inbjudan) {
      return;
    }
    inbjudan.style.opacity = "0";
    inbjudan.style.transform = "translateY(6px)";
    inbjudan.style.pointerEvents = "none";
    inbjudan.style.visibility = "hidden";
    inbjudan.style.transitionDelay = "";
    if (permanent) {
      minnsAvfardad();
    }
  }

  function ritaInbjudan(rubrik, text) {
    if (inbjudan || avfardad()) {
      return;
    }
    var stillsam =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    inbjudan = document.createElement("div");
    // Ovanför knappen och högerställd: Skatteverket lägger sin till vänster om
    // figuren, men på en smal skärm trycks en vänsterställd bubbla ut ur sidan.
    // Ovanför säger samma sak och håller på 320px.
    inbjudan.style.cssText =
      "position:fixed;z-index:" + Z + ";right:20px;bottom:88px;" +
      "max-width:260px;box-sizing:border-box;padding:12px 34px 12px 14px;" +
      "background:#fff;color:#0f172a;border-radius:14px;" +
      "box-shadow:0 8px 28px rgba(15,23,42,.22);" +
      "font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;" +
      "opacity:0;transform:translateY(6px);visibility:hidden;" +
      (stillsam
        ? ""
        : "transition:opacity .22s ease,transform .22s ease,visibility 0s linear .22s;");

    var oppna = document.createElement("button");
    oppna.type = "button";
    oppna.style.cssText =
      "all:unset;display:block;cursor:pointer;max-width:100%;";
    // Rubriken bär frågan, raden under inbjudan — samma tvådelning som
    // referensen, för den läses i ett ögonkast.
    var h = document.createElement("span");
    h.style.cssText = "display:block;font-weight:600;margin-bottom:2px;";
    h.textContent = rubrik;
    var b = document.createElement("span");
    b.style.cssText = "display:block;color:#475569;";
    b.textContent = text;
    oppna.appendChild(h);
    oppna.appendChild(b);
    oppna.addEventListener("click", function () {
      doljInbjudan(true);
      visa();
    });

    var stang = document.createElement("button");
    stang.type = "button";
    stang.setAttribute("aria-label", "Stäng meddelandet");
    stang.style.cssText =
      "position:absolute;top:6px;right:6px;width:24px;height:24px;" +
      "border:0;background:transparent;color:#64748b;cursor:pointer;" +
      "border-radius:50%;display:flex;align-items:center;justify-content:center;" +
      "padding:0;line-height:0;";
    stang.innerHTML =
      "<svg aria-hidden='true' width='14' height='14' viewBox='0 0 24 24' fill='none' " +
      "stroke='currentColor' stroke-width='2.5' stroke-linecap='round'>" +
      "<line x1='6' y1='6' x2='18' y2='18'/><line x1='18' y1='6' x2='6' y2='18'/></svg>";
    stang.addEventListener("click", function (event) {
      event.stopPropagation();
      doljInbjudan(true);
    });

    inbjudan.appendChild(oppna);
    inbjudan.appendChild(stang);

    try {
      document.body.appendChild(inbjudan);
    } catch (fel) {
      inbjudan = null;
      return;
    }

    // Efter en kort stund, inte i samma ögonblick som sidan laddar: en bubbla
    // som slår upp mitt i att besökaren börjar läsa är i vägen, inte hjälpsam.
    inbjudanTimer = window.setTimeout(function () {
      if (oppen || avfardad()) {
        return;
      }
      inbjudan.style.visibility = "visible";
      inbjudan.style.transitionDelay = "0s";
      inbjudan.style.opacity = "1";
      inbjudan.style.transform = "translateY(0)";
      inbjudan.style.pointerEvents = "auto";
    }, 4500);
  }

  // -- Öppna/stäng ----------------------------------------------------------

  var mobil = window.matchMedia ? window.matchMedia("(max-width: 480px)") : null;

  function visa() {
    oppen = true;
    // Chatten är öppnad — inbjudan har gjort sitt och ska inte ligga kvar
    // ovanpå panelen.
    doljInbjudan(true);
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
    panel.style.visibility = "visible";
    panel.style.transitionDelay = "0s";
    panel.style.opacity = "1";
    panel.style.transform = "translateY(0)";
    knapp.innerHTML = kryss;
    knapp.setAttribute("aria-label", "Stäng chatten");
    knapp.setAttribute("aria-expanded", "true");
    // Fullskärmsläget: knappen låg annars kvar ÖVER chattens skickaknapp
    // (uppmätt på 375px). Chatten har sitt eget kryss i sidhuvudet — men
    // BARA när iframen faktiskt laddat. Felrutan har inget kryss, så där
    // står knappen kvar som enda väg ut.
    if (mobil && mobil.matches && redo) {
      knapp.style.display = "none";
    }
  }

  function dolj() {
    oppen = false;
    panel.style.pointerEvents = "none";
    panel.style.opacity = "0";
    panel.style.transform = "translateY(8px)";
    panel.style.visibility = "hidden";
    panel.style.transitionDelay = "";
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
    knapp.style.display = "flex";
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
      // Texterna kapas med flit: de kommer från vår egen origin, men ett fält
      // utan tak är ett fält som kan spränga kundens layout.
      var rubrik = event.data.inbjudanRubrik;
      var text = event.data.inbjudanText;
      if (
        typeof rubrik === "string" && rubrik &&
        typeof text === "string" && text &&
        rubrik.length < 80 && text.length < 120
      ) {
        ritaInbjudan(rubrik, text);
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
