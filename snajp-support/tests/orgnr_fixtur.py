"""Ett giltigt, deterministiskt orgnr per bolagsnamn för testfixtures.

Samma orgnr på två bolag är samma bolag för dubblettspärren
(app/leads/upptagna.py): fixtures som gav alla kandidater "556824-9022"
föll när spärren började läsas om före varje skrivning (2026-10-06).
"""

import zlib


def orgnr_for(namn: str) -> str:
    bas = f"556{zlib.crc32(namn.encode('utf-8')) % 1_000_000:06d}"
    summa = sum(
        (d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 == 0 else d for i, d in enumerate(int(c) for c in bas)
    )
    return f"{bas[:6]}-{bas[6:]}{(10 - summa % 10) % 10}"


if __name__ == "__main__":
    from app.leads.orgnr import juridisk_form  # noqa: F401 — finns modulen fungerar importen

    assert orgnr_for("Ett AB") != orgnr_for("Två AB") and orgnr_for("Ett AB") == orgnr_for("Ett AB")
    print("orgnr_fixtur: ok", orgnr_for("Ett AB"))
