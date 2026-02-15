#!/usr/bin/env python3
"""
Build docs/person.html — hash-routed SPA for all persons in the Epstein dataset.
Default view: searchable card grid of all 1,416 persons.
Detail view (#slug): full profile with flights, co-passengers, and Leaflet map.
"""

import json
from pathlib import Path
from collections import Counter

from build_utils import (
    load_flights,
    load_persons,
    build_passenger_counts,
    build_name_to_slug,
    build_co_passenger_matrix,
    build_person_flights,
    fuzzy_match_airport,
    CATEGORY_COLORS,
    get_nav_html,
    NAV_CSS,
    AIRPORTS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "person.html"


def main():
    flights = load_flights()
    persons = load_persons()

    name_to_slug = build_name_to_slug(persons)
    passenger_counts = build_passenger_counts(flights)
    co_matrix = build_co_passenger_matrix(flights)
    person_flights = build_person_flights(flights)

    # ── PERSONS array: metadata for all persons ──────────────────────────────
    persons_list = []
    for p in persons:
        persons_list.append({
            "slug": p["slug"],
            "name": p["name"],
            "category": p.get("category", "other"),
            "aliases": p.get("aliases") or [],
            "shortBio": p.get("shortBio", ""),
            "status": p.get("status") or [],
            "flightCount": p.get("flightCount", 0),
            "documentCount": p.get("documentCount", 0),
            "connectionCount": p.get("connectionCount", 0),
            "emailCount": p.get("emailCount", 0),
        })

    # ── FLIGHT_DATA: keyed by slug, only for persons who appear in flights ───
    flight_data = {}
    for p in persons:
        name = p["name"]
        aliases = p.get("aliases") or []

        # Collect flights for this person (by name or any alias)
        all_flights = []
        seen_ids = set()
        for lookup_name in [name] + aliases:
            for f in person_flights.get(lookup_name, []):
                fid = f.get("id", "")
                if fid not in seen_ids:
                    seen_ids.add(fid)
                    all_flights.append(f)

        if not all_flights:
            continue

        # Sort flights by date descending
        all_flights.sort(key=lambda f: f.get("date", ""), reverse=True)

        # Build flight records with resolved coordinates
        flight_records = []
        for f in all_flights:
            oc = fuzzy_match_airport(f.get("origin", ""))
            dc = fuzzy_match_airport(f.get("destination", ""))
            passengers = []
            for pname in f.get("passengerNames", []):
                if pname != name and pname not in aliases:
                    passengers.append(pname)
            flight_records.append({
                "date": f.get("date", ""),
                "origin": f.get("origin", ""),
                "dest": f.get("destination", ""),
                "aircraft": f.get("aircraft", ""),
                "passengers": passengers,
                "oc": oc,
                "dc": dc,
            })

        # Build co-passenger ranking
        co_counts = Counter()
        all_names = [name] + aliases
        for f in all_flights:
            for pname in f.get("passengerNames", []):
                if pname not in all_names:
                    co_counts[pname] += 1
        co_passengers = co_counts.most_common(50)

        flight_data[p["slug"]] = {
            "flights": flight_records,
            "coPassengers": co_passengers,
        }

    persons_json = json.dumps(persons_list, ensure_ascii=False)
    flight_data_json = json.dumps(flight_data, ensure_ascii=False)
    category_colors_json = json.dumps(CATEGORY_COLORS)
    name_to_slug_json = json.dumps(name_to_slug, ensure_ascii=False)

    nav_html = get_nav_html("person")

    html = build_html(
        persons_json,
        flight_data_json,
        category_colors_json,
        name_to_slug_json,
        nav_html,
        len(persons),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT} ({len(persons)} persons, {len(flight_data)} with flight data)")


def build_html(persons_json, flight_data_json, category_colors_json, name_to_slug_json, nav_html, total_persons):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epstein Files — People ({total_persons:,})</title>
    <meta name="description" content="Searchable directory of all {total_persons:,} persons in the Epstein files. Flight records, co-passengers, and connection data.">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; }}

        {NAV_CSS}

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

        /* ── Grid View ────────────────────────────────────────────── */
        #gridView {{ padding: 20px; }}

        .search-bar {{
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .search-bar input {{
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #333;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 14px;
            flex: 1;
            min-width: 200px;
        }}
        .search-bar input::placeholder {{ color: #555; }}
        .search-bar input:focus {{ outline: none; border-color: #cc0000; }}
        .search-count {{
            font-size: 13px;
            color: #888;
            white-space: nowrap;
        }}
        .search-count strong {{ color: #cc0000; }}

        .category-filters {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        .cat-pill {{
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid #333;
            background: #1a1a1a;
            color: #888;
            transition: all 0.15s;
            text-transform: capitalize;
        }}
        .cat-pill:hover {{ border-color: #555; color: #fff; }}
        .cat-pill.active {{ color: #fff; }}

        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 12px;
        }}
        .person-card {{
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 16px;
            cursor: pointer;
            transition: border-color 0.15s, transform 0.15s;
        }}
        .person-card:hover {{
            border-color: #cc0000;
            transform: translateY(-2px);
        }}
        .card-name {{
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
        }}
        .card-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            color: #fff;
            text-transform: capitalize;
        }}
        .card-flights {{
            font-size: 12px;
            color: #888;
            margin-top: 8px;
        }}
        .card-flights strong {{ color: #cc0000; }}

        /* ── Detail View ──────────────────────────────────────────── */
        #detailView {{ display: none; padding: 20px; max-width: 1200px; margin: 0 auto; }}

        .back-btn {{
            display: inline-block;
            color: #cc0000;
            text-decoration: none;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 20px;
            cursor: pointer;
        }}
        .back-btn:hover {{ text-decoration: underline; }}

        .detail-header {{
            margin-bottom: 24px;
        }}
        .detail-name {{
            font-size: 28px;
            font-weight: 900;
            color: #fff;
            margin-bottom: 8px;
        }}
        .detail-badges {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            text-transform: capitalize;
        }}
        .badge-category {{ color: #fff; }}
        .badge-convicted {{ background: #cc0000; color: #fff; }}
        .badge-deceased {{ background: #555; color: #fff; }}
        .badge-indicted {{ background: #e65100; color: #fff; }}
        .detail-bio {{
            font-size: 14px;
            color: #bbb;
            line-height: 1.6;
            margin-bottom: 8px;
        }}
        .detail-aliases {{
            font-size: 13px;
            color: #666;
        }}
        .detail-aliases span {{ color: #999; }}

        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }}
        .stat-box {{
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 14px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 900;
            color: #cc0000;
        }}
        .stat-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 4px;
        }}

        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #222;
        }}

        .no-flights {{
            font-size: 14px;
            color: #666;
            padding: 20px;
            text-align: center;
            background: #111;
            border-radius: 8px;
            border: 1px solid #222;
        }}

        #personMap {{
            width: 100%;
            height: 400px;
            border-radius: 8px;
            border: 1px solid #222;
            margin-bottom: 24px;
            background: #111;
        }}

        .flight-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            font-size: 13px;
        }}
        .flight-table th {{
            background: #111;
            color: #888;
            text-align: left;
            padding: 10px 12px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #333;
            position: sticky;
            top: 0;
        }}
        .flight-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #1a1a1a;
            color: #ccc;
            vertical-align: top;
        }}
        .flight-table tr:hover td {{ background: #111; }}
        .flight-table .route-arrow {{ color: #cc0000; font-weight: 700; }}
        .flight-table a {{
            color: #cc0000;
            text-decoration: none;
        }}
        .flight-table a:hover {{ text-decoration: underline; }}
        .flight-table-wrap {{
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #222;
            border-radius: 8px;
            margin-bottom: 24px;
        }}

        .copax-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 24px;
        }}
        .copax-table th {{
            background: #111;
            color: #888;
            text-align: left;
            padding: 8px 12px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #333;
        }}
        .copax-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #1a1a1a;
            color: #ccc;
        }}
        .copax-table tr:hover td {{ background: #111; }}
        .copax-table a {{ color: #cc0000; text-decoration: none; }}
        .copax-table a:hover {{ text-decoration: underline; }}
        .copax-count {{
            color: #cc0000;
            font-weight: 700;
        }}
        .copax-table-wrap {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #222;
            border-radius: 8px;
            margin-bottom: 24px;
        }}

        @media (max-width: 768px) {{
            .header {{ padding: 10px 12px; }}
            .header h1 {{ font-size: 16px; }}
            #gridView {{ padding: 12px; }}
            #detailView {{ padding: 12px; }}
            .cards-grid {{
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 8px;
            }}
            .stats-bar {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .detail-name {{ font-size: 22px; }}
            .flight-table {{ font-size: 12px; }}
            .flight-table th, .flight-table td {{ padding: 8px 8px; }}
        }}

        @media (max-width: 480px) {{
            .cards-grid {{
                grid-template-columns: 1fr;
            }}
            .stats-bar {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}
            .search-bar {{ flex-direction: column; }}
            .search-bar input {{ min-width: unset; }}
            .category-filters {{ gap: 6px; }}
            .cat-pill {{ font-size: 11px; padding: 4px 10px; }}
        }}
    </style>
</head>
<body>

{nav_html}

<div class="header">
    <h1><span>&#x1F464;</span> People Database</h1>
    <div class="header-stats">
        <span><strong>{total_persons:,}</strong> persons</span>
    </div>
</div>

<!-- ── Grid View (default) ──────────────────────────────────────── -->
<div id="gridView">
    <div class="search-bar">
        <input type="text" id="searchInput" placeholder="Search by name, alias, or category...">
        <span class="search-count" id="searchCount"><strong>{total_persons:,}</strong> shown</span>
    </div>
    <div class="category-filters" id="categoryFilters"></div>
    <div class="cards-grid" id="cardsGrid"></div>
</div>

<!-- ── Detail View (#slug) ──────────────────────────────────────── -->
<div id="detailView">
    <a class="back-btn" id="backBtn">&larr; Back to all people</a>
    <div id="detailContent"></div>
</div>

<script>
const PERSONS = {persons_json};
const FLIGHT_DATA = {flight_data_json};
const CATEGORY_COLORS = {category_colors_json};
const NAME_TO_SLUG = {name_to_slug_json};

let activeCategory = null;
let leafletLoaded = false;
let personMap = null;
let mapLayers = null;

// ── Render cards grid ──────────────────────────────────────────────
function renderCards(filter, catFilter) {{
    const grid = document.getElementById('cardsGrid');
    const countEl = document.getElementById('searchCount');
    const lowerFilter = (filter || '').toLowerCase();

    let shown = 0;
    let html = '';

    PERSONS.forEach(p => {{
        // Category filter
        if (catFilter && p.category !== catFilter) return;

        // Text search filter
        if (lowerFilter) {{
            const haystack = (p.name + ' ' + p.category + ' ' + (p.aliases || []).join(' ')).toLowerCase();
            if (haystack.indexOf(lowerFilter) === -1) return;
        }}

        shown++;
        const catColor = CATEGORY_COLORS[p.category] || '#757575';
        const flightBadge = p.flightCount > 0
            ? '<div class="card-flights"><strong>' + p.flightCount + '</strong> flights</div>'
            : '';

        html += '<div class="person-card" onclick="navigateTo(\\'' + p.slug + '\\')">'
            + '<div class="card-name">' + escHtml(p.name) + '</div>'
            + '<span class="card-badge" style="background:' + catColor + '">' + escHtml(p.category) + '</span>'
            + flightBadge
            + '</div>';
    }});

    grid.innerHTML = html;
    countEl.innerHTML = '<strong>' + shown.toLocaleString() + '</strong> shown';
}}

// ── Render category filter pills ───────────────────────────────────
function renderCategoryFilters() {{
    const container = document.getElementById('categoryFilters');
    const counts = {{}};
    PERSONS.forEach(p => {{
        counts[p.category] = (counts[p.category] || 0) + 1;
    }});

    let html = '<span class="cat-pill active" data-cat="" style="border-color:#cc0000;color:#fff;">All</span>';
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    sorted.forEach(([cat, count]) => {{
        const color = CATEGORY_COLORS[cat] || '#757575';
        html += '<span class="cat-pill" data-cat="' + cat + '">'
            + cat + ' (' + count + ')</span>';
    }});
    container.innerHTML = html;

    container.querySelectorAll('.cat-pill').forEach(pill => {{
        pill.addEventListener('click', function() {{
            container.querySelectorAll('.cat-pill').forEach(p => {{
                p.classList.remove('active');
                p.style.borderColor = '#333';
                p.style.color = '#888';
            }});
            this.classList.add('active');
            const cat = this.dataset.cat;
            const color = cat ? (CATEGORY_COLORS[cat] || '#757575') : '#cc0000';
            this.style.borderColor = color;
            this.style.color = '#fff';
            activeCategory = cat || null;
            renderCards(document.getElementById('searchInput').value, activeCategory);
        }});
    }});
}}

// ── Detail view ────────────────────────────────────────────────────
function showDetail(slug) {{
    const person = PERSONS.find(p => p.slug === slug);
    if (!person) {{
        showGrid();
        return;
    }}

    document.getElementById('gridView').style.display = 'none';
    document.getElementById('detailView').style.display = 'block';

    const fd = FLIGHT_DATA[slug];
    let html = '';

    // Header
    html += '<div class="detail-header">';
    html += '<div class="detail-name">' + escHtml(person.name) + '</div>';
    html += '<div class="detail-badges">';
    const catColor = CATEGORY_COLORS[person.category] || '#757575';
    html += '<span class="badge badge-category" style="background:' + catColor + '">' + escHtml(person.category) + '</span>';
    if (person.status && person.status.length > 0) {{
        person.status.forEach(s => {{
            html += '<span class="badge badge-' + s + '">' + escHtml(s) + '</span>';
        }});
    }}
    html += '</div>';
    if (person.shortBio) {{
        html += '<div class="detail-bio">' + escHtml(person.shortBio) + '</div>';
    }}
    if (person.aliases && person.aliases.length > 0) {{
        html += '<div class="detail-aliases">Also known as: <span>' + person.aliases.map(a => escHtml(a)).join(', ') + '</span></div>';
    }}
    html += '</div>';

    // Stats bar
    html += '<div class="stats-bar">';
    html += statBox(person.flightCount, 'Flights');
    html += statBox(person.documentCount, 'Documents');
    html += statBox(person.connectionCount, 'Connections');
    html += statBox(person.emailCount, 'Emails');
    html += '</div>';

    if (fd && fd.flights && fd.flights.length > 0) {{
        // Map
        html += '<div class="section-title">Flight Routes</div>';
        html += '<div id="personMap"></div>';

        // Flight table
        html += '<div class="section-title">Flight Records (' + fd.flights.length + ')</div>';
        html += '<div class="flight-table-wrap">';
        html += '<table class="flight-table">';
        html += '<thead><tr><th>Date</th><th>Route</th><th>Aircraft</th><th>Co-Passengers</th></tr></thead>';
        html += '<tbody>';
        fd.flights.forEach(f => {{
            const paxLinks = f.passengers.map(name => {{
                const pSlug = NAME_TO_SLUG[name];
                if (pSlug) {{
                    return '<a href="person.html#' + pSlug + '">' + escHtml(name) + '</a>';
                }}
                return escHtml(name);
            }}).join(', ') || '<em style="color:#555">None listed</em>';

            html += '<tr>'
                + '<td style="white-space:nowrap">' + escHtml(f.date) + '</td>'
                + '<td>' + escHtml(f.origin) + ' <span class="route-arrow">&rarr;</span> ' + escHtml(f.dest) + '</td>'
                + '<td>' + escHtml(f.aircraft) + '</td>'
                + '<td>' + paxLinks + '</td>'
                + '</tr>';
        }});
        html += '</tbody></table></div>';

        // Co-passenger ranking
        if (fd.coPassengers && fd.coPassengers.length > 0) {{
            html += '<div class="section-title">Most Frequent Co-Passengers</div>';
            html += '<div class="copax-table-wrap">';
            html += '<table class="copax-table">';
            html += '<thead><tr><th>#</th><th>Name</th><th>Shared Flights</th></tr></thead>';
            html += '<tbody>';
            fd.coPassengers.forEach(([name, count], i) => {{
                const pSlug = NAME_TO_SLUG[name];
                const nameHtml = pSlug
                    ? '<a href="person.html#' + pSlug + '">' + escHtml(name) + '</a>'
                    : escHtml(name);
                html += '<tr><td>' + (i + 1) + '</td><td>' + nameHtml + '</td><td class="copax-count">' + count + '</td></tr>';
            }});
            html += '</tbody></table></div>';
        }}
    }} else {{
        html += '<div class="no-flights">No flight records found for this person.</div>';
    }}

    document.getElementById('detailContent').innerHTML = html;

    // Initialize map if person has flights
    if (fd && fd.flights && fd.flights.length > 0) {{
        loadLeaflet(() => {{
            initPersonMap(fd.flights);
        }});
    }}

    // Scroll to top
    window.scrollTo(0, 0);

    // Update page title
    document.title = person.name + ' — Epstein Files';
}}

function statBox(value, label) {{
    return '<div class="stat-box"><div class="stat-value">' + (value || 0).toLocaleString() + '</div><div class="stat-label">' + label + '</div></div>';
}}

function showGrid() {{
    document.getElementById('gridView').style.display = 'block';
    document.getElementById('detailView').style.display = 'none';
    document.title = 'Epstein Files \u2014 People ({total_persons:,})';

    // Destroy map if it exists
    if (personMap) {{
        personMap.remove();
        personMap = null;
    }}
}}

// ── Leaflet lazy loader ────────────────────────────────────────────
function loadLeaflet(callback) {{
    if (leafletLoaded) {{
        callback();
        return;
    }}

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.onload = function() {{
        leafletLoaded = true;
        callback();
    }};
    document.head.appendChild(script);
}}

function initPersonMap(flights) {{
    // Destroy previous map instance if any
    if (personMap) {{
        personMap.remove();
        personMap = null;
    }}

    const mapEl = document.getElementById('personMap');
    if (!mapEl) return;

    personMap = L.map('personMap', {{
        center: [28, -60],
        zoom: 3,
        zoomControl: true,
        preferCanvas: true
    }});

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png', {{
        attribution: '&copy; OpenStreetMap, &copy; CARTO',
        maxZoom: 18
    }}).addTo(personMap);

    const bounds = [];

    flights.forEach(f => {{
        if (!f.oc || !f.dc) return;

        // Flight line
        L.polyline([f.oc, f.dc], {{
            color: '#cc0000',
            weight: 2,
            opacity: 0.6
        }}).addTo(personMap);

        // Origin marker
        L.circleMarker(f.oc, {{
            radius: 5,
            color: '#cc0000',
            fillColor: '#ff4444',
            fillOpacity: 0.8,
            weight: 1
        }}).bindTooltip(f.origin, {{ direction: 'top', offset: [0, -4] }}).addTo(personMap);

        // Destination marker
        L.circleMarker(f.dc, {{
            radius: 5,
            color: '#cc0000',
            fillColor: '#ff4444',
            fillOpacity: 0.8,
            weight: 1
        }}).bindTooltip(f.dest, {{ direction: 'top', offset: [0, -4] }}).addTo(personMap);

        bounds.push(f.oc);
        bounds.push(f.dc);
    }});

    if (bounds.length > 0) {{
        personMap.fitBounds(bounds, {{ padding: [30, 30] }});
    }}
}}

// ── Navigation helpers ─────────────────────────────────────────────
function navigateTo(slug) {{
    window.location.hash = slug;
}}

function handleHash() {{
    const hash = window.location.hash.replace('#', '');
    if (hash) {{
        showDetail(hash);
    }} else {{
        showGrid();
    }}
}}

// ── Utility ────────────────────────────────────────────────────────
function escHtml(str) {{
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}}

// ── Init ───────────────────────────────────────────────────────────
document.getElementById('backBtn').addEventListener('click', function(e) {{
    e.preventDefault();
    window.location.hash = '';
}});

document.getElementById('searchInput').addEventListener('input', function() {{
    renderCards(this.value, activeCategory);
}});

renderCategoryFilters();
renderCards('', null);
handleHash();
window.addEventListener('hashchange', handleHash);
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
