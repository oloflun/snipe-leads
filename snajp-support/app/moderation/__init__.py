"""Tonläges- och påhoppsbedömning, delad av alla tre agenterna.

Bodde i `app/leads/` tills 2026-08-24 trots att bara support använde den.
Flytten hit är en flytt av ANSVAR, inte bara av en fil: att avgöra om ett
inkommande meddelande bär ett hot är plattformsinfrastruktur, precis som
`agentcore/` och `storage/`, och inte agentlogik.

Det bryter inte principen om att bokföringsagenten inte delar prompt, playbook
eller verktyg med de andra (se `agent/bookkeeping_agent.py`). Modulen här bär
ingen prompt och inget verktyg — den läser en sträng och returnerar ett beslut.
Vad beslutet ska LEDA till avgör varje agent för sig.
"""
