"""Constants for the Grid Clock integration.

cdn.gridclock.eu is a static, public JSON CDN (Cloudflare R2) that
infra/publisher.py in the GridClock backend publishes to. It is the same
data the Grid Clock app and website read - there is currently no
server-side bearer-token enforcement on it. This integration still sends
an ``Authorization: Bearer <key>`` header whenever an API key is
configured, so it keeps working unchanged if/when that CDN endpoint (or a
future dedicated partner endpoint) starts requiring one - see
infra/publisher.py's module docstring for the v1/... path layout this
mirrors.
"""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "gridclock"
PLATFORMS = ["sensor"]

CONF_ZONE = "zone"
CONF_API_KEY = "api_key"

API_BASE = "https://cdn.gridclock.eu"
API_SCHEMA = "v1"

# CDN cache-control on latest.json is "max-age=300, stale-while-revalidate=86400"
# (infra/publisher.py CACHE_LATEST) - polling every 5 minutes stays inside that
# window without hammering the CDN.
UPDATE_INTERVAL = timedelta(minutes=5)
REQUEST_TIMEOUT = 15

# Price values on the CDN are integers in 0.1 ct/kWh (infra/publisher.py UNIT).
# Divide by this to get ct/kWh.
PRICE_UNIT_DIVISOR = 10
PRICE_UNIT = "ct/kWh"

# Bidding zones and their display names, mirrored from infra/publisher.py's
# NAMES dict so the picker always matches what the CDN actually publishes.
ZONES: dict[str, dict[str, str]] = {
    "NL":      {"nl": "Nederland",                  "en": "Netherlands"},
    "BE":      {"nl": "België",                     "en": "Belgium"},
    "FR":      {"nl": "Frankrijk",                  "en": "France"},
    "DE_LU":   {"nl": "Duitsland en Luxemburg",      "en": "Germany and Luxembourg"},
    "AT":      {"nl": "Oostenrijk",                 "en": "Austria"},
    "CH":      {"nl": "Zwitserland",                "en": "Switzerland"},
    "IT_NORD": {"nl": "Italië Noord",                "en": "Italy North"},
    "IT_CNOR": {"nl": "Italië Midden-Noord",         "en": "Italy Centre-North"},
    "IT_CSUD": {"nl": "Italië Midden-Zuid",          "en": "Italy Centre-South"},
    "IT_SUD":  {"nl": "Italië Zuid",                 "en": "Italy South"},
    "IT_SICI": {"nl": "Sicilië",                     "en": "Sicily"},
    "IT_SARD": {"nl": "Sardinië",                    "en": "Sardinia"},
    "IT_CALA": {"nl": "Calabrië",                    "en": "Calabria"},
    "ES":      {"nl": "Spanje",                     "en": "Spain"},
    "PT":      {"nl": "Portugal",                   "en": "Portugal"},
    "PL":      {"nl": "Polen",                      "en": "Poland"},
    "CZ":      {"nl": "Tsjechië",                    "en": "Czechia"},
    "SK":      {"nl": "Slowakije",                  "en": "Slovakia"},
    "HU":      {"nl": "Hongarije",                  "en": "Hungary"},
    "RO":      {"nl": "Roemenië",                    "en": "Romania"},
    "IE_SEM":  {"nl": "Ierland",                    "en": "Ireland"},
    "DK_1":    {"nl": "Denemarken West",            "en": "Denmark West"},
    "DK_2":    {"nl": "Denemarken Oost",            "en": "Denmark East"},
    "SE_1":    {"nl": "Zweden 1 (Luleå)",            "en": "Sweden 1 (Luleå)"},
    "SE_2":    {"nl": "Zweden 2 (Sundsvall)",       "en": "Sweden 2 (Sundsvall)"},
    "SE_3":    {"nl": "Zweden 3 (Stockholm)",       "en": "Sweden 3 (Stockholm)"},
    "SE_4":    {"nl": "Zweden 4 (Malmö)",            "en": "Sweden 4 (Malmö)"},
    "NO_1":    {"nl": "Noorwegen 1 (Oslo)",         "en": "Norway 1 (Oslo)"},
    "NO_2":    {"nl": "Noorwegen 2 (Kristiansand)", "en": "Norway 2 (Kristiansand)"},
    "NO_3":    {"nl": "Noorwegen 3 (Trondheim)",    "en": "Norway 3 (Trondheim)"},
    "NO_4":    {"nl": "Noorwegen 4 (Tromsø)",        "en": "Norway 4 (Tromsø)"},
    "NO_5":    {"nl": "Noorwegen 5 (Bergen)",       "en": "Norway 5 (Bergen)"},
    "FI":      {"nl": "Finland",                    "en": "Finland"},
    "EE":      {"nl": "Estland",                    "en": "Estonia"},
    "LV":      {"nl": "Letland",                    "en": "Latvia"},
    "LT":      {"nl": "Litouwen",                   "en": "Lithuania"},
    "GR":      {"nl": "Griekenland",                "en": "Greece"},
    "BG":      {"nl": "Bulgarije",                  "en": "Bulgaria"},
    "HR":      {"nl": "Kroatië",                     "en": "Croatia"},
    "SI":      {"nl": "Slovenië",                   "en": "Slovenia"},
    "RS":      {"nl": "Servië",                     "en": "Serbia"},
}

DEFAULT_ZONE = "NL"
