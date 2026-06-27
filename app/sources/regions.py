"""EU country list shared by the frontend region picker and result-side location filtering.

key:     display label shown in the UI; also passed verbatim to the LinkedIn API as the
         location string (LinkedIn accepts country names and "European Union" directly).
code:    ISO 3166-1 alpha-2 — kept for reference; not used by any job-board API.
aliases: lowercase substrings matched against job.location for result-side filtering.
         Includes local-language name and major cities so city-level results are not
         filtered out when the user selects a country.
"""
from __future__ import annotations

REGIONS: list[dict] = [
    # ── Pan-EU ───────────────────────────────────────────────────────────────
    {
        "key": "European Union",
        "code": "eu",
        "aliases": [
            "european union", "europe",
            # all 27 member states listed so any EU city-level result passes through
            "germany", "france", "italy", "spain", "poland", "netherlands",
            "belgium", "sweden", "austria", "denmark", "finland", "ireland",
            "portugal", "czech", "romania", "hungary", "slovakia", "bulgaria",
            "croatia", "slovenia", "estonia", "latvia", "lithuania",
            "luxembourg", "cyprus", "malta", "greece",
        ],
    },
    # ── Germany (primary target) ──────────────────────────────────────────────
    {
        "key": "Germany",
        "code": "de",
        "aliases": [
            "germany", "deutschland",
            "berlin", "munich", "münchen", "hamburg", "frankfurt",
            "cologne", "köln", "düsseldorf", "stuttgart", "dortmund",
            "essen", "leipzig", "bremen", "dresden", "hannover", "nuremberg", "nürnberg",
        ],
    },
    # ── Remaining 26 EU member states (alphabetical) ─────────────────────────
    {
        "key": "Austria",
        "code": "at",
        "aliases": ["austria", "österreich", "vienna", "wien", "graz", "linz"],
    },
    {
        "key": "Belgium",
        "code": "be",
        "aliases": ["belgium", "belgique", "belgië", "brussels", "bruxelles", "brussel", "antwerp", "ghent"],
    },
    {
        "key": "Bulgaria",
        "code": "bg",
        "aliases": ["bulgaria", "sofia", "plovdiv"],
    },
    {
        "key": "Croatia",
        "code": "hr",
        "aliases": ["croatia", "hrvatska", "zagreb", "split"],
    },
    {
        "key": "Cyprus",
        "code": "cy",
        "aliases": ["cyprus", "nicosia", "limassol"],
    },
    {
        "key": "Czech Republic",
        "code": "cz",
        "aliases": ["czech", "czechia", "prague", "praha", "brno"],
    },
    {
        "key": "Denmark",
        "code": "dk",
        "aliases": ["denmark", "danmark", "copenhagen", "københavn", "aarhus"],
    },
    {
        "key": "Estonia",
        "code": "ee",
        "aliases": ["estonia", "eesti", "tallinn", "tartu"],
    },
    {
        "key": "Finland",
        "code": "fi",
        "aliases": ["finland", "suomi", "helsinki", "espoo", "tampere"],
    },
    {
        "key": "France",
        "code": "fr",
        "aliases": ["france", "paris", "lyon", "marseille", "toulouse", "bordeaux", "lille", "nice"],
    },
    {
        "key": "Greece",
        "code": "gr",
        "aliases": ["greece", "ellada", "athens", "athina", "thessaloniki"],
    },
    {
        "key": "Hungary",
        "code": "hu",
        "aliases": ["hungary", "magyarország", "budapest", "debrecen"],
    },
    {
        "key": "Ireland",
        "code": "ie",
        "aliases": ["ireland", "éire", "dublin", "cork", "galway"],
    },
    {
        "key": "Italy",
        "code": "it",
        "aliases": ["italy", "italia", "rome", "roma", "milan", "milano", "turin", "torino", "florence", "firenze", "naples"],
    },
    {
        "key": "Latvia",
        "code": "lv",
        "aliases": ["latvia", "latvija", "riga"],
    },
    {
        "key": "Lithuania",
        "code": "lt",
        "aliases": ["lithuania", "lietuva", "vilnius", "kaunas"],
    },
    {
        "key": "Luxembourg",
        "code": "lu",
        "aliases": ["luxembourg", "luxemburg"],
    },
    {
        "key": "Malta",
        "code": "mt",
        "aliases": ["malta", "valletta"],
    },
    {
        "key": "Netherlands",
        "code": "nl",
        "aliases": ["netherlands", "nederland", "holland", "amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague", "den haag"],
    },
    {
        "key": "Poland",
        "code": "pl",
        "aliases": ["poland", "polska", "warsaw", "warszawa", "krakow", "kraków", "wroclaw", "wrocław", "gdansk"],
    },
    {
        "key": "Portugal",
        "code": "pt",
        "aliases": ["portugal", "lisbon", "lisboa", "porto"],
    },
    {
        "key": "Romania",
        "code": "ro",
        "aliases": ["romania", "românia", "bucharest", "bucurești", "cluj", "timisoara"],
    },
    {
        "key": "Slovakia",
        "code": "sk",
        "aliases": ["slovakia", "slovensko", "bratislava", "košice"],
    },
    {
        "key": "Slovenia",
        "code": "si",
        "aliases": ["slovenia", "slovenija", "ljubljana", "maribor"],
    },
    {
        "key": "Spain",
        "code": "es",
        "aliases": ["spain", "españa", "madrid", "barcelona", "valencia", "seville", "sevilla", "bilbao"],
    },
    {
        "key": "Sweden",
        "code": "se",
        "aliases": ["sweden", "sverige", "stockholm", "gothenburg", "göteborg", "malmö", "malmo"],
    },
]

_BY_KEY = {r["key"]: r for r in REGIONS}
KEYS = [r["key"] for r in REGIONS]


def parse_keys(raw: str | None) -> list[str]:
    """Comma-separated region keys from the frontend → validated, deduped, ordered list."""
    out: list[str] = []
    for part in (raw or "").split(","):
        k = part.strip()
        if k in _BY_KEY and k not in out:
            out.append(k)
    return out


def area_codes(keys: list[str]) -> list[str]:
    """Return job-board area codes for the selected keys.

    EU country entries have no job-board area code (code is an ISO alpha-2 string,
    not a numeric platform code), so this always returns [] for EU regions.
    Kept for API compatibility with the 104 source.
    """
    return []


def linkedin_location(keys: list[str]) -> str:
    """Selected region key → LinkedIn location string; empty selection → '' (global)."""
    if not keys:
        return ""
    r = _BY_KEY.get(keys[0])
    return r["key"] if r else ""


def match_location(location: str | None, keys: list[str]) -> bool:
    """Result-side filter: does job.location fall within any selected region?

    Empty keys → no filter, always True.
    Empty/unknown location → treated as a match (don't drop jobs missing location data).
    LinkedIn results are already location-filtered at the API level; this is a safety
    net for other sources that don't support server-side location filtering.
    """
    if not keys:
        return True
    loc = (location or "").lower()
    if not loc.strip():
        return True
    for k in keys:
        r = _BY_KEY.get(k)
        if r and any(a in loc for a in r["aliases"]):
            return True
    return False
