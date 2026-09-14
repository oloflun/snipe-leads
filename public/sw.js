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
 * Därför cachas exakt EN sak: appskalet — ikonerna och offline-sidan.
 *
 * Byggartefakterna under `/_next/static/` cachades här fram till 2026-08-23.
 * De gör det inte längre, och skälet står i fetch-hanteraren: en cache som
 * överlever en deploy strandar öppna flikar på filer servern slutat hålla.
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
 *
 * Höjd till v2 2026-08-23. Höjningen är inte kosmetisk: den är SANERINGEN.
 * v1 cachade `/_next/static/` cache-först (se nedan), och de artefakterna låg
 * kvar för alltid eftersom namnet aldrig ändrades. Varje webbläsare som besökt
 * appen bar alltså en växande hög av chunks från gamla byggen. `activate`
 * raderar v1 i sin helhet vid nästa sidladdning, utan att användaren gör något.
 *
 * Höjd till v3 2026-08-25: `snipe_logo.svg` bytt mot den nya varumärkesfilen.
 */

const CACHE = "snajp-v3";

const SKAL = [
  "/offline.html",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/snajp-symbol-black.svg"
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

  // `/_next/static/` står INTE här längre, och det är den bärande ändringen.
  //
  // Motiveringen förut var att byggartefakterna är innehållshashade och därför
  // inte kan ändras under samma URL. Det stämmer — men det är fel slutsats.
  // Filerna kan ändra sig UNDER FÖTTERNA på en öppen flik ändå, genom att
  // FÖRSVINNA: vid en deploy byter varje chunk namn, servern slutar hålla de
  // gamla, och en flik som stod öppen pekar på filer som inte finns kvar.
  // Klicka på en länk och navigeringen dör med webbläsarens egen felsida.
  //
  // Uppmätt två gånger samma dag 2026-08-23. Först i `next dev`, där Turbopack
  // återanvänder filnamnet mellan ombyggen — servern levererade ny CSS medan
  // webbläsaren envist körde den gamla, och ändringen såg ut att inte fungera.
  // Sedan i drift, där en deploy mitt under en testsession lämnade en öppen
  // flik med referenser till ett bygge som var borta.
  //
  // Vinsten var dessutom liten: Next sätter redan `Cache-Control: immutable`
  // på dem, så webbläsarens egen HTTP-cache gör samma jobb — utan att överleva
  // en deploy. Ikonerna ligger kvar: de hör till skalet, byter aldrig namn, och
  // är det som gör appen installerbar.
  if (url.pathname.startsWith("/icons/")) {
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
