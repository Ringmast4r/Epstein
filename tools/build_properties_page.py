#!/usr/bin/env python3
"""
Build docs/properties.html — interactive property pages for all known Epstein properties.
Shows flight connections, visitor timelines, and route maps for each property.
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

from build_utils import (
    load_flights,
    load_persons,
    build_name_to_slug,
    match_airport_to_property,
    fuzzy_match_airport,
    PROPERTIES,
    CATEGORY_COLORS,
    get_nav_html,
    NAV_CSS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "properties.html"


def main():
    flights = load_flights()
    persons = load_persons()
    name_to_slug = build_name_to_slug(persons)

    nav_html = get_nav_html("properties")

    # ── Build per-property data ──────────────────────────────────────────────
    property_data = {}

    for prop_name, prop_info in PROPERTIES.items():
        prop_flights = []          # list of matching flight dicts
        visitors = Counter()       # passenger name → visit count
        dates = []                 # all dates for range calc
        timeline_raw = []          # list of {date, direction, passengers, otherAirport}
        route_counter = Counter()  # other airport name → count
        route_coords = {}          # other airport name → coords

        for f in flights:
            origin = f.get("origin", "")
            dest = f.get("destination", "")
            date = f.get("date", "")
            pax = f.get("passengerNames", [])

            origin_match = match_airport_to_property(origin)
            dest_match = match_airport_to_property(dest)

            matched = False
            direction = ""
            other_airport = ""

            if dest_match == prop_name:
                # Flight arriving at this property
                matched = True
                direction = "arrived"
                other_airport = origin
            elif origin_match == prop_name:
                # Flight departing from this property
                matched = True
                direction = "departed"
                other_airport = dest

            if not matched:
                continue

            prop_flights.append(f)
            if date:
                dates.append(date)

            for name in pax:
                visitors[name] += 1

            # Build passenger list with slugs
            pax_with_slugs = []
            for name in pax:
                slug = name_to_slug.get(name, "")
                pax_with_slugs.append({"name": name, "slug": slug})

            timeline_raw.append({
                "date": date,
                "direction": direction,
                "passengers": pax_with_slugs,
                "otherAirport": other_airport,
            })

            # Track routes to other airports
            if other_airport:
                route_counter[other_airport] += 1
                if other_airport not in route_coords:
                    coords = fuzzy_match_airport(other_airport)
                    if coords:
                        route_coords[other_airport] = coords

        # Sort dates for range
        sorted_dates = sorted(dates) if dates else []
        date_range = [sorted_dates[0], sorted_dates[-1]] if sorted_dates else ["", ""]

        # Top visitors (top 20)
        top_visitors = []
        for name, count in visitors.most_common(20):
            slug = name_to_slug.get(name, "")
            top_visitors.append([name, count, slug])

        # Timeline grouped by year, sorted chronologically
        timeline_raw.sort(key=lambda x: x["date"])
        timeline_by_year = defaultdict(list)
        for entry in timeline_raw:
            year = entry["date"][:4] if entry["date"] else "Unknown"
            timeline_by_year[year].append(entry)
        # Convert to regular dict with sorted keys
        timeline = {yr: timeline_by_year[yr] for yr in sorted(timeline_by_year.keys())}

        # Routes
        routes = []
        for airport, count in route_counter.most_common():
            coords = route_coords.get(airport)
            if coords:
                routes.append({"airport": airport, "coords": coords, "count": count})

        property_data[prop_name] = {
            "coords": prop_info["coords"],
            "desc": prop_info["desc"],
            "flights": len(prop_flights),
            "uniqueVisitors": len(visitors),
            "dateRange": date_range,
            "topVisitors": top_visitors,
            "timeline": timeline,
            "routes": routes,
        }

    property_data_json = json.dumps(property_data)

    html = build_html(nav_html, property_data_json, len(PROPERTIES))
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT} ({len(PROPERTIES)} properties)")


def build_html(nav_html, property_data_json, total_properties):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epstein Properties</title>
    <meta name="description" content="All known Epstein properties with flight connections, visitor timelines, and route maps.">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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

        #overview-map {{
            width: 100%;
            height: 400px;
            border-bottom: 1px solid #222;
        }}

        .content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        .property-section {{
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            margin-bottom: 30px;
            overflow: hidden;
        }}

        .property-header {{
            padding: 20px 24px;
            border-bottom: 1px solid #222;
        }}
        .property-header h2 {{
            font-size: 22px;
            font-weight: 900;
            color: #cc0000;
            margin-bottom: 6px;
        }}
        .property-header .desc {{
            font-size: 14px;
            color: #999;
            line-height: 1.5;
        }}

        .stats-row {{
            display: flex;
            gap: 24px;
            padding: 16px 24px;
            border-bottom: 1px solid #222;
            flex-wrap: wrap;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 900;
            color: #cc0000;
        }}
        .stat-label {{
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 2px;
        }}

        .property-body {{
            display: flex;
            gap: 0;
        }}
        .property-left {{
            flex: 1;
            min-width: 0;
            border-right: 1px solid #222;
        }}
        .property-right {{
            width: 420px;
            flex-shrink: 0;
        }}

        .section-title {{
            font-size: 12px;
            font-weight: 700;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 14px 24px;
            border-bottom: 1px solid #222;
            background: #0a0a0a;
        }}

        /* Top Visitors Table */
        .visitors-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .visitors-table th {{
            text-align: left;
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 16px;
            border-bottom: 1px solid #222;
            background: #0d0d0d;
        }}
        .visitors-table td {{
            padding: 8px 16px;
            font-size: 13px;
            border-bottom: 1px solid #1a1a1a;
        }}
        .visitors-table tr:hover {{ background: #1a1a1a; }}
        .visitors-table .rank {{ color: #555; font-size: 12px; width: 40px; }}
        .visitors-table .count {{ color: #cc0000; font-weight: 700; text-align: right; width: 60px; }}
        .visitors-table a {{ color: #fff; text-decoration: none; }}
        .visitors-table a:hover {{ color: #cc0000; text-decoration: underline; }}

        /* Timeline */
        .timeline-container {{
            max-height: 500px;
            overflow-y: auto;
        }}
        .timeline-year {{
            font-size: 16px;
            font-weight: 900;
            color: #cc0000;
            padding: 12px 24px 6px;
            position: sticky;
            top: 0;
            background: #111;
            z-index: 2;
            border-bottom: 1px solid #222;
        }}
        .timeline-item {{
            padding: 8px 24px 8px 40px;
            border-bottom: 1px solid #1a1a1a;
            font-size: 13px;
            display: flex;
            gap: 12px;
            align-items: baseline;
            flex-wrap: wrap;
        }}
        .timeline-date {{
            color: #888;
            font-weight: 700;
            white-space: nowrap;
            min-width: 90px;
        }}
        .timeline-direction {{
            font-weight: 700;
            white-space: nowrap;
            min-width: 24px;
        }}
        .timeline-direction.arrived {{ color: #4caf50; }}
        .timeline-direction.departed {{ color: #ff9800; }}
        .timeline-pax {{
            flex: 1;
            min-width: 0;
        }}
        .timeline-pax a {{
            color: #ddd;
            text-decoration: none;
        }}
        .timeline-pax a:hover {{
            color: #cc0000;
            text-decoration: underline;
        }}
        .timeline-airport {{
            color: #666;
            font-size: 12px;
            white-space: nowrap;
        }}

        /* Mini Map */
        .mini-map {{
            height: 300px;
            background: #0a0a0a;
        }}

        @media (max-width: 768px) {{
            #overview-map {{
                height: 250px;
            }}
            .stats-row {{
                gap: 16px;
            }}
            .property-body {{
                flex-direction: column;
            }}
            .property-right {{
                width: 100%;
                border-top: 1px solid #222;
            }}
            .property-left {{
                border-right: none;
            }}
            .timeline-item {{
                flex-direction: column;
                gap: 4px;
                padding: 10px 24px 10px 40px;
            }}
            .timeline-date {{ min-width: auto; }}
            .timeline-airport {{ white-space: normal; }}
            .content {{
                padding: 12px;
            }}
            .header h1 {{ font-size: 16px; }}
        }}
    </style>
</head>
<body>

{nav_html}

<div class="header">
    <h1><span>&#x1F3E0;</span> Epstein Properties</h1>
    <div class="header-stats">
        <span><strong>{total_properties}</strong> properties</span>
    </div>
</div>

<div id="overview-map"></div>

<div class="content" id="properties-content"></div>

<script>
const PROPERTY_DATA = {property_data_json};

const TILE_URL = 'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png';
const TILE_ATTR = '&copy; OpenStreetMap, &copy; CARTO';

// ── Overview map ─────────────────────────────────────────────────────────────
const overviewMap = L.map('overview-map', {{
    center: [30, -50],
    zoom: 3,
    zoomControl: true,
    preferCanvas: true
}});

L.tileLayer(TILE_URL, {{
    attribution: TILE_ATTR,
    maxZoom: 18
}}).addTo(overviewMap);

Object.entries(PROPERTY_DATA).forEach(([name, data]) => {{
    const marker = L.circleMarker(data.coords, {{
        radius: 10,
        color: '#cc0000',
        fillColor: '#ff4444',
        fillOpacity: 0.9,
        weight: 2
    }}).addTo(overviewMap);

    marker.bindPopup(
        '<div style="font-family: -apple-system, sans-serif;">' +
        '<div style="font-size: 15px; font-weight: 900; color: #cc0000; margin-bottom: 4px;">' + name + '</div>' +
        '<div style="font-size: 12px; color: #666; margin-bottom: 6px;">' + data.desc + '</div>' +
        '<div style="font-size: 13px;"><strong>' + data.flights + '</strong> flights &middot; <strong>' + data.uniqueVisitors + '</strong> unique visitors</div>' +
        '</div>',
        {{ maxWidth: 320 }}
    );

    marker.bindTooltip(name, {{ direction: 'top', offset: [0, -8] }});
}});

// ── Render property sections ─────────────────────────────────────────────────
const contentEl = document.getElementById('properties-content');

Object.entries(PROPERTY_DATA).forEach(([name, data]) => {{
    const sectionId = name.toLowerCase().replace(/[^a-z0-9]+/g, '-');

    // Build top visitors table rows
    let visitorRows = '';
    data.topVisitors.forEach(([vName, vCount, vSlug], idx) => {{
        const link = vSlug
            ? '<a href="person.html#' + vSlug + '">' + vName + '</a>'
            : vName;
        visitorRows += '<tr><td class="rank">' + (idx + 1) + '</td><td>' + link + '</td><td class="count">' + vCount + '</td></tr>';
    }});

    // Build timeline HTML
    let timelineHtml = '';
    Object.entries(data.timeline).forEach(([year, entries]) => {{
        timelineHtml += '<div class="timeline-year">' + year + '</div>';
        entries.forEach(entry => {{
            const arrow = entry.direction === 'arrived' ? '&rarr;' : '&larr;';
            const dirClass = entry.direction;
            const paxLinks = entry.passengers.map(p => {{
                if (p.slug) {{
                    return '<a href="person.html#' + p.slug + '">' + p.name + '</a>';
                }}
                return p.name;
            }}).join(', ') || '<em style="color:#555;">No passengers listed</em>';

            timelineHtml += '<div class="timeline-item">' +
                '<span class="timeline-date">' + entry.date + '</span>' +
                '<span class="timeline-direction ' + dirClass + '">' + arrow + '</span>' +
                '<span class="timeline-pax">' + paxLinks + '</span>' +
                '<span class="timeline-airport">' + (entry.otherAirport || 'Unknown') + '</span>' +
                '</div>';
        }});
    }});

    const dateRangeStr = data.dateRange[0] && data.dateRange[1]
        ? data.dateRange[0] + ' &ndash; ' + data.dateRange[1]
        : 'N/A';

    const section = document.createElement('div');
    section.className = 'property-section';
    section.id = sectionId;
    section.innerHTML =
        '<div class="property-header">' +
            '<h2>' + name + '</h2>' +
            '<div class="desc">' + data.desc + '</div>' +
        '</div>' +
        '<div class="stats-row">' +
            '<div class="stat-item"><div class="stat-value">' + data.flights + '</div><div class="stat-label">Flights</div></div>' +
            '<div class="stat-item"><div class="stat-value">' + data.uniqueVisitors + '</div><div class="stat-label">Unique Visitors</div></div>' +
            '<div class="stat-item"><div class="stat-value">' + dateRangeStr + '</div><div class="stat-label">Date Range</div></div>' +
        '</div>' +
        '<div class="property-body">' +
            '<div class="property-left">' +
                '<div class="section-title">Top Visitors</div>' +
                '<table class="visitors-table">' +
                    '<thead><tr><th>#</th><th>Name</th><th>Visits</th></tr></thead>' +
                    '<tbody>' + visitorRows + '</tbody>' +
                '</table>' +
                '<div class="section-title">Flight Timeline</div>' +
                '<div class="timeline-container">' + timelineHtml + '</div>' +
            '</div>' +
            '<div class="property-right">' +
                '<div class="section-title">Route Map</div>' +
                '<div class="mini-map" id="map-' + sectionId + '"></div>' +
            '</div>' +
        '</div>';

    contentEl.appendChild(section);
}});

// ── Lazy-init mini maps with IntersectionObserver ────────────────────────────
const miniMapEls = document.querySelectorAll('.mini-map');
const initializedMaps = new Set();

const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
        if (!entry.isIntersecting) return;
        const el = entry.target;
        if (initializedMaps.has(el.id)) return;
        initializedMaps.add(el.id);

        // Find property data for this map
        const sectionEl = el.closest('.property-section');
        const propName = sectionEl.querySelector('h2').textContent;
        const data = PROPERTY_DATA[propName];
        if (!data) return;

        const miniMap = L.map(el.id, {{
            center: data.coords,
            zoom: 4,
            zoomControl: false,
            attributionControl: false,
            preferCanvas: true
        }});

        L.tileLayer(TILE_URL, {{
            maxZoom: 18
        }}).addTo(miniMap);

        // Property marker
        L.circleMarker(data.coords, {{
            radius: 8,
            color: '#cc0000',
            fillColor: '#ff4444',
            fillOpacity: 0.9,
            weight: 2
        }}).addTo(miniMap).bindTooltip(propName, {{ permanent: true, direction: 'top', offset: [0, -10] }});

        // Route lines
        const bounds = L.latLngBounds([data.coords]);
        data.routes.forEach(route => {{
            const weight = Math.min(1 + Math.log2(route.count + 1), 5);
            L.polyline([data.coords, route.coords], {{
                color: '#cc0000',
                weight: weight,
                opacity: 0.5
            }}).addTo(miniMap);

            L.circleMarker(route.coords, {{
                radius: 4,
                color: '#888',
                fillColor: '#aaa',
                fillOpacity: 0.7,
                weight: 1
            }}).addTo(miniMap).bindTooltip(route.airport + ' (' + route.count + ')', {{ direction: 'top', offset: [0, -6] }});

            bounds.extend(route.coords);
        }});

        if (data.routes.length > 0) {{
            miniMap.fitBounds(bounds, {{ padding: [30, 30] }});
        }}

        // Force Leaflet to recalculate size after DOM paint
        setTimeout(() => {{ miniMap.invalidateSize(); }}, 200);
    }});
}}, {{ rootMargin: '200px' }});

miniMapEls.forEach(el => observer.observe(el));
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
