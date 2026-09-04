# Grid Clock — Home Assistant custom integration

Haalt dag-vooruit elektriciteitsprijzen (15 min resolutie voor NL, andere
zones kunnen een ander interval publiceren — zie `resolution_minutes`) op
uit `cdn.gridclock.eu`, met een optionele bearer-key.

## Waarom "optioneel"

`cdn.gridclock.eu` is vandaag een publieke, onbeveiligde CDN (dezelfde
`v1/prices/{zone}/latest.json`-bestanden die de Grid Clock-app en -website
gebruiken — zie `infra/publisher.py` in het GridClock-project). Er is nog
geen serverside bearer-verificatie. Deze integratie stuurt de sleutel dus
gewoon mee als je er één invult (`Authorization: Bearer <key>`), en werkt
ook prima zonder — zo blijft hij werken zonder wijzigingen zodra je ooit
wél verificatie toevoegt.

## Installatie

1. Kopieer deze map (`custom_components/gridclock`) naar
   `<jouw HA-config-map>/custom_components/gridclock`.
2. Herstart Home Assistant.
3. Instellingen → Apparaten en diensten → Integratie toevoegen → "Grid Clock".
4. Kies je biedzone (bv. Nederland) en vul optioneel je bearer-sleutel in.

De sleutel later wijzigen kan via de integratie-opties (tandwiel-icoon),
zonder de integratie opnieuw te hoeven toevoegen.

## Entiteiten

Per geconfigureerde zone, gegroepeerd onder één apparaat ("Grid Clock NL"):

- **Huidige prijs** (`sensor.grid_clock_nl_current_price`) — prijs van het
  kwartier waar "nu" in valt, in ct/kWh.
- **Prijzen** (`sensor.grid_clock_nl_prices`) — state = aantal bekende
  kwartieren; attributen `prices` ( `[{"startsAt": ..., "total": ...}, ...]`,
  net als `sensor.epex_prices` uit `epex_live_sensors.yaml`) en `knownUntil`.

## Migreren van de EPEX/EVI-opstelling

`home assistant/packages/epex_live_sensors.yaml` en `epex_live_helpers.yaml`
gebruiken vandaag `sensor.epex_prices` (bron: `epex.goldschmitz.be`, niet
onder jouw beheer). De `prices`-attribuutvorm van `sensor.grid_clock_*_prices`
is bewust identiek, dus je kunt in `epex_live_sensors.yaml` overal
`state_attr('sensor.epex_prices', ...)` vervangen door
`state_attr('sensor.grid_clock_nl_prices', ...)` en `sensor.epex_current_price`
door de nieuwe `sensor.grid_clock_nl_current_price` — de rest van de
template-keten (afname/injectie/BTW-berekening, "goedkoop nu") blijft
ongewijzigd werken. Dit bestand doet die vervanging niet automatisch; dat is
bewust een aparte stap zodra je hebt geverifieerd dat de nieuwe sensoren goede
data leveren.

## Bestanden

- `const.py` — zone-lijst (gespiegeld van `infra/publisher.py`'s `NAMES`),
  CDN-basis-URL, update-interval (elk uur; bij het toevoegen van een
  biedzone wordt meteen ook al opgehaald, via de testcall in `config_flow.py`
  en de eerste refresh van de coordinator).
- `coordinator.py` — haalt en parseert `v1/prices/{zone}/latest.json`.
- `config_flow.py` — UI-setup (zone-keuze + bearer-sleutel), met een
  live testcall zodat een foute sleutel of onbereikbare CDN meteen zichtbaar is.
- `sensor.py` — de twee entiteiten hierboven.
- `brand/` — `icon.png`/`icon@2x.png`/`logo.png`/`logo@2x.png`: het
  Grid Clock-logo voor de integratietegel in Instellingen → Apparaten en
  diensten. Sinds HA 2026.3 pikt Home Assistant deze lokale map automatisch
  op (geen aparte PR naar de publieke `home-assistant/brands`-repo nodig,
  want dat is voor deze private integratie sowieso niet toepasselijk). Op
  oudere HA-versies val je terug op het generieke puzzel-icoon — geen fout,
  gewoon minder mooi.
