/**
 * Service worker — det som gör Snajp installerbar och startbar utan nät.
 *
 * ## Varför den finns
 *
 * Manifestet ensamt räcker för iOS ("Lägg till på hemskärmen"), men Chrome och
 * Edge — desktop som Android — visar ingen installationsknapp alls utan en
 * registrerad service worker med en fetch-hanterare. Utan den här filen är
 * appen alltså installerbar på en av tre plattformar.
 *
 * ## Regeln som inte får brytas: KUNDDATA CACHAS ALDRIG
 *
 * En service worker skriver till disk, och den disken är användarens egen —
 * delad dator, delad telefon, kvar efter utloggning. Allt under `/api/` är
 * kundens ärenden, mejladresser och prospekt, och ingenting av det får hamna
 * i ett cachelager. Detsamma gäller varje sidnavigering: `/dashboard/*`
 * renderas på servern MED kunddata i HTML:en.
 *
 * Därför cachas exakt två saker:
 *
 *   1. Statiska byggartefakter under `/_next/static/` — namnade med
 *      innehållshash, alltså oföränderliga.
 *   2. Appskalet: ikonerna och offline-sidan.
 *
 * Allt annat går rakt till nätet, varje gång. Det är en medveten avvägning:
 * appen blir inte snabbare offline, den blir INSTALLERBAR och möts av en
 * begriplig sida i stället för webbläsarens dinosaurie när nätet är borta.
 *
 * ## Versionen
 *
 * `CACHE` bär ett versionsnummer. Höj det när `SKAL` ändras — annars ligger
 * den gamla offline-sidan kvar tills webbläsaren själv städar, vilket kan ta
 * veckor. `activate` raderar varje cache med ett annat namn.
 */

const CACHE = "snajp-v1";

const SKAL = [
  "/offline.html",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/snipe_logo.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // addAll är allt-eller-inget: en 404 på en enda fil gör att INGENTING
      // cachas, och installationen misslyckas tyst. Filerna läggs därför en
      // och en, och en miss lämnas åt nätet.
      .then((cache) => Promise.allSettled(SKAL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((nycklar) =>
        Promise.all(nycklar.filter((n) => n !== CACHE).map((n) => caches.delete(n)))
      )
      .then(() => self.clients.claim())
  );
});

/** Sådant som ALDRIG får cachas, oavsett vad Cache-Control säger. */
function arKanslig(url) {
  return (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/dashboard") ||
    url.pathname.startsWith("/admin") ||
    url.pathname.startsWith("/settings") ||
    url.pathname.startsWith("/chat/")
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Bara GET. En POST som besvaras ur cache vore ett svar på en fråga som
  // aldrig ställdes.
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  // Andra origins (Google Fonts m.m.) lämnas åt webbläsaren.
  if (url.origin !== self.location.origin) {
    return;
  }

  // Sidnavigeringar: alltid nät först. Faller nätet visas offline-sidan —
  // aldrig en cachad version av en kunds arbetsyta.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/offline.html").then((r) => r ?? Response.error()))
    );
    return;
  }

  if (arKanslig(url)) {
    return;
  }

  // Innehållshashade byggartefakter: cache först, för de kan per definition
  // inte ha ändrats under samma URL.
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(request).then(
        (traff) =>
          traff ??
          fetch(request).then((svar) => {
            if (svar.ok) {
              const kopia = svar.clone();
              caches.open(CACHE).then((cache) => cache.put(request, kopia));
            }
            return svar;
          })
      )
    );
  }
});
