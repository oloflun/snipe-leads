"""Utvärderingsset: hur många frågor kan agenten besvara utan att svara fel?

Körs manuellt mot en LOKAL backend med Livrustnings kunskapsbas seedad. Det är
inget pytest-test — det är mätinstrumentet för avvägningen mellan täckning och
korrekthet, och siffrorna hör hemma i en commit-motivering, inte i CI.

    python -m tests.eval_livrustning <api-nyckel>

Varje fråga bär sitt FÖRVÄNTADE fack. Tre utfall räknas:
  träff      — besvarad, och underlaget kom ur rätt fack
  fel        — besvarad, men ur fel fack (det allvarliga: kunden får fel svar)
  överlämnad — eskalerad till människa

"överlämnad" är inte ett fel i sig. Saknas underlaget är överlämning rätt svar.
Målet är att minska överlämningarna som beror på att sökningen missade, utan att
öka "fel" ens med ett.
"""

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

# (fråga, förväntat fack, finns underlag i KB?)
CASES = [
    ("Hur lång är garantin på en hjärtstartare?", "garanti", True),
    ("Vad täcker garantin och vad gäller om den gått sönder?", "garanti", True),
    ("Vilka undantag finns från garantin?", "garanti", True),
    ("Jag vill ångra mitt köp, hur gör jag?", "retur_reklamation", True),
    ("Varan kom skadad, hur reklamerar jag?", "retur_reklamation", True),
    ("Vad kostar frakten?", "leverans", True),
    ("Hur snabbt kommer varan och vilket fraktbolag använder ni?", "leverans", True),
    ("När kommer mitt paket?", "leverans", True),
    ("Kan vi få faktura i stället för kortbetalning?", "betalning", True),
    ("Går det att delbetala en hjärtstartare?", "betalning", True),
    ("Vad kostar en hjärtstartare?", "betalning", True),
    ("Hur bokar vi en HLR-kurs för 15 personer?", "utbildning", True),
    ("Vad ingår i eHLR och kan den göras på distans?", "utbildning", True),
    ("Håller ni kurser hos oss på kontoret?", "utbildning", True),
    ("Vad är Hjärtsäker zon?", "ovrigt", True),
    ("Var ligger ni och hur kontaktar jag er?", "ovrigt", True),
    # Underlag saknas helt i deras KB — här SKA agenten lämna över.
    ("Vår hjärtstartare fungerar inte", "teknisk_support", False),
    ("Hjärtstartaren larmar med en röd blinkande lampa", "teknisk_support", False),
    ("Elektroderna har gått ut, hur byter jag dem?", "teknisk_support", False),
]


def call(path, key, payload=None, method="GET"):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "X-API-Key": key},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ask(key: str, question: str) -> dict:
    job = call("/api/chat", key, {"message": question, "customer_email": "eval@example.com"}, "POST")
    for _ in range(60):
        time.sleep(0.3)
        state = call(f"/api/jobs/{job['job_id']}", key)
        if state["status"] == "completed":
            return state["result"]
        if state["status"] == "failed":
            raise RuntimeError(state.get("error"))
    raise RuntimeError("jobbet blev aldrig klart")


def main() -> None:
    key = sys.argv[1]
    kb = call("/api/kb", key)
    by_title = {a["title"]: a["category"] for a in kb["articles"]}
    print(f"Kunskapsbas: {len(kb['articles'])} artiklar\n")

    hits = wrong = handed_over = 0
    for question, expected, has_material in CASES:
        result = ask(key, question)
        sources = result["kb_sources"]
        used = by_title.get(sources[0]["title"]) if sources else None

        if result["escalated"]:
            outcome, detail = "överlämnad", ""
            handed_over += 1
        elif used == expected or (expected == "garanti" and used == "retur_reklamation"):
            outcome, detail = "träff", f"<- {sources[0]['title']}"
            hits += 1
        else:
            outcome, detail = "FEL", f"<- {sources[0]['title']} ({used})"
            wrong += 1

        flag = "" if has_material else "  [inget underlag i KB]"
        # Triagens fack skrivs ut separat: ett fel svar kan bero antingen på att
        # facket blev fel eller på att sökningen missade inom rätt fack, och de
        # två kräver helt olika åtgärder.
        print(
            f"  {outcome:11} fack={result['category']:16} "
            f"{question[:46]:48} {detail}{flag}"
        )

    total = len(CASES)
    answerable = sum(1 for _, _, m in CASES if m)
    print(f"\n  träff       {hits}/{answerable} av de besvarbara")
    print(f"  FEL         {wrong}   (ska vara 0)")
    print(f"  överlämnad  {handed_over}/{total}")


if __name__ == "__main__":
    main()
