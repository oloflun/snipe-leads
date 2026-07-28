"""Kunskapsbas för den PUBLIKA DEMON.

Demon föreställer "Nordpuls Medical", ett påhittat bolag som säljer
hjärtstartare — samma bransch som piloten, så att demon visar den verkliga
användningen i stället för ett orelaterat e-handelsexempel.

Innehållet är samma struktur som `kb_templates.KB_TEMPLATE`, men utan
platshållarmarkering: demon ska kunna svara på riktigt, medan en ny pilotkund
får samma artiklar tydligt märkta som utkast att ersätta.
"""

from .kb_templates import as_articles

DEMO_COMPANY = "Nordpuls Medical"

# Färdig text (prefixed=False) — demon svarar med den här som underlag.
KB_ARTICLES: list[dict] = as_articles(prefixed=False)
