"""Kunskapsbasens kategori "salj" och supportens ärendefack hålls isär.

"salj" (sv "Erbjudande och säljfakta", en "Offer and sales facts") finns bara
i kunskapsbasen (config.KB_CATEGORIES, CHECK-villkoret på
ss_knowledge_base.category). Triage, ärenden, regler och agentens
ärendeverktyg läser config.CATEGORIES och får aldrig välja "salj": ett ärende
i det facket har ingen regel, ingen etikett och ingen plats i inkorgen.
"""

from pathlib import Path

from app.agent.triage import tolka_svar
from app.api.schemas import KbArticle
from app.config import CATEGORIES, CATEGORY_LABELS, DEFAULT_CATEGORY_RULES, KB_CATEGORIES

MIGRATIONER = Path(__file__).resolve().parents[2] / "db" / "migrations"


def test_salj_ar_en_kunskapsbaskategori_men_inget_arendefack():
    assert "salj" in KB_CATEGORIES
    assert set(CATEGORIES) < set(KB_CATEGORIES)
    assert "salj" not in CATEGORIES
    assert "salj" not in CATEGORY_LABELS
    assert "salj" not in DEFAULT_CATEGORY_RULES


def test_triagen_kan_inte_valja_salj():
    assert tolka_svar({"kategori": "salj"}, [])["category"] == "ovrigt"
    assert tolka_svar({"category": "salj"}, [])["category"] == "ovrigt"


def test_artikelschemat_tar_salj():
    assert KbArticle(title="Pris", content="Från 149 kr i månaden.", category="salj").category == "salj"


def test_migrationen_tillater_salj_i_kunskapsbasen():
    filer = [p for p in MIGRATIONER.glob("*.sql") if "kb_kategori_salj" in p.name]
    assert len(filer) == 1
    sql = filer[0].read_text(encoding="utf-8")
    assert "ss_knowledge_base_category_check" in sql
    assert "'salj'" in sql
    # Ärendenas fack rörs inte (kommentarerna nämner dem, satserna gör det inte).
    satser = "\n".join(rad for rad in sql.splitlines() if not rad.lstrip().startswith("--"))
    assert "ss_tickets" not in satser
    assert "ss_classifications" not in satser
