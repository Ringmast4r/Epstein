#!/usr/bin/env python3
"""
Build docs/flights.html — interactive Leaflet.js map of all Epstein flights.
Reads data/flights.json and embeds it into a self-contained HTML file.
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter

# Add tools/ to path for build_utils import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_utils import get_nav_html, NAV_CSS

REPO_ROOT = Path(__file__).resolve().parent.parent
FLIGHTS_JSON = REPO_ROOT / "data" / "flights.json"
OUTPUT = REPO_ROOT / "docs" / "flights.html"

# Airport name → [lat, lon] lookup
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
    # Additional airports from flight data
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
    "FLL Airport": [26.0726, -80.1527],
}


def fuzzy_match_airport(name):
    """Try to match airport name to coordinates."""
    if not name:
        return None
    # Exact match
    if name in AIRPORTS:
        return AIRPORTS[name]
    # Case-insensitive
    for key, coords in AIRPORTS.items():
        if key.lower() == name.lower():
            return coords
    # Partial match
    name_lower = name.lower()
    for key, coords in AIRPORTS.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return coords
    # ICAO/IATA code extraction
    code = name.replace(" Airport", "").strip()
    if code in AIRPORTS:
        return AIRPORTS[code]
    return None


def main():
    flights = json.load(open(FLIGHTS_JSON, encoding="utf-8"))

    # Build passenger stats
    passenger_counts = Counter()
    for f in flights:
        for name in f.get("passengerNames", []):
            passenger_counts[name] += 1

    # Build airport stats and resolve coordinates
    airport_set = set()
    for f in flights:
        if f.get("origin"):
            airport_set.add(f["origin"])
        if f.get("destination"):
            airport_set.add(f["destination"])

    resolved = 0
    unresolved = []
    for ap in airport_set:
        if fuzzy_match_airport(ap):
            resolved += 1
        else:
            unresolved.append(ap)

    print(f"Airports: {resolved} resolved, {len(unresolved)} unresolved")
    if unresolved:
        print(f"  Unresolved: {unresolved[:20]}")

    # Prepare flight data for JS (only flights with resolvable airports)
    js_flights = []
    for f in flights:
        origin_coords = fuzzy_match_airport(f.get("origin", ""))
        dest_coords = fuzzy_match_airport(f.get("destination", ""))
        js_flights.append({
            "id": f.get("id", ""),
            "date": f.get("date", ""),
            "origin": f.get("origin", ""),
            "destination": f.get("destination", ""),
            "aircraft": f.get("aircraft", ""),
            "passengers": f.get("passengerNames", []),
            "oc": origin_coords,
            "dc": dest_coords,
        })

    # Prepare airport markers with per-airport stats
    airport_markers = {}
    airport_stats = {}  # name -> {flights, passengers: {name: count}, dates: [min, max]}
    for ap in airport_set:
        coords = fuzzy_match_airport(ap)
        if coords:
            airport_markers[ap] = coords
            airport_stats[ap] = {"flights": 0, "passengers": Counter(), "dates": []}

    for f in flights:
        origin = f.get("origin", "")
        dest = f.get("destination", "")
        date = f.get("date", "")
        pax = f.get("passengerNames", [])
        for ap in [origin, dest]:
            if ap in airport_stats:
                airport_stats[ap]["flights"] += 1
                if date:
                    airport_stats[ap]["dates"].append(date)
                for p in pax:
                    airport_stats[ap]["passengers"][p] += 1

    # Convert to JSON-serializable format (top 20 passengers per airport)
    airport_stats_js = {}
    for ap, stats in airport_stats.items():
        top = stats["passengers"].most_common(20)
        dates = sorted(stats["dates"]) if stats["dates"] else []
        airport_stats_js[ap] = {
            "flights": stats["flights"],
            "top": top,
            "dateRange": [dates[0], dates[-1]] if dates else [],
        }

    # Passenger list sorted by flight count
    top_passengers = passenger_counts.most_common(50)

    flights_json = json.dumps(js_flights)
    airports_json = json.dumps(airport_markers)
    passengers_json = json.dumps(top_passengers)
    airport_stats_json = json.dumps(airport_stats_js)

    nav_html = get_nav_html("flights")
    nav_css = NAV_CSS
    html = build_html(flights_json, airports_json, passengers_json, airport_stats_json, len(flights), len(passenger_counts), nav_html, nav_css)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT} ({len(flights)} flights)")


def build_html(flights_json, airports_json, passengers_json, airport_stats_json, total_flights, total_passengers, nav_html, nav_css):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epstein Flight Map — 1,708 Flights</title>
    <meta name="description" content="Interactive map of every known Epstein flight (1997-2019). 1,708 flights. Filter by passenger, date, airport.">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; }}

        .header {{
            background: #0a0a0a;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 3px solid #cc0000;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 900;
            color: #fff;
        }}
        .header h1 span {{ color: #cc0000; }}
        .header-stats {{
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #999;
        }}
        .header-stats strong {{ color: #fff; }}
        .header-back {{
            color: #cc0000;
            text-decoration: none;
            font-size: 13px;
            font-weight: 700;
        }}

        .controls {{
            background: #111;
            padding: 12px 20px;
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
            border-bottom: 1px solid #222;
        }}
        .controls label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .controls select, .controls input {{
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #333;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 13px;
        }}
        .controls select {{ min-width: 180px; }}
        .controls input[type="date"] {{ width: 140px; }}
        .controls button {{
            background: #cc0000;
            color: #fff;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
        }}
        .controls button:hover {{ background: #ff0000; }}
        .filter-count {{
            font-size: 13px;
            color: #cc0000;
            font-weight: 700;
            margin-left: auto;
        }}

        .main {{
            display: flex;
            height: calc(100vh - 145px);
        }}

        #map {{
            flex: 1;
            background: #0a0a0a;
        }}

        .sidebar {{
            width: 320px;
            background: #111;
            overflow-y: auto;
            border-left: 1px solid #222;
        }}
        .sidebar-title {{
            padding: 14px 16px;
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            background: #0a0a0a;
            border-bottom: 1px solid #222;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .passenger-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            border-bottom: 1px solid #1a1a1a;
            cursor: pointer;
            font-size: 13px;
        }}
        .passenger-item:hover {{ background: #1a1a1a; }}
        .passenger-item.active {{ background: #1a0000; border-left: 3px solid #cc0000; }}
        .passenger-name {{ color: #fff; }}
        .passenger-count {{
            color: #cc0000;
            font-weight: 700;
            font-size: 12px;
        }}

        .flight-popup {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .flight-popup strong {{ color: #cc0000; }}
        .flight-popup .fp-date {{ font-weight: 700; margin-bottom: 4px; }}
        .flight-popup .fp-route {{ margin-bottom: 4px; }}
        .flight-popup .fp-passengers {{ font-size: 12px; color: #555; }}
        .flight-popup .fp-aircraft {{ font-size: 11px; color: #888; margin-top: 4px; }}

        .airport-popup {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .airport-popup .ap-name {{
            font-size: 15px;
            font-weight: 900;
            color: #cc0000;
            margin-bottom: 4px;
        }}
        .airport-popup .ap-stats {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid #ddd;
        }}
        .airport-popup .ap-pax-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 6px;
            font-weight: 700;
        }}
        .airport-popup .ap-pax-list {{
            max-height: 250px;
            overflow-y: auto;
        }}
        .airport-popup .ap-pax-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            padding: 3px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .airport-popup .ap-pax-count {{
            color: #cc0000;
            font-weight: 700;
            margin-left: 12px;
        }}

        {nav_css}

        @media (max-width: 768px) {{
            .sidebar {{ display: none; }}
            .main {{ height: calc(100vh - 170px); }}
            .header {{ padding: 10px 12px; }}
            .header h1 {{ font-size: 16px; }}
            .controls {{ padding: 8px 12px; gap: 8px; }}
            .controls select, .controls input {{ font-size: 12px; min-width: 120px; }}
        }}
    </style>
</head>
<body>

<div class="header">
    <h1><span>&#x2708;</span> Epstein Flight Map</h1>
    <div class="header-stats">
        <span><strong>{total_flights:,}</strong> flights</span>
        <span><strong>{total_passengers}</strong> passengers</span>
        <span><strong>1997 &ndash; 2019</strong></span>
    </div>
    <a class="header-back" href="index.html">&larr; Back to Index</a>
</div>

{nav_html}

<div class="controls">
    <label>Passenger</label>
    <select id="passengerFilter">
        <option value="">All passengers</option>
    </select>
    <label>From</label>
    <input type="date" id="dateFrom" value="1997-01-01">
    <label>To</label>
    <input type="date" id="dateTo" value="2019-12-31">
    <button onclick="applyFilters()">Filter</button>
    <button onclick="resetFilters()" style="background:#333;">Reset</button>
    <span class="filter-count" id="filterCount">{total_flights:,} flights shown</span>
</div>

<div class="main">
    <div id="map"></div>
    <div class="sidebar">
        <div class="sidebar-title">Top Passengers (by flight count)</div>
        <div id="passengerList"></div>
    </div>
</div>

<script>
const FLIGHTS = {flights_json};
const AIRPORTS = {airports_json};
const TOP_PASSENGERS = {passengers_json};
const AIRPORT_STATS = {airport_stats_json};

// Init map
const map = L.map('map', {{
    center: [28, -60],
    zoom: 4,
    zoomControl: true,
    preferCanvas: true
}});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png', {{
    attribution: '&copy; OpenStreetMap, &copy; CARTO',
    maxZoom: 18
}}).addTo(map);

// Airport markers with clickable popups
const airportMarkers = L.layerGroup().addTo(map);
Object.entries(AIRPORTS).forEach(([name, coords]) => {{
    const stats = AIRPORT_STATS[name];
    const flightCount = stats ? stats.flights : 0;
    const radius = Math.min(4 + Math.sqrt(flightCount) * 0.5, 14);

    const marker = L.circleMarker(coords, {{
        radius: radius,
        color: '#cc0000',
        fillColor: '#ff4444',
        fillOpacity: 0.8,
        weight: 1
    }}).addTo(airportMarkers);

    marker.bindTooltip(name + ' (' + flightCount + ')', {{ direction: 'top', offset: [0, -6] }});

    if (stats) {{
        let popupHtml = '<div class="airport-popup">';
        popupHtml += '<div class="ap-name">' + name + '</div>';
        popupHtml += '<div class="ap-stats">' + stats.flights + ' flights';
        if (stats.dateRange && stats.dateRange.length === 2) {{
            popupHtml += ' &middot; ' + stats.dateRange[0] + ' to ' + stats.dateRange[1];
        }}
        popupHtml += '</div>';
        if (stats.top && stats.top.length > 0) {{
            popupHtml += '<div class="ap-pax-title">Passengers from this airport:</div>';
            popupHtml += '<div class="ap-pax-list">';
            stats.top.forEach(([pName, pCount]) => {{
                popupHtml += '<div class="ap-pax-row"><span>' + pName + '</span><span class="ap-pax-count">' + pCount + '</span></div>';
            }});
            popupHtml += '</div>';
        }}
        popupHtml += '</div>';
        marker.bindPopup(popupHtml, {{ maxWidth: 320, maxHeight: 400 }});
    }}
}});

// Flight lines layer
let flightLines = L.layerGroup().addTo(map);

function drawFlights(flights) {{
    flightLines.clearLayers();
    let count = 0;
    flights.forEach(f => {{
        if (!f.oc || !f.dc) return;
        if (f.oc[0] === f.dc[0] && f.oc[1] === f.dc[1]) return;
        count++;
        const line = L.polyline([f.oc, f.dc], {{
            color: f.passengers.length > 0 ? '#cc0000' : '#444',
            weight: Math.min(1 + f.passengers.length * 0.3, 4),
            opacity: 0.5
        }}).addTo(flightLines);

        const pax = f.passengers.length > 0
            ? f.passengers.join(', ')
            : '<em>No passengers listed</em>';

        line.bindPopup(`
            <div class="flight-popup">
                <div class="fp-date">${{f.date}}</div>
                <div class="fp-route"><strong>${{f.origin}}</strong> &rarr; <strong>${{f.destination}}</strong></div>
                <div class="fp-passengers">${{pax}}</div>
                <div class="fp-aircraft">${{f.aircraft || 'Unknown aircraft'}}</div>
            </div>
        `, {{ maxWidth: 350 }});
    }});
    document.getElementById('filterCount').textContent = count.toLocaleString() + ' flights shown';
}}

// Populate passenger dropdown and sidebar
const select = document.getElementById('passengerFilter');
TOP_PASSENGERS.forEach(([name, count]) => {{
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name + ' (' + count + ')';
    select.appendChild(opt);
}});

const pList = document.getElementById('passengerList');
TOP_PASSENGERS.forEach(([name, count]) => {{
    const div = document.createElement('div');
    div.className = 'passenger-item';
    div.innerHTML = '<span class="passenger-name">' + name + '</span><span class="passenger-count">' + count + ' flights</span>';
    div.onclick = () => {{
        select.value = name;
        applyFilters();
        document.querySelectorAll('.passenger-item').forEach(el => el.classList.remove('active'));
        div.classList.add('active');
    }};
    pList.appendChild(div);
}});

function applyFilters() {{
    const passenger = document.getElementById('passengerFilter').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;

    const filtered = FLIGHTS.filter(f => {{
        if (passenger && !f.passengers.includes(passenger)) return false;
        if (dateFrom && f.date < dateFrom) return false;
        if (dateTo && f.date > dateTo) return false;
        return true;
    }});
    drawFlights(filtered);
}}

function resetFilters() {{
    document.getElementById('passengerFilter').value = '';
    document.getElementById('dateFrom').value = '1997-01-01';
    document.getElementById('dateTo').value = '2019-12-31';
    document.querySelectorAll('.passenger-item').forEach(el => el.classList.remove('active'));
    drawFlights(FLIGHTS);
}}

// Initial draw
drawFlights(FLIGHTS);
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
