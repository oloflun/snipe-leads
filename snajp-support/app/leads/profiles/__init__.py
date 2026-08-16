"""ICP-FÖRSLAG per kund.

Filerna här är **förslag att godkänna**, inte sanningar. Ingen av dem läses
automatiskt av pipelinen: en profil blir verklig först när någon medvetet
skriver in den via `PUT /api/leads/config`, och då passerar den samma strikta
validering som allt annat kundskrivet.

Skälet att de ändå ligger i kod: ett ICP-förslag bygger på antaganden om vem
kundens nästa kund är, och de antagandena ska gå att läsa, ifrågasätta och
diffa. Ett förslag som bara existerar i ett samtal går inte att granska i
efterhand — och när urvalet visar sig fel är frågan alltid "vad antog vi?".
"""

from __future__ import annotations

from .livrustning import LIVRUSTNING_ICP_FORSLAG, LIVRUSTNING_MOTIVERING

__all__ = ["LIVRUSTNING_ICP_FORSLAG", "LIVRUSTNING_MOTIVERING"]
