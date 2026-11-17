# Säkerhet / Security

[Svenska](#svenska) · [English](#english)

---

## Svenska

### Rapportera en sårbarhet

Har du hittat en säkerhetsbrist i Snajp (webbplatsen www.snajp.se, appen,
chattwidgeten eller backenden i det här repot)? Rapportera den privat, inte i
ett öppet ärende:

1. **Föredraget:** GitHubs privata sårbarhetsrapportering. Öppna fliken
   **Security** i repot och välj **Report a vulnerability**. Rapporten syns
   bara för dig och för oss.
2. **Annars:** mejla **kontakt@snajp.se** med ämnesraden "Säkerhet".

Skriv inte om bristen i ett öppet ärende, en pull request eller någon annan
offentlig kanal innan vi har åtgärdat den.

### Vad rapporten bör innehålla

- Vilken del som berörs (adress, endpoint eller fil i repot).
- Vad bristen är och vad en angripare skulle kunna göra med den.
- Steg för att återskapa den, så korta som möjligt.
- Hur du upptäckte den och när.
- Hur vi når dig för följdfrågor.

### Spelregler

- Testa bara mot ditt eget konto och din egen data. Läs, ändra eller radera
  aldrig andras uppgifter. Råkar du komma åt någon annans data: sluta
  direkt, spara ingenting och berätta i rapporten vad du såg.
- Stör inte driften: ingen överbelastning, inga massutskick, ingen
  automatiserad skanning som påverkar tjänsten för andra.
- Ingen social manipulation av oss, våra kunder eller deras kunder, och inga
  fysiska intrång.

### Vad du kan förvänta dig

- Bekräftelse på att vi tagit emot rapporten inom **[FYLL: antal]
  arbetsdagar**.
- En första bedömning och, när det går, en plan för åtgärden.
- Besked när bristen är åtgärdad. Vill du nämnas när vi berättar om
  rättelsen gör vi det.

Berör bristen personuppgifter hanterar vi den enligt vår incidentrutin
([INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)), som bland annat följer
GDPR:s frist på 72 timmar för anmälan till IMY.

---

## English

### Reporting a vulnerability

Found a security issue in Snajp (the website www.snajp.se, the app, the chat
widget or the backend in this repository)? Please report it privately, not
in a public issue:

1. **Preferred:** GitHub private vulnerability reporting. Open the
   **Security** tab of this repository and choose **Report a
   vulnerability**. Only you and we can see the report.
2. **Otherwise:** email **kontakt@snajp.se** with the subject "Security".

Please do not discuss the issue in a public issue, pull request or any other
public channel until we have fixed it.

### What to include

- The affected part (URL, endpoint or file in the repository).
- What the issue is and what an attacker could do with it.
- Steps to reproduce it, as short as possible.
- How and when you found it.
- How we can reach you with follow-up questions.

### Rules of engagement

- Only test against your own account and your own data. Never read, change
  or delete other people's data. If you do reach someone else's data by
  accident: stop immediately, keep nothing and tell us in the report what
  you saw.
- Do not disrupt the service: no load testing, no mass sending, no automated
  scanning that affects the service for others.
- No social engineering of us, our customers or their customers, and no
  physical intrusion.

### What you can expect

- Confirmation that we received your report within **[FYLL: antal]
  business days**.
- An initial assessment and, where possible, a plan for the fix.
- Word when the issue is fixed. If you would like to be credited when we
  describe the fix, we will do so.

If the issue involves personal data, we handle it under our incident
routine ([INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)), which among other
things follows the GDPR 72-hour deadline for notifying the supervisory
authority (IMY).
