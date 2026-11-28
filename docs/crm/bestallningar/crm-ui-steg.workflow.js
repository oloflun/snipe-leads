export const meta = {
  name: 'crm-ui-steg',
  description: 'Gränssnittssteg i följd i Snajp CRM (fas 4 och 5): varje steg byggs, granskas mot funktionslistan och rättas, på Opus',
  phases: [
    { title: 'Bygg', detail: 'en byggare i taget, samma worktree, tar bilder', model: 'opus' },
    { title: 'Granska', detail: 'en granskare läser commiten mot raderna och reglerna', model: 'opus' },
    { title: 'Rätta', detail: 'fynden rättas och committas', model: 'opus' },
  ],
}

const S = 'C:/Users/ANTONL~1/AppData/Local/Temp/claude/05d8e7d92420aa22/4b7c04f9-a411-45fa-addb-72e117ec542a/scratchpad/'
const ROT = 'C:/Users/Anton L/snipe-leads/.claude/worktrees/snajp-crm-dd0d83'
const GEMENSAMT = S + 'ui-gemensamt.md'
const STEG = (args && args.steg) || []

const RAPPORT = {
  type: 'object',
  properties: {
    commits: { type: 'array', items: { type: 'string' } },
    filer: { type: 'array', items: { type: 'string' } },
    byggda_rader: { type: 'string', description: 'Rad-ID:n som är byggda, och var (fil och komponent)' },
    inte_byggda_rader: { type: 'array', items: { type: 'string' }, description: 'Rad-ID och skälet, en per post' },
    andpunkter: { type: 'array', items: { type: 'string' }, description: 'Ändpunkterna vyn anropar' },
    saknas_i_backend: { type: 'array', items: { type: 'string' } },
    kontroller: { type: 'string', description: 'Typkontroll och invarianter med utfall i siffror' },
    bilder: { type: 'array', items: { type: 'string' } },
    adresser: { type: 'array', items: { type: 'string' }, description: 'Adresser i förhandsvisningen där orkestratören ser ytan' },
    inte_verifierat: { type: 'array', items: { type: 'string' } },
  },
  required: ['commits', 'filer', 'byggda_rader', 'inte_byggda_rader', 'andpunkter', 'saknas_i_backend', 'kontroller', 'bilder', 'inte_verifierat'],
}

const FYND = {
  type: 'object',
  properties: {
    fynd: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          allvar: { type: 'string', enum: ['fel', 'risk', 'lucka'] },
          fil: { type: 'string' }, rad: { type: 'number' }, vad: { type: 'string' },
          scenario: { type: 'string', description: 'Konkret: vad användaren gör eller vilket läge som råder, och vad som då blir fel' },
          forslag: { type: 'string' },
        },
        required: ['allvar', 'fil', 'vad', 'scenario'],
      },
    },
    rader_som_saknas: { type: 'array', items: { type: 'string' }, description: 'Rad-ID ur beställningen som varken är byggda eller redovisade som inte byggda' },
    last: { type: 'array', items: { type: 'string' } },
  },
  required: ['fynd', 'rader_som_saknas', 'last'],
}

const utfall = []
for (const b of STEG) {
  phase('Bygg')
  const rapport = await agent(
    'Du är gränssnittsbyggare i Snajp CRM. Läs FÖRST hela ' + GEMENSAMT + ' (uppdrag, gränser, form, regler, förhandsvisning, kontroller, bilder, commitregler) och sedan hela din beställning: ' + b.fil + '. Arbetskatalog: ' + ROT + '. Tidigare steg i samma följd har redan byggt och committat sina delar: läs `git log --oneline -12` och bygg ovanpå det som finns. Bygg allt beställningen säger, kör kontrollerna tills de är gröna, ta bilderna, stäng servern, och committa bara dina egna filer. Svara med rapporten.',
    { label: 'bygg:' + b.nr + ' ' + b.namn, phase: 'Bygg', model: 'opus', agentType: 'general-purpose', schema: RAPPORT },
  )
  if (!rapport) { utfall.push({ steg: b.nr, rapport: null }); log('Steg ' + b.nr + ' gav ingen rapport'); continue }

  phase('Granska')
  const granskning = await agent(
    'Du granskar ett gränssnittssteg i Snajp CRM som en annan agent just committat. Arbetskatalog: ' + ROT + '. Ändra INGA filer, committa ingenting, starta ingen server, kör ingen tsc och ingen next (maskinen har lite minne). Läs ' + GEMENSAMT + ' och beställningen ' + b.fil + ', sedan `git show --stat ' + (rapport.commits || []).map(c => String(c).split(' ')[0]).join(' ') + '` och HELA innehållet i de nya och ändrade filerna (inte bara diffen). Byggarens egen rapport: ' + JSON.stringify(rapport) + '\n\nDitt mått är beställningens rader. (1) FUNKTIONERNA: gå igenom varje rad-ID i beställningen mot läsarens underlag (docs/crm/underlag/app-*.md, samma ID) och mot koden. En rad som varken är byggd eller redovisad som inte byggd är en lucka: skriv den i rader_som_saknas. En rad som är byggd men beter sig annorlunda än underlaget och dagens komponent (fel anrop, fel ordning, fel gräns, saknat tomläge, saknat felbesked, saknad ånger) är ett fynd. Jämför varje anrop mot backendkoden under snajp-support/app/api/: metod, väg, parametrar, kroppens fält, svarets form, felkoder. (2) REGLERNA: tvåspråkighet (strängar som bara finns på ett språk, pluralfel, sammansatta meningar som blir fel på engelska), webbplatsbedömningen (visas något om sajten utan att svaret bär fälten, räknar klienten ut något själv, följer den med i export eller kopiering), läsroll och kundbesök (skrivande knappar som inte stängs av, anrop som går förbi proxyn), förlopp och utfall som ska finnas kvar efter omladdning, texter som lovar något koden inte gör. (3) LOGIK: kapplöpningar mellan hämtningar, optimistiska ändringar som inte läggs tillbaka vid fel, Ångra som gör något annat än användaren tror, sidindelning, adressparametrar efter omladdning. (4) TILLGÄNGLIGHET ur koden: tangentbord, fokus när en rad eller dialog försvinner, namn på kontroller på båda språken, färg som ensam bär betydelse, live-regioner som monteras med sitt innehåll. (5) FORMEN ur koden: egna komponenter där Astryx eller verktygslådan har en, färger utanför tokens, kopierad markup ur dagens app, en funktion lagd ovanpå i stället för in i ytan. Bilderna i docs/crm/bilder/fas4/ får du läsa med Read när ett fynd rör hur något ser ut, men den slutliga bedömningen av utseende gör orkestratören. Förhandsvisningens påhittade svar granskas bara om de har en annan form än backendens (då döljer de ett fel i vyn). Varje fynd ska ha fil, rad och ett konkret scenario. Inga stilsynpunkter. Högst 20 fynd, de allvarligaste först. Hittar du inget: tomma listor, hitta inte på något.',
    { label: 'granska:' + b.nr + ' ' + b.namn, phase: 'Granska', model: 'opus', agentType: 'general-purpose', schema: FYND },
  )
  const fynd = (granskning && granskning.fynd) || []
  const saknas = (granskning && granskning.rader_som_saknas) || []
  let rattning = null
  if (fynd.length || saknas.length) {
    phase('Rätta')
    rattning = await agent(
      'Du rättar granskarens fynd i ett gränssnittssteg i Snajp CRM. Arbetskatalog: ' + ROT + '. Läs FÖRST hela ' + GEMENSAMT + ' och beställningen ' + b.fil + '. Fynden: ' + JSON.stringify(fynd) + '\n\nRader som granskaren säger saknas: ' + JSON.stringify(saknas) + '\n\nPröva varje fynd mot koden innan du rättar: stämmer det, rätta det. Stämmer det inte, säg varför och rör inte koden. En rad som saknas bygger du, eller redovisar som inte byggd med skälet (till exempel att ändpunkten saknas eller att raden hör till ett senare steg). Kör kontrollerna igen tills de är gröna, ta om bilderna för det du ändrat som syns (stäng servern efteråt), och committa dina ändringar med sökvägarna utskrivna (meddelande: "fix(crm): rattelser efter granskning av steg ' + b.nr + '"). Svara med rapporten för steget som det står EFTER rättningen, och skriv i inte_verifierat varje fynd du avfärdade med skälet.',
      { label: 'rätta:' + b.nr + ' ' + b.namn, phase: 'Rätta', model: 'opus', agentType: 'general-purpose', schema: RAPPORT },
    )
  }
  utfall.push({ steg: b.nr, namn: b.namn, rapport, fynd, saknas, rattning })
  log('Steg ' + b.nr + ' (' + b.namn + '): ' + fynd.length + ' fynd, ' + saknas.length + ' rader saknades')
}
return utfall
