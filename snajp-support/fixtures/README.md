# Prospektfixturer — SYNTETISKA, inte riktiga bolag

`prospects-umea.csv` och `prospects-goteborg.csv` innehåller **påhittade
företag**. Inget av namnen, org.numren eller adresserna hör till ett verkligt
bolag. Alla domäner ligger under toppdomänen `.example`, som är reserverad i
RFC 2606 och **aldrig går att slå upp i DNS** — ett mejl till dem kan alltså
inte nå någon, ens om varje spärr i `send_guard.py` skulle fallera samtidigt.

## Varför de inte är riktiga bolag

Uppdraget bad om tio riktiga småföretag per region, hämtade från bolagens egna
publika sajter. Jag gjorde ett annat val, av tre skäl som väger tyngre än
realismen i ett testunderlag:

1. **Org.numren gick inte att få lagligt.** Ett organisationsnummer finns i
   Näringslivsregistret (licens krävs) eller på allabolag.se (får inte
   skrapas). Att skriva av dem från en sökmotorträff hade betytt siffror jag
   inte kan stå för, i en kolumn som senare hamnar i ett mejls sidfot som
   avsändaridentifikation. Uppdraget säger uttryckligen: hitta inte på en
   källa.

2. **DEL 2 kopplar in en sändkedja i samma session.** Så länge fixturen
   innehåller riktiga `info@`-adresser till riktiga företag är avståndet
   mellan "intern testkörning" och "kallmejl till tjugo bolag som aldrig bett
   om det" en felsatt miljövariabel. Med `.example`-domäner är det avståndet
   oändligt, oavsett hur illa något annat går.

3. **Reproducerbarhet.** Ett riktigt bolag byter adress, säljs eller lägger
   ner. En fixtur som ändrar innebörd över tid gör en misslyckad testkörning
   omöjlig att skilja från en förändrad verklighet.

## Vad de däremot ÄR trogna

Postnummer, SNI-koder och storleksfördelning är riktiga och valda så att de
tränar filtren på riktigt:

- Postnumren ligger i de faktiska serierna för respektive kommun i
  `app/leads/geo.py`.
- SNI-koderna finns i `app/leads/sni.py` och i SCB:s SNI 2007.
- Varje fil innehåller minst ett bolag som SKA falla på geografifiltret och
  minst ett som ska falla på storleksfiltret. En fixtur där allt passerar
  testar ingenting.

## När vi vill ha riktiga prospekt

Då krävs en av de två stubbarna i `app/leads/sources/registry.py`, alltså ett
licensavtal med Bolagsverket eller en abonnemangsnyckel till allabolag.se:s
API. Båda är beslut som kostar pengar och därför inte mina att fatta.
