#!/usr/bin/env python3
"""
Shared utilities for Epstein page build scripts.
Common data loaders, airport lookups, co-passenger analysis, and shared HTML/CSS.
"""

import json
import re
from pathlib import Path
from collections import Counter
from itertools import combinations

REPO_ROOT = Path(__file__).resolve().parent.parent
FLIGHTS_JSON = REPO_ROOT / "data" / "flights.json"
PERSONS_JSON = REPO_ROOT / "data" / "persons.json"

# ── Airport name → [lat, lon] lookup ──────────────────────────────────────────
AIRPORTS = {
    "Teterboro Airport, NJ": [40.8501, -74.0608],
    "Palm Beach International, FL": [26.6832, -80.0956],
    "TIST Airport": [18.3373, -64.9733],
    "Cyril E. King Airport, USVI": [18.3373, -64.9733],
    "Little St. James Island, USVI": [18.3000, -64.8254],
    "Laurence G. Hanscom Field, Bedford, MA": [42.4700, -71.2890],
    "EWR Airport": [40.6895, -74.1745],
    "Le Bourget, Paris, France": [48.9693, 2.4414],
    "Paris Le Bourget, France": [48.9693, 2.4414],
    "LFBG Airport": [45.6583, -0.3175],
    "Albuquerque International Sunport, NM": [35.0402, -106.6092],
    "ISP Airport": [40.7952, -73.1002],
    "Santa Fe Municipal Airport, NM": [35.6170, -106.0889],
    "John F. Kennedy International, NY": [40.6413, -73.7781],
    "BAF Airport": [42.1580, -72.7157],
    "MCN Airport": [32.6927, -83.6490],
    "GYH Airport": [34.7584, -82.3764],
    "RYY Airport": [34.0132, -84.5971],
    "TQPF Airport": [18.4450, -64.5433],
    "Columbus, OH": [39.9980, -82.8919],
    "Columbus Airport, OH": [39.9980, -82.8919],
    "White Plains Airport, NY": [41.0670, -73.7076],
    "HPN Airport": [41.0670, -73.7076],
    "Dulles International, VA": [38.9531, -77.4565],
    "IAD Airport": [38.9531, -77.4565],
    "Miami International, FL": [25.7959, -80.2870],
    "MIA Airport": [25.7959, -80.2870],
    "Opa-Locka Airport, FL": [25.9070, -80.2784],
    "OPF Airport": [25.9070, -80.2784],
    "St. Thomas, USVI": [18.3373, -64.9733],
    "FLL Airport": [26.0726, -80.1527],
    "Fort Lauderdale, FL": [26.0726, -80.1527],
    "LGA Airport": [40.7772, -73.8726],
    "LaGuardia Airport, NY": [40.7772, -73.8726],
    "London Luton, UK": [51.8747, -0.3683],
    "Luton Airport, UK": [51.8747, -0.3683],
    "London Stansted, UK": [51.8860, 0.2389],
    "SFB Airport": [28.7776, -81.2372],
    "Orlando Sanford, FL": [28.7776, -81.2372],
    "BQN Airport": [18.4949, -67.1294],
    "Aguadilla, PR": [18.4949, -67.1294],
    "Japan": [35.5494, 139.7798],
    "NRT Airport": [35.7647, 140.3864],
    "Narita, Japan": [35.7647, 140.3864],
    "Azores, Portugal": [37.7412, -25.6756],
    "Shannon Airport, Ireland": [52.7020, -8.9248],
    "SNN Airport": [52.7020, -8.9248],
    "BDA Airport": [32.3640, -64.6787],
    "Bermuda": [32.3640, -64.6787],
    "SAF Airport": [35.6170, -106.0889],
    "ABQ Airport": [35.0402, -106.6092],
    "DCA Airport": [38.8512, -77.0402],
    "Reagan National, DC": [38.8512, -77.0402],
    "Ronald Reagan Airport, DC": [38.8512, -77.0402],
    "Bangor International, ME": [44.8074, -68.8281],
    "BGR Airport": [44.8074, -68.8281],
    "TEB Airport": [40.8501, -74.0608],
    "PBI Airport": [26.6832, -80.0956],
    "JFK Airport": [40.6413, -73.7781],
    "SJU Airport": [18.4394, -66.0018],
    "San Juan, PR": [18.4394, -66.0018],
    "Farmingdale Airport, NY": [40.7288, -73.4134],
    "FRG Airport": [40.7288, -73.4134],
    "Republic Airport, NY": [40.7288, -73.4134],
    "MVY Airport": [41.3933, -70.6144],
    "Martha's Vineyard, MA": [41.3933, -70.6144],
    "ACK Airport": [41.2531, -70.0602],
    "Nantucket, MA": [41.2531, -70.0602],
    "Morristown Airport, NJ": [40.7994, -74.4149],
    "MMU Airport": [40.7994, -74.4149],
    "Gary, IN": [41.6163, -87.4128],
    "GYY Airport": [41.6163, -87.4128],
    "Chicago Midway, IL": [41.7868, -87.7522],
    "MDW Airport": [41.7868, -87.7522],
    "Marrakech, Morocco": [31.6068, -8.0363],
    "RAK Airport": [31.6068, -8.0363],
    "Rabat, Morocco": [34.0531, -6.7515],
    "Nice, France": [43.6584, 7.2159],
    "NCE Airport": [43.6584, 7.2159],
    "ACY Airport": [39.4576, -74.5772],
    "APC Airport": [38.2132, -122.2806],
    "ASE Airport": [39.2232, -106.8688],
    "Accra, Ghana": [5.6052, -0.1668],
    "BCT Airport": [26.3785, -80.1077],
    "BFI Airport": [47.5300, -122.3020],
    "BQK Airport": [31.2588, -81.4666],
    "BUR Airport": [34.2007, -118.3585],
    "CNM Airport": [32.3375, -104.2633],
    "CNO Airport": [33.9747, -117.6368],
    "CNW Airport": [31.6378, -97.0742],
    "CPS Airport": [38.5707, -90.1562],
    "CRW Airport": [38.3731, -81.5932],
    "CYJT Airport": [48.5442, -58.5500],
    "CYQX Airport": [48.9369, -54.5681],
    "CYVR Airport": [49.1947, -123.1839],
    "CYXU Airport": [43.0336, -81.1511],
    "CYYR Airport": [53.3192, -60.4258],
    "Daytona Beach International, FL": [29.1799, -81.0581],
    "DIAP Airport": [5.2614, -3.9263],
    "EDDM Airport": [48.3538, 11.7861],
    "EGGP Airport": [53.3336, -2.8497],
    "EGHL Airport": [51.1872, -1.0335],
    "EGPH Airport": [55.9500, -3.3725],
    "EINN Airport": [52.7020, -8.9248],
    "ESSA Airport": [59.6519, 17.9186],
    "FOK Airport": [40.8437, -72.6318],
    "Fort Lauderdale-Hollywood International, FL": [26.0726, -80.1527],
    "GEG Airport": [47.6199, -117.5338],
    "GMME Airport": [34.0514, -6.7515],
    "GMMX Airport": [31.6068, -8.0363],
    "GOOY Airport": [14.7397, -17.4902],
    "GUC Airport": [38.5339, -106.9332],
    "GVAC Airport": [16.7414, -22.9494],
    "Hanscom Field, MA": [42.4700, -71.2890],
    "ILG Airport": [39.6787, -75.6065],
    "IND Airport": [39.7173, -86.2944],
    "ISM Airport": [28.2898, -81.4371],
    "JFK International, NY": [40.6413, -73.7781],
    "Johannesburg, South Africa": [-26.1392, 28.2461],
    "John Glenn Columbus International, OH": [39.9980, -82.8919],
    "LAS Airport": [36.0840, -115.1537],
    "LAX International, CA": [33.9425, -118.4081],
    "LAX Airport": [33.9425, -118.4081],
    "LCQ Airport": [30.1820, -82.5769],
    "LEIB Airport": [38.8729, 1.3731],
    "LFBE Airport": [44.8253, 0.5186],
    "LFMN Airport": [43.6584, 7.2159],
    "LFTH Airport": [43.0973, 6.1460],
    "LGB Airport": [33.8177, -118.1516],
    "LGIR Airport": [35.3397, 25.1803],
    "LLBG Airport": [32.0114, 34.8867],
    "LOWW Airport": [48.1103, 16.5697],
    "LPAZ Airport": [36.9714, -25.1706],
    "LSGG Airport": [46.2381, 6.1089],
    "LSZH Airport": [47.4647, 8.5492],
    "LZIB Airport": [48.1702, 17.2127],
    "LZTT Airport": [49.0736, 20.2411],
    "Lagos, Nigeria": [6.5774, 3.3214],
    "London Luton Airport, UK": [51.8747, -0.3683],
    "London Stansted Airport, UK": [51.8860, 0.2389],
    "MBPV Airport": [21.7736, -72.2659],
    "MDPC Airport": [18.5674, -68.3634],
    "MDPP Airport": [19.7579, -70.5700],
    "MHT Airport": [42.9326, -71.4357],
    "MIV Airport": [39.3678, -75.0722],
    "MMSD Airport": [23.1518, -109.7215],
    "MYNN Airport": [25.0390, -77.4662],
    "Maputo, Mozambique": [-25.9208, 32.5726],
    "Martha's Vineyard Airport, MA": [41.3933, -70.6144],
    "Montreal-Trudeau International, Canada": [45.4706, -73.7408],
    "NUQ Airport": [37.4161, -122.0490],
    "OAK Airport": [37.7213, -122.2208],
    "ONT Airport": [34.0560, -117.6012],
    "PDK Airport": [33.8756, -84.3020],
    "PHL Airport": [39.8721, -75.2411],
    "PTK Airport": [42.6655, -83.4185],
    "PWM Airport": [43.6462, -70.3093],
    "Palm Beach Estate, FL": [26.7056, -80.0364],
    "Phoenix Sky Harbor International, AZ": [33.4373, -112.0078],
    "PHX Airport": [33.4373, -112.0078],
    "RBA Airport": [34.0514, -6.7515],
    "RIC Airport": [37.5052, -77.3197],
    "RSW Airport": [26.5362, -81.7553],
    "RUH Airport": [24.9576, 46.6988],
    "RWI Airport": [35.8563, -77.8919],
    "Rabat-Salé Airport, Morocco": [34.0514, -6.7515],
    "Ronald Reagan Washington National, DC": [38.8512, -77.0402],
    "SAN Airport": [32.7338, -117.1933],
    "SBGR Airport": [-23.4356, -46.4731],
    "SDL Airport": [33.6229, -111.9105],
    "SEF Airport": [27.4564, -81.3425],
    "SFO Airport": [37.6213, -122.3790],
    "SJC Airport": [37.3626, -121.9290],
    "SKBO Airport": [4.7016, -74.1469],
    "SLC Airport": [40.7884, -111.9778],
    "SSI Airport": [31.1518, -81.3913],
    "SWF Airport": [41.5041, -74.1048],
    "Savannah/Hilton Head International, GA": [32.1276, -81.2021],
    "TJSJ Airport": [18.4394, -66.0018],
    "TPA Airport": [27.9755, -82.5332],
    "TUL Airport": [36.1984, -95.8881],
    "TUS Airport": [32.1161, -110.9410],
    "VNY Airport": [34.2098, -118.4900],
    "VQQ Airport": [30.2187, -81.8767],
    "Washington Dulles International, VA": [38.9531, -77.4565],
    "Westchester County Airport, NY": [41.0670, -73.7076],
    "Bangor International Airport, ME": [44.8074, -68.8281],
    "Boston Logan International, MA": [42.3656, -71.0096],
}


def fuzzy_match_airport(name):
    """Try to match airport name to coordinates."""
    if not name:
        return None
    if name in AIRPORTS:
        return AIRPORTS[name]
    for key, coords in AIRPORTS.items():
        if key.lower() == name.lower():
            return coords
    name_lower = name.lower()
    for key, coords in AIRPORTS.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return coords
    code = name.replace(" Airport", "").strip()
    if code in AIRPORTS:
        return AIRPORTS[code]
    return None


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_flights():
    return json.load(open(FLIGHTS_JSON, encoding="utf-8"))


def load_persons():
    return json.load(open(PERSONS_JSON, encoding="utf-8"))


# ── Analysis helpers ──────────────────────────────────────────────────────────

def build_passenger_counts(flights):
    """Return Counter of passenger_name → total flight count."""
    counts = Counter()
    for f in flights:
        for name in f.get("passengerNames", []):
            counts[name] += 1
    return counts


def build_name_to_slug(persons):
    """Map person name (and aliases) → slug for cross-linking."""
    mapping = {}
    for p in persons:
        mapping[p["name"]] = p["slug"]
        for alias in (p.get("aliases") or []):
            mapping[alias] = p["slug"]
    return mapping


def build_name_to_person(persons):
    """Map person name (and aliases) → full person dict."""
    mapping = {}
    for p in persons:
        mapping[p["name"]] = p
        for alias in (p.get("aliases") or []):
            mapping[alias] = p
    return mapping


def build_co_passenger_matrix(flights):
    """Return Counter of (nameA, nameB) tuple (sorted) → shared flight count."""
    matrix = Counter()
    for f in flights:
        names = sorted(set(f.get("passengerNames", [])))
        for a, b in combinations(names, 2):
            matrix[(a, b)] += 1
    return matrix


def build_person_flights(flights):
    """Return dict of passenger_name → list of flight dicts."""
    pf = {}
    for f in flights:
        for name in f.get("passengerNames", []):
            pf.setdefault(name, []).append(f)
    return pf


# ── Category colors ───────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    "associate": "#cc0000",
    "socialite": "#e040fb",
    "politician": "#2196f3",
    "business": "#4caf50",
    "celebrity": "#ffc107",
    "legal": "#ff9800",
    "royalty": "#ffd700",
    "academic": "#00bcd4",
    "military-intelligence": "#1a237e",
    "other": "#757575",
}


# ── Property definitions ─────────────────────────────────────────────────────

PROPERTIES = {
    "Little St. James Island": {
        "coords": [18.3000, -64.8254],
        "desc": "Epstein's 70-acre private island in the US Virgin Islands, known as 'Pedophile Island'. Purchased in 1998.",
        "match_terms": ["st. james", "tist", "cyril e. king", "st. thomas", "tqpf", "usvi"],
    },
    "Palm Beach Estate": {
        "coords": [26.7056, -80.0364],
        "desc": "358 El Brillo Way — Epstein's 14,000 sq ft Palm Beach mansion where much of the documented abuse occurred.",
        "match_terms": ["palm beach", "pbi"],
    },
    "NYC Townhouse": {
        "coords": [40.7580, -73.9655],
        "desc": "9 East 71st Street, Manhattan — largest private residence in NYC. Accessed via Teterboro Airport, NJ.",
        "match_terms": ["teterboro", "teb airport"],
    },
    "Paris Apartment": {
        "coords": [48.8708, 2.2862],
        "desc": "Avenue Foch apartment in Paris 16th arrondissement — Epstein's European base of operations.",
        "match_terms": ["le bourget", "paris le bourget"],
    },
    "Zorro Ranch": {
        "coords": [35.1700, -105.6700],
        "desc": "7,500-acre ranch near Stanley, New Mexico. Accessed via Santa Fe or Albuquerque airports.",
        "match_terms": ["santa fe", "saf airport", "albuquerque", "abq"],
    },
}


def match_airport_to_property(airport_name):
    """Return property name if airport matches a known Epstein property, else None."""
    if not airport_name:
        return None
    lower = airport_name.lower()
    for prop_name, prop in PROPERTIES.items():
        for term in prop["match_terms"]:
            if term in lower:
                return prop_name
    return None


# ── Shared navigation HTML/CSS ────────────────────────────────────────────────

def get_nav_html(active_page):
    """Return shared nav bar HTML string.
    active_page: flights | network | person | properties | routes
    """
    links = [
        ("flights.html", "Flights", "flights"),
        ("network.html", "Network", "network"),
        ("person.html", "People", "person"),
        ("properties.html", "Properties", "properties"),
        ("routes.html", "Routes", "routes"),
    ]
    items = []
    for href, label, key in links:
        cls = "nav-link active" if key == active_page else "nav-link"
        items.append(f'<a href="{href}" class="{cls}">{label}</a>')
    items.append('<a href="index.html" class="nav-link nav-back">&larr; Index</a>')
    return '<nav class="nav-bar">' + ''.join(items) + '</nav>'


NAV_CSS = """
.nav-bar {
    background: #111;
    padding: 0 20px;
    display: flex;
    gap: 0;
    border-bottom: 1px solid #222;
    overflow-x: auto;
}
.nav-link {
    color: #888;
    text-decoration: none;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
    transition: color 0.15s;
}
.nav-link:hover { color: #fff; text-decoration: none; }
.nav-link.active { color: #cc0000; border-bottom-color: #cc0000; }
.nav-back { margin-left: auto; color: #cc0000; }
"""
