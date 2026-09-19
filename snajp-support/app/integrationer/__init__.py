"""Integrationer: support-agenten mot kundens egna system (bd snipe-36u).

Ebbots löfte, som vi bygger motsvarigheten till: agenten "går att integrera
med de flesta ärendehanterings- och CRM-system, samt övriga verktyg i
serviceflödet, så länge det finns öppna API:er eller stöd för Model Context
Protocol (MCP)". Två vägar in, per kund:

  HTTP   modell.HttpKonfig: Ebbot-kompatibel `requests`-array. Varje förfrågan
         blir ett verktyg (http_verktyg.py).
  MCP    modell.McpKonfig: en fjärr-MCP-server, vars verktyg listas och
         anropas via det officiella SDK:t (mcp_klient.py).

Och två sätt de används:

  uppslag.py    modellen väljer verktyg i ett eget steg i support-kedjan,
                koden anropar. Resultatet blir en faktakälla.
  handelser.py  koden anropar vid en händelse (arende_eskalerat), till
                exempel för att skapa ärendet i kundens Zendesk.

Säkerheten sitter i tre lager, alla i kod:

  natvakt.py      bara publika https-adresser, varje omdirigering prövad,
                  tids- och storleksgräns.
  hemligheter.py  kundens nycklar krypterade i vila, aldrig i prompten,
                  tvättade ur varje svar.
  modell.py       modellens argument kan aldrig välja server, skriva över en
                  hemlighet eller kodens kontextvärden (kund.email).
"""
