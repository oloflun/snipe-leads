import "server-only";

/**
 * Vilken driftmiljö Next-appen kör i — på ETT ställe.
 *
 * ## Varför den behövs
 *
 * `development` på Railway är en SPEGEL av produktionen (se CLAUDE.md): samma
 * kod, samma utseende, riktiga kunders ärenden. Det som skiljer den från
 * produktionen är alltså inte innehållet utan att den inte ska hittas.
 *
 * Uppmätt 2026-08-24: `web-development-6c85.up.railway.app` saknade robots.txt
 * helt och skickade ingen `X-Robots-Tag`. Den var alltså fritt indexerbar —
 * en fullständig kopia av säljsajten på en andra adress, med en inloggning som
 * leder till riktig kunddata. Vercels SSO-skydd täckte det förut; Railway har
 * ingen motsvarighet, och ingen ersättning lades in vid flytten.
 *
 * Appens EGEN grind håller (mätt samma dag: /dashboard och /settings ger 307
 * till /login, /admin ger 404, API ger 401). Det här handlar om det andra
 * lagret: att spegeln inte ska ligga i ett sökindex.
 *
 * ## Varför RAILWAY_ENVIRONMENT_NAME och inte NODE_ENV
 *
 * `NODE_ENV` är "production" i BÅDA Railway-miljöerna — det säger att bygget
 * är optimerat, inte vilken miljö det körs i. Att grinda på den hade gjort
 * spegeln indexerbar igen, alltså precis inget.
 *
 * Railway sätter `RAILWAY_ENVIRONMENT_NAME` automatiskt på varje tjänst. Samma
 * variabel som backendens `Settings.aktiv_miljo()` läser — en sanning, två
 * språk.
 */

/** Miljönamnet, normaliserat. Tom sträng = okänd (lokal körning). */
export function aktivMiljo(): string {
  return (
    process.env.RAILWAY_ENVIRONMENT_NAME ||
    process.env.ENVIRONMENT ||
    ""
  )
    .trim()
    .toLowerCase();
}

/**
 * Om det här är den skarpa produktionen.
 *
 * Fail-closed åt rätt håll: en OKÄND miljö räknas INTE som produktion, alltså
 * blir den noindex. Kostnaden för ett falskt negativt är att en lokal körning
 * bär en noindex-tagg som ingen ser. Kostnaden för ett falskt positivt är att
 * en spegel av kunddatan hamnar i Google.
 */
export function arProduktion(): boolean {
  return aktivMiljo() === "main";
}
