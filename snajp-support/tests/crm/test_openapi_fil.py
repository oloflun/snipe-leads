"""docs/crm/openapi.json är specifikationen kunden får. Den ska stämma med koden."""

from __future__ import annotations

import json
from pathlib import Path

from app.api import crm_v1

FIL = Path(__file__).resolve().parents[3] / "docs" / "crm" / "openapi.json"


def test_specifikationen_i_docs_stammer_med_koden():
    assert FIL.exists(), "Kör: python scripts/crm_openapi.py"
    assert json.loads(FIL.read_text(encoding="utf-8")) == json.loads(json.dumps(crm_v1.specifikation())), (
        "docs/crm/openapi.json är inaktuell. Kör: python scripts/crm_openapi.py"
    )


def test_varje_felkod_i_koden_ar_stabil_och_dokumenterad():
    """Felkoderna är en del av kontraktet: en integration grenar på dem."""
    import re

    from app.api import crm_v1_berikning, crm_v1_objekt, crm_v1_sparr, crm_v1_tidslinje

    kalla = "".join(Path(m.__file__).read_text(encoding="utf-8")
                    for m in (crm_v1, crm_v1_objekt, crm_v1_tidslinje, crm_v1_sparr, crm_v1_berikning))
    koder = set(re.findall(r'fel\(\s*\d{3},\s*"([a-z_]+)"', kalla)) | {"rate_limited"}
    guide = (FIL.parent / "API.md").read_text(encoding="utf-8")
    saknas = sorted(k for k in koder if f"`{k}`" not in guide)
    assert not saknas, f"Felkoder som saknas i docs/crm/API.md: {saknas}"
