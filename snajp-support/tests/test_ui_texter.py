"""Kör scripts/granska_ui_texter.py i ordinarie testkörning, så att nya
stavfel i hårdkodad användarsynlig text fångas innan de når en kund.
Skannern är kurerad (inte en fullständig ordlista) — nya fel läggs till i
FELSTAVNINGAR i app/textkvalitet.py när de upptäcks.
"""

import subprocess
import sys
from pathlib import Path


def test_ui_texter_fria_fran_kanda_sprakfel():
    rot = Path(__file__).resolve().parents[2]
    skript = rot / "scripts" / "granska_ui_texter.py"
    assert skript.exists(), skript
    resultat = subprocess.run(
        [sys.executable, str(skript)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=rot,
    )
    assert resultat.returncode == 0, f"Skannern fann språkfel:\n{resultat.stdout}"
