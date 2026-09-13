# Pilotavtal — Snajp

> **Utkast 2026-09-13. Ska läsas av jurist innan det skickas** (se
> [`JURIDIK_ATGARDER.md`](JURIDIK_ATGARDER.md), P0.3c). Hakparenteser är
> uppgifter som fylls i per kund eller som ännu inte är verifierade — ett avtal
> med en kvarlämnad hakparentes ska inte skrivas under.
>
> Hålls på 2–3 sidor med flit. Styrningen av vad agenterna får göra ligger i
> produktens regler (auto/utkast/eskalera), inte i avtalstext — avtalet
> beskriver bara att de reglerna finns och vem som äger dem.

---

**Parter**

1. **[Snajp AB]**, org.nr [xxxxxx-xxxx], [adress] ("Snajp")
2. **[Kund AB]**, org.nr [xxxxxx-xxxx], [adress] ("Kunden")

## 1. Pilotperiod och pris

1.1 Piloten löper i **8 veckor** från [startdatum] till [slutdatum].

1.2 Pilotavgiften är **[belopp] kr exkl. moms** för hela perioden och avser
paketet **[Snajp Support / Leads / Duo / Trio / Bokföring]**. Uppstartsavgiften
är [inkluderad / X kr].

1.3 Ordinarie prislista vid avtalets tecknande, för att Kunden ska veta vad som
gäller efter piloten (priser per månad exkl. moms, ingångspriser som sätts efter
volym):

| Paket | Pris från |
|---|---|
| Snajp Support | 3 990 kr |
| Snajp Leads (150 prospekt, 300 mejl/mån) | 4 490 kr |
| Snajp Duo (Support + Leads) | 6 990 kr |
| Snajp Trio (Support + Leads + Bokföring) | 9 990 kr |
| Snajp Bokföring | 2 690 kr |
| Uppstart (kunskapsbas och konfiguration), engång | 1 590 kr |
| Extra prospekt / extra mejl | 9 kr / 3 kr st |

Ingen bindningstid. *(Källa: `lib/pricing.ts` — uppdatera tabellen om filen ändras.)*

1.4 Piloten övergår **inte** automatiskt i ett betalt abonnemang. Senast vecka 7
meddelar Kunden om den vill fortsätta till ordinarie pris.

## 2. Upplägg och styrning

2.1 Piloten genomförs i tre faser. Övergången mellan faserna görs i produktens
regler per ärendekategori — *utkast* (människa godkänner), *auto* (skickas
direkt) eller *eskalera* (alltid till människa) — och kräver att Kunden har
godkänt den.

| Vecka | Läge | Vad som mäts |
|---|---|---|
| 1–2 | Allt som utkast. Snajp och Kunden bygger kunskapsbas och regler tillsammans. | Luckor i kunskapsbasen |
| 3–6 | Kunden granskar och godkänner själv. | Andel utkast som godkänns **utan redigering**, per kategori |
| 7–8 | Autosvar på de kategorier Kunden valt ut som ofarliga. Övrigt som tidigare. | Samma andel, plus reklamationer på autosvar |

2.2 Ett ärende skickas bara automatiskt om kategorins regel är *auto*, agentens
konfidens når tröskeln och tonen i kundens mejl inte är negativ. Annars blir det
ett utkast.

## 3. Mänsklig granskning

3.1 **Inga utgående säljmejl (Leads) skickas utan att en människa hos Kunden
har godkänt dem.** Så fungerar produkten redan; här blir det ett avtalsvillkor.

3.2 Supportsvar skickas som utkast, utom i kategorier som Kunden uttryckligen
satt till *auto* (punkt 2). Ärenden på listan i Bilaga 2 punkt 7 är alltid
*eskalera*.

3.3 Kunden ansvarar för innehållet i det Kunden godkänner. Snajp ansvarar för
att regler och spärrar fungerar som de är beskrivna.

## 4. Kundens medverkan

4.1 Kunden lämnar underlaget i Bilaga 2 senast [datum, vecka 1].

4.2 **Motprestation:** Kunden deltar i ett **veckovis feedbacksamtal** (30 min)
under pilotperioden. Kunden ger Snajp **rätt att nämna Kunden som referens**
(namn och logotyp) samt att använda ett citat efter att Kunden godkänt texten.

## 5. Personuppgifter (personuppgiftsbiträdesavtal)

5.1 Kunden är personuppgiftsansvarig och Snajp personuppgiftsbiträde för de
uppgifter som behandlas i tjänsten: kundmejl och ärenden, prospekt och
kontaktuppgifter, samt bokföringsunderlag.

5.2 Snajp behandlar uppgifterna endast enligt Kundens dokumenterade
instruktioner, som utgörs av detta avtal och Kundens inställningar i tjänsten.

5.3 Snajp anlitar de underbiträden som anges i **Bilaga 1**. Byte eller tillägg
meddelas Kunden minst [30] dagar i förväg; Kunden får invända och säga upp
piloten utan kostnad.

5.4 Personuppgifter överförs inte till tredje land utan skyddsåtgärder enligt
dataskyddsförordningen kapitel V. Språkmodeller som behandlar data utanför
EU/EES utan sådana åtgärder används inte för Kundens uppgifter.

5.5 Snajp underrättar Kunden om en personuppgiftsincident utan onödigt dröjsmål
och senast inom [24] timmar efter upptäckt. Rutinen står i `INCIDENT_RESPONSE.md`.

5.6 Snajp bistår Kunden vid de registrerades begäran om tillgång, rättelse och
radering.

## 6. Ansvar

6.1 Snajps sammanlagda ansvar under avtalet är **begränsat till den
pilotavgift Kunden har betalat**.

6.2 Snajp ansvarar inte för indirekt skada eller utebliven vinst, eller för
innehåll som Kunden har godkänt (punkt 3.3).

6.3 Begränsningarna gäller inte vid uppsåt eller grov vårdslöshet.

## 7. Avslut, export och radering

7.1 Vid pilotens slut, eller om Kunden inte fortsätter, lämnar Snajp på begäran
inom 14 dagar en **export** av Kundens data: kunskapsbas, ärenden och svar,
prospekt och leadslistor (CSV/JSON) samt bokföringsunderlag (SIE4 där det finns).

7.2 Senast **30 dagar** efter avslut **raderas** Kundens data ur tjänsten.
Snajp bekräftar raderingen skriftligt. Säkerhetskopior gallras enligt ordinarie
cykel om [X] dagar.

## 8. Övrigt

8.1 Parterna håller den andra partens affärsinformation konfidentiell.

8.2 Avtalet lyder under svensk rätt. Tvist avgörs av allmän domstol.

---

Ort och datum ______________________

**Snajp** ______________________ **Kunden** ______________________

---

## Bilaga 1 — Underbiträden

| Underbiträde | Ändamål | Region / avtal |
|---|---|---|
| Google (Gemini via Vertex AI) | Språkmodell: klassificerar och skriver text, läser bilder och kvitton | [Vertex-region + Googles DPA — verifieras] |
| Railway | Drift av applikationen och databasen | [Region — `scripts/railway_region.py` gav "okänd" för alla tjänster 2026-09-13] |
| Resend (EU) | Utskick av mejl | [EU-region + DPA — verifieras] |
| Redis Cloud (Redis Ltd) | Jobbkö och cache med automatisk radering (TTL) | [EU-region + DPA — `scripts/redis_kontroll.py`] |
| ScrapeGraphAI | Hämtning av publika webbsidor under leads-research | [Region + DPA — ej bekräftat] |

*Håll i synk med `UNDERLEVERANTORER` i `lib/bolag.ts` och
`docs/registerforteckning.md`. Den listan tar fortfarande upp Supabase och
OpenAI. Stryk dem där om de inte längre behandlar data, eller lägg till dem här.*

## Bilaga 2 — Underlag från Kunden (vecka 1)

Det här blir kunskapsbasen och reglerna. Det mesta går att förifylla med
`scripts/pilot_kb_utkast.py` (orgnr + webbplats → utkast). Kunden granskar
utkastet och kompletterar det som saknas.

1. **Villkorstexter** — köpvillkor, leveransvillkor, retur och ångerrätt
2. **Garantier** — vad som gäller och hur ett garantiärende går till
3. **Prislista** — aktuell, med vad som ingår
4. **Topp-10-frågor** från kunder, med det svar Kunden ger i dag
5. **Målgrupp:** 3 drömkunder (namngivna bolag) och 3 bolag Kunden aldrig vill kontakta
6. **Avsändaradress** för mejl, och vem som kan lägga in DNS-poster (SPF/DKIM)
7. **Ärenden som alltid ska till människa** — t.ex. reklamationer över [X] kr,
   hot om rättsliga åtgärder, personuppgiftsbegäranden, uppsägningar
