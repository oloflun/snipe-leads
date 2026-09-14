"""Körningens överskrivningar ska nå ända fram — alla sju fälten.

Fyra av de sju saknades tills 2026-08-19: roller, signaler som krävs och de
diskvalificerande kom alltid från arbetsytans sparade ICP, hur formuläret än
fylldes i. Felet var tyst — en override som inte finns i modellen faller bort i
pydantic utan att någon får veta det, och körningen ser ut att ha lytt.

Det som mäts är därför INTE att fälten finns, utan att ett värde som skickas in
kommer ut i det renderade ICP:t. Ett fält som glider ur `LIST_FIELDS` eller ur
`har_nagot()` fäller det här testet.
"""

from app.api.schemas import LeadsRunOverrides
from app.leads.context_pack import _med_overrides
from app.leads.icp import LIST_FIELDS, render_icp

SPARAT = {
    "industries": ["Bygg"],
    "exclude_industries": ["Bemanning"],
    "geography": ["Skåne"],
    "roles": ["VD"],
    "must_have": ["Egen produktion"],
    "deal_breakers": ["Under 10 anställda"],
    "company_size": {"min": 1, "max": 49},
}

KORNINGEN = {
    "industries": ["Livsmedel"],
    "exclude_industries": ["Spel"],
    "geography": ["Norrbotten"],
    "roles": ["Platschef"],
    "must_have": ["Nyöppnad anläggning"],
    "deal_breakers": ["Franchise"],
}


def test_alla_listfalt_gar_att_overskriva():
    """Varje fält i LIST_FIELDS ska gå att styra per körning."""
    assert set(KORNINGEN) == set(LIST_FIELDS), (
        "Testet och LIST_FIELDS har glidit isär — lägg till fältet i båda."
    )

    sammanslagen = _med_overrides(SPARAT, KORNINGEN)
    renderat = render_icp(sammanslagen)

    for falt, varden in KORNINGEN.items():
        assert sammanslagen[falt] == varden, f"{falt} slogs inte ihop"
        assert varden[0] in renderat, f"{falt} nådde inte det renderade ICP:t"

    # Det sparade ska vara BORTA, inte tillagt. En override som lägger till
    # i stället för att ersätta breddar urvalet i tysthet.
    for varden in SPARAT.values():
        if isinstance(varden, list):
            assert varden[0] not in renderat


def test_modellen_slapper_igenom_alla_falten():
    """`har_nagot()` läste tidigare en handskriven lista som glömdes bort."""
    for falt, varden in KORNINGEN.items():
        modell = LeadsRunOverrides(**{falt: varden})
        assert modell.har_nagot(), f"{falt} räknas inte som en override"
        assert modell.model_dump(exclude_none=True) == {falt: varden}

    assert not LeadsRunOverrides().har_nagot()


def test_tomt_falt_behaller_det_sparade():
    """None betyder 'använd det sparade', inte 'inga branscher alls'."""
    sammanslagen = _med_overrides(SPARAT, {"geography": ["Norrbotten"]})
    assert sammanslagen["industries"] == ["Bygg"]
    assert sammanslagen["geography"] == ["Norrbotten"]


def test_storleken_gar_fortfarande_att_overskriva():
    sammanslagen = _med_overrides(SPARAT, {"anstallda_min": 50, "anstallda_max": 500})
    assert sammanslagen["company_size"] == {"min": 50, "max": 500}
    assert "50" in render_icp(sammanslagen)
