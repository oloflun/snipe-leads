# Jämförelsesidornas källor

Underlaget till `/jamfor-ai-sdr` och `/jamfor-supportagenter`, kontrollerat
**2026-11-06** mot varje leverantörs egna sidor. Datan som sidorna visar bor i
`lib/jamforelser.ts`; den här filen är beviset bakom den.

**Regler (marknadsföringslagen, jämförande reklam):** varje uppgift ska gå att
kontrollera på leverantörens egen sida. Det som inte står där är "Ej angivet",
aldrig en gissning. Snajp säljer två av verktygen och säger det på sidan. Kör
om kontrollen före varje större ändring och minst var tredje månad; ändra
`KONTROLLERAD` i `lib/jamforelser.ts` när det är gjort.

## AI-SDR och leadsagenter

| Leverantör | Källor | Det sidan bygger på |
|---|---|---|
| AI Kollegorna (Erik) | aikollegorna.se, /erik-b2b-saljaren, /priser, /faq | AI-säljare för svenska B2B via mejl och LinkedIn. "det som går ut … godkänner ni först" (FAQ). "All lagring och drift sker på servrar inom EU"; krävande uppgifter i amerikanska modeller med SCC. 4 900 kr/mån exkl. moms, ingen startavgift. Skrivspråk ej uttryckligen angivet. |
| Revexa (Leo) | revexa.io, /pris, /docs/sakerhet-och-gdpr, /blogg/ai-saljagent-pa-svenska | AI-SDR via LinkedIn och mejl efter köpsignaler. "Svenska till svenska köpare" (bloggen). "Som standard säger ni ja till varje meddelande". Databas och drift inom EU, krypterade säkerhetskopior i USA. 999 kr/mån exkl. moms, 7 dagar gratis. |
| Salesforge (Agent Frank) | salesforge.ai, /agent/frank, /pricing, /privacy | AI-SDR för mejl och LinkedIn. Svenska bland 20+ språk. Co-Pilot: granskning före utskick; Auto-Pilot utan. Servrar inom EU. /pricing: 499 USD/mån; FAQ: från 599 USD/mån kvartalsvis. Siten säger emot sig själv; sidan anger 499 USD och noten. |
| 11x (Alice) | 11x.ai, /products/alice/pricing, docs.11x.ai | Utgående agent för mejl och sociala kanaler. "Multi-language Outreach (105+)", svenska ej nämnt. Godkännande valfritt. AWS, region ej angiven. Growth från 3 750 USD/mån, årsvis. |
| SuperOffice Lead Agent | docs.superoffice.com (lead-agent), superoffice.com/content/system-of-action/ | Hittar och kvalificerar prospekt i CRM:et; dokumentationen nämner inga utskick. "coming soon" / "early access". Säljaren godkänner. "Hosted in the EU". Pris ej publicerat, kräver CRM Suite Plus. |
| Sista AI | sista.ai, /sv/services/ai-sales-agents-sdr | Konsultbolag i Amsterdam som bygger säljagenter (mejl, LinkedIn, SMS). Människa godkänner i piloten. Lagring ej angiven. Pilot 7 000 EUR fast pris. |

Nämns ofta men gör något annat (står i sidans frågor, inte i tabellen):
Rebel/getrebelos.com (kontaktdatabas, "We don't send on your behalf"),
Kust IT KIT Lead Agent (navigeringsbot på hemsidan), hirefinn.ai Finn (röstagent
för inkommande leads), Leadsson (köpta listor), Franzens Leads (pay per lead, B2C).

## Supportagenter och chattbotar

| Leverantör | Källor | Det sidan bygger på |
|---|---|---|
| ImBox (ImBot) | imbox.se/chatbot/, /priser/, /gdpr/ | Kundtjänstplattform med AI-chatbot tränad på företagets eget innehåll. Byter språk automatiskt (svenska ej nämnt). Lämnar över till mänsklig agent. Servrar inom EU/ESS. Pris efter demo. |
| Kundo (AI Chat) | kundo.se/ai-chat, /mail | Svensk ärendehantering. AI-chatten svarar bara ur kopplade källor, översätter i realtid. En agent tar över med hela konversationen. Data inom EU, språkmodellen via OpenAI i Azures EU-miljö. Pris ej publicerat. |
| Ebbot | ebbot.com, /platform/chat-agent, /platform/email-agent | AI-agenter för chatt och mejl, svar ur godkänd kunskap, 100+ språk. Överlämning till människa. Lagringsplats ej angiven ("EU and US environments"). Pris ej publicerat. |
| Dstny | dstny.se/produkter/dstny-chatbot, /produkter/ai-tjanster/voice-agent | Chatbot på hemsidan och röstagent; Voice Agent har svenska i språklistan och lagrar data i Azure Sweden Central. Överlämning till live chat/människa. Pris ej publicerat. |
| chattbot.se | chattbot.se, /allmanna-villkor/ | Chatbot för kundsupport med kopplingar till chattappar. Kunskapsbas, svenska svar, överlämning och lagring ej angivna. Från 899 kr/mån (exkl. moms enligt villkoren), 30 dagar gratis. |
| Zendesk AI agents | zendesk.com/service/ai/ai-agents/, /pricing/, support.zendesk.com (språk) | AI-agenter i webb, mejl, röst. Svenska i språklistan. EES-lagring som tillägg (gratis från Suite Professional). Suite Team 55 USD per agent/mån årsvis; AI-ärenden utöver kvoten kostar extra. |
| Intercom Fin | fin.ai/pricing, intercom.com/help (språk, datalagring) | AI-agent i chatt, mejl, röst. Svenska i språklistan. USA som standard, EU på avtal. 0,99 USD per löst ärende. |

Inte med i tabellen: Freshdesk (två officiella prissidor säger olika), Boost.ai
(köps av Automation Anywhere, inga publicerade språk eller priser), AI-byrån
(byrå som bygger på beställning, inget pris).

## Var listorna som AI-svaren citerar tar in leverantörer

| Lista | Väg in |
|---|---|
| businesswith.se/chatbot, /lead-generation-verktyg | hub.businesswith.com → "List your SaaS" (HubSpot-formulär), leverantörsportal app.businesswith.com. Kräver konto; pris för grundlistning ej publicerat. |
| getrebelos.com/sv/blog/ai-sdr-verktyg | Ingen anmälan. Kontakt hello@ / press@getrebelos.com. Skrivet av Rebels vd, som själv säljer i kategorin. |
| revexa.io bloggar | Ingen anmälan. hey@revexa.io. Revexa säljer själv en AI-SDR. |
| alicelabs.ai/sv/insights | Ingen anmälan. linus@alicelabs.ai (författare). Nästa översyn 2026-12-16/18. |
| revenuebase.ai/companies/ai-sdr-platforms/sweden | Byggs automatiskt ur bolagets egen beskrivning och säte i Sverige. Ingen anmälan; "Report an issue" per rad. |
