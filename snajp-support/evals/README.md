# Evalsviterna

Realistiska fall per agent med en bedömningsmall som går att räkna ut
mekaniskt. Sviterna körs mot en driftsatt miljö med riktig modell, före och
efter en ändring av promptar, modell eller kedja.

| Agent | Fil | Körs genom | Kriterier |
|---|---|---|---|
| Support | `support_livrustning.json` | chatten (`POST /api/chat`, `is_test`) | utfall, fakta, inga fel, format |
| Iris | `iris_utkast.json` + `iris_rubrik.json` | utkastvägen (`POST /api/leads/outreach/draft`) | levererat, inga påhitt, skrivregler (signalen är en upplysning) |
| Kvittohanteraren | `kvitto.json` | uppladdningen (`POST /api/kvitton/underlag`) | status, belopp, fält |

Supportens fall bygger på Livrustnings kunskapsbas (`kb/livrustning.json`, en
ögonblicksbild 2026-11-10): det sviten kräver av ett svar står i en artikel
där, och `tests/test_evalsviter.py` kontrollerar det.

## Köra

```bash
cd snajp-support
python -m evals.kor forbered --env development      # en gång: egna evalkunder med kunskapsbasen
python -m evals.kor kor --env development --agent alla --etikett fore
# ... ändringen rullas ut ...
python -m evals.kor kor --env development --agent alla --etikett efter
python -m evals.kor jamfor fore efter
```

Resultaten skrivs till `docs/stabilitet-2026-11/eval/<etikett>-<agent>.json`
med varje falls svar, kriterier och svarstid. Sviterna körs aldrig mot
produktionen (`--env main` avvisas).

Kvittohanteraren får en ny evalkund vid varje körning: samma dokument en
gång till hos samma kund flaggas, med rätta, som möjliga dubbletter.

Evalkunderna är egna kunder (`eval-…`) utan koppling till någon riktig kund.
Nycklarna läggs i `.env.deploy` som `EVAL_<MILJÖ>_NYCKLAR` och skrivs aldrig
ut. Iris fördelas över flera evalkunder, eftersom leadsbudgeten räknas per
kund och dygn och ett utkast läser över hundratusen tokens.

## Bedömningen

Ett fall är godkänt när alla dess kriterier håller (`bedomning.py`). Rapporten
visar också andelen per kriterium och per falltyp, så att det syns vad som
brister. Mallen är deterministisk: ingen andra modell dömer, och samma svar
ger samma poäng.

Det mallen inte mäter: tonen i ett svar, och om ingången i ett utkast är den
bästa möjliga. Det står under `ovrigt` i Iris rubrik och bedöms av en
människa på de sparade svaren.

## Lägga till fall

Ett fall som fälldes i drift hör hemma här: frågan, det förväntade utfallet
och det svaret måste eller inte får innehålla. Sviterna ska ha minst trettio
fall var; `tests/test_evalsviter.py` håller i det och i fallens form.
