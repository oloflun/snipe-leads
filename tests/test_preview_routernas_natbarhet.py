"""En route som påstås gå att nå direkt måste faktiskt gå att nå.

`lib/routes.ts` säger om `preview: true` att routen "finns och fungerar" och
att flaggan bara styr vad som VISAS i menyn. `AppShell` räknade samtidigt ut
sin stranded-effekt ur menyns routes — alltså utan preview-routerna — och
studsade därför varje sådan adress tillbaka till `/dashboard`.

Följden: /dashboard/companies, /contacts, /inbox, /analytics och /assistant
gick inte att öppna alls som kund. Ingen av filerna såg fel ut för sig; det är
motsägelsen MELLAN dem som var felet, och den sortens fel överlever en
kodgranskning eftersom bara den ena filen är öppen åt gången.

Testet läser filerna som text i stället för att köra TypeScript. Det räcker för
frågan som ställs, och det kan köras i samma svit som resten.
"""

from __future__ import annotations

import re
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
APPSHELL = (ROT / "components" / "AppShell.tsx").read_text(encoding="utf-8")
ROUTES = (ROT / "lib" / "routes.ts").read_text(encoding="utf-8")


def test_stranded_raknas_med_preview_routerna():
    """Underlaget för stranded MÅSTE innehålla preview-routerna.

    Kravet uttrycks som `includePreview: true` i det anrop vars resultat
    stranded räknas ur. Utan flaggan är varje preview-route onåbar för en
    inloggad kund.
    """
    # Blocket från deklarationen av underlaget till och med stranded-uträkningen.
    block = APPSHELL.split("const stranded")[0].split("const navRoutes")[1]

    assert "includePreview: true" in block, (
        "AppShell räknar stranded ur menyns routes. Preview-routerna saknas då i "
        "underlaget, och varje sådan adress studsar tillbaka till /dashboard — "
        "trots att lib/routes.ts påstår att de nås direkt."
    )


def test_stranded_behaller_scope_filtret():
    """Skyddet mot att smalna av vyn och bli kvar på en sida man inte kan nå.

    Det är hela skälet till att effekten finns. Ett underlag utan `shows()`
    hade tagit bort den, och symptomet — en användare kvar på en leads-sida
    efter att ha växlat till Support — hade inte synts i något annat test.
    """
    block = APPSHELL.split("const stranded")[0].split("const navRoutes")[1]

    assert "shows(route.product)" in block, (
        "Underlaget för stranded filtrerar inte längre på scope. Den som växlar "
        "till Support medan de står på en leads-sida blir kvar där."
    )


def test_routes_pastar_fortfarande_att_preview_nas_direkt():
    """Om påståendet tas bort ska testet ovan omprövas, inte tyst gälla vidare.

    Det som gör motsägelsen till ett fel är att lib/routes.ts LOVAR något.
    Ändras löftet är det här testet fel fråga att ställa.
    """
    assert "nås fortfarande direkt" in ROUTES

    # Och det ska faktiskt finnas preview-routes att prata om.
    assert len(re.findall(r"preview:\s*true", ROUTES)) >= 3
