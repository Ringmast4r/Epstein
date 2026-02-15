#!/usr/bin/env python3
"""
Build docs/routes.html — interactive route analysis of all Epstein flights.
Reads data/flights.json and embeds computed route, yearly, monthly, and aircraft
data into a self-contained HTML file with D3.js charts and a Leaflet map.
"""

import json
from pathlib import Path
from collections import Counter

from build_utils import load_flights, fuzzy_match_airport, get_nav_html, NAV_CSS

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "routes.html"


def main():
    flights = load_flights()

    # ── Resolve coordinates for every flight ─────────────────────────────────
    enriched = []
    for f in flights:
        origin = f.get("origin", "")
        dest = f.get("destination", "")
        enriched.append({
            "date": f.get("date", ""),
            "origin": origin,
            "destination": dest,
            "aircraft": f.get("aircraft", ""),
            "oc": fuzzy_match_airport(origin),
            "dc": fuzzy_match_airport(dest),
        })

    # ── Route pair counts ────────────────────────────────────────────────────
    route_counter = Counter()
    for e in enriched:
        if e["origin"] and e["destination"]:
            route_counter[(e["origin"], e["destination"])] += 1

    unique_routes = len(route_counter)

    # Top 20 routes with resolved coordinates
    top_routes = []
    for (orig, dest), count in route_counter.most_common(20):
        top_routes.append({
            "route": f"{orig} \u2192 {dest}",
            "origin": orig,
            "dest": dest,
            "count": count,
            "oc": fuzzy_match_airport(orig),
            "dc": fuzzy_match_airport(dest),
        })

    # ── Yearly flight volume ─────────────────────────────────────────────────
    yearly = Counter()
    for e in enriched:
        if e["date"] and len(e["date"]) >= 4:
            yearly[e["date"][:4]] += 1

    # ── Monthly flight volume (year-month grid) ──────────────────────────────
    monthly = Counter()
    for e in enriched:
        if e["date"] and len(e["date"]) >= 7:
            monthly[e["date"][:7]] += 1

    # ── Aircraft breakdown ───────────────────────────────────────────────────
    aircraft_counter = Counter()
    for e in enriched:
        ac = e["aircraft"].strip() if e["aircraft"] else "Unknown"
        if ac:
            aircraft_counter[ac] += 1
    aircraft_list = [{"name": name, "count": count}
                     for name, count in aircraft_counter.most_common()]

    # ── Date range ───────────────────────────────────────────────────────────
    dates = sorted(e["date"] for e in enriched if e["date"])
    date_min = dates[0] if dates else "1997-01-01"
    date_max = dates[-1] if dates else "2019-12-31"

    # ── Serialize to JSON ────────────────────────────────────────────────────
    flights_json = json.dumps(enriched)
    top_routes_json = json.dumps(top_routes)
    yearly_json = json.dumps(dict(yearly))
    monthly_json = json.dumps(dict(monthly))
    aircraft_json = json.dumps(aircraft_list)

    nav_html = get_nav_html("routes")

    html = build_html(
        flights_json=flights_json,
        top_routes_json=top_routes_json,
        yearly_json=yearly_json,
        monthly_json=monthly_json,
        aircraft_json=aircraft_json,
        nav_html=nav_html,
        total_flights=len(flights),
        unique_routes=unique_routes,
        date_min=date_min,
        date_max=date_max,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT} ({len(flights)} flights, {unique_routes} unique routes)")


def build_html(flights_json, top_routes_json, yearly_json, monthly_json,
               aircraft_json, nav_html, total_flights, unique_routes,
               date_min, date_max):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Route Analysis — Epstein Flights</title>
    <meta name="description" content="Route analysis of every known Epstein flight (1997-2019). Top routes, yearly volume, heatmap, and aircraft breakdown.">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
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

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px 40px;
        }}

        /* ── Date range filter ─────────────────────────────────── */
        .filter-bar {{
            background: #111;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
            border-bottom: 1px solid #222;
        }}
        .filter-bar label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .filter-bar .range-wrap {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 260px;
        }}
        .filter-bar input[type="range"] {{
            flex: 1;
            accent-color: #cc0000;
            cursor: pointer;
        }}
        .filter-bar .range-label {{
            color: #cc0000;
            font-weight: 700;
            font-size: 14px;
            min-width: 36px;
            text-align: center;
        }}
        .filter-bar button {{
            background: #333;
            color: #fff;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
        }}
        .filter-bar button:hover {{ background: #cc0000; }}
        .filter-count {{
            font-size: 13px;
            color: #cc0000;
            font-weight: 700;
            margin-left: auto;
        }}

        /* ── Sections ──────────────────────────────────────────── */
        .section {{
            margin-top: 32px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 900;
            color: #fff;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #cc0000;
        }}
        .section-title span {{ color: #cc0000; }}

        /* ── Top routes ────────────────────────────────────────── */
        .top-routes-grid {{
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }}
        .route-table-wrap {{
            flex: 1;
            overflow-x: auto;
        }}
        .route-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .route-table th {{
            text-align: left;
            padding: 8px 12px;
            background: #111;
            color: #888;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #222;
        }}
        .route-table td {{
            padding: 6px 12px;
            border-bottom: 1px solid #1a1a1a;
        }}
        .route-table tr:hover {{ background: #111; }}
        .route-rank {{ color: #555; font-weight: 700; width: 40px; }}
        .route-name {{ color: #fff; white-space: nowrap; }}
        .route-count {{ color: #cc0000; font-weight: 700; width: 60px; text-align: right; }}
        .route-bar-cell {{ width: 200px; }}
        .route-bar {{
            height: 14px;
            background: #cc0000;
            border-radius: 2px;
            min-width: 4px;
        }}

        #routeMap {{
            width: 500px;
            min-width: 300px;
            height: 400px;
            border-radius: 6px;
            border: 1px solid #222;
            flex-shrink: 0;
        }}

        /* ── Charts ────────────────────────────────────────────── */
        .chart-container {{
            background: #111;
            border-radius: 6px;
            border: 1px solid #222;
            padding: 16px;
            overflow-x: auto;
        }}

        .d3-tooltip {{
            position: absolute;
            background: #222;
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            border: 1px solid #cc0000;
            z-index: 1000;
        }}

        /* ── Heatmap ───────────────────────────────────────────── */
        .heatmap-wrap {{
            overflow-x: auto;
        }}
        .heatmap-label {{
            font-size: 11px;
            fill: #888;
        }}

        /* ── Aircraft ──────────────────────────────────────────── */
        .aircraft-bar-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 4px 0;
            border-bottom: 1px solid #1a1a1a;
        }}
        .aircraft-name {{
            width: 300px;
            min-width: 200px;
            font-size: 13px;
            color: #ccc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .aircraft-bar-wrap {{
            flex: 1;
            height: 18px;
            position: relative;
        }}
        .aircraft-bar {{
            height: 100%;
            background: #cc0000;
            border-radius: 2px;
            min-width: 4px;
        }}
        .aircraft-count {{
            min-width: 50px;
            text-align: right;
            font-size: 13px;
            font-weight: 700;
            color: #cc0000;
        }}
        .aircraft-highlight {{
            background: #1a0000;
            border: 1px solid #cc0000;
            border-radius: 4px;
            padding: 4px 0;
        }}
        .aircraft-highlight .aircraft-name {{
            color: #ff4444;
            font-weight: 700;
        }}
        .aircraft-highlight .aircraft-bar {{
            background: #ff2222;
        }}
        .lolita-label {{
            font-size: 10px;
            color: #ff4444;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
            margin-left: 8px;
        }}

        /* ── Mobile ────────────────────────────────────────────── */
        @media (max-width: 768px) {{
            .top-routes-grid {{
                flex-direction: column;
            }}
            #routeMap {{
                width: 100%;
                height: 250px;
            }}
            .route-table-wrap {{
                overflow-x: auto;
            }}
            .aircraft-name {{
                width: 160px;
                min-width: 120px;
            }}
            .container {{
                padding: 0 10px 30px;
            }}
            .header {{ padding: 10px 12px; }}
            .header h1 {{ font-size: 16px; }}
            .filter-bar {{ padding: 10px 12px; gap: 10px; }}
        }}
    </style>
</head>
<body>

{nav_html}

<div class="header">
    <h1><span>&#x2708;</span> Route Analysis</h1>
    <div class="header-stats">
        <span><strong>{total_flights:,}</strong> flights</span>
        <span><strong>{unique_routes:,}</strong> unique routes</span>
        <span><strong>{date_min[:4]} &ndash; {date_max[:4]}</strong></span>
    </div>
</div>

<div class="filter-bar">
    <label>Date Range</label>
    <div class="range-wrap">
        <span class="range-label" id="startLabel">1997</span>
        <input type="range" id="startYear" min="1997" max="2019" value="1997">
    </div>
    <span style="color:#555;">&ndash;</span>
    <div class="range-wrap">
        <input type="range" id="endYear" min="1997" max="2019" value="2019">
        <span class="range-label" id="endLabel">2019</span>
    </div>
    <button onclick="resetRange()">Reset</button>
    <span class="filter-count" id="filterCount">{total_flights:,} flights</span>
</div>

<div class="container">

    <!-- Section 1: Top Routes -->
    <div class="section" id="topRoutesSection">
        <div class="section-title"><span>#1</span> Top Routes</div>
        <div class="top-routes-grid">
            <div class="route-table-wrap">
                <table class="route-table">
                    <thead>
                        <tr><th>Rank</th><th>Route</th><th>Flights</th><th></th></tr>
                    </thead>
                    <tbody id="routeTableBody"></tbody>
                </table>
            </div>
            <div id="routeMap"></div>
        </div>
    </div>

    <!-- Section 2: Yearly Flight Volume -->
    <div class="section">
        <div class="section-title"><span>#2</span> Yearly Flight Volume</div>
        <div class="chart-container" id="yearlyChart" style="height:340px;"></div>
    </div>

    <!-- Section 3: Flight Heatmap -->
    <div class="section">
        <div class="section-title"><span>#3</span> Flight Heatmap (Year &times; Month)</div>
        <div class="chart-container heatmap-wrap" id="heatmapChart"></div>
    </div>

    <!-- Section 4: Aircraft Breakdown -->
    <div class="section">
        <div class="section-title"><span>#4</span> Aircraft Breakdown</div>
        <div class="chart-container" id="aircraftChart"></div>
    </div>

</div>

<div class="d3-tooltip" id="tooltip" style="opacity:0;"></div>

<script>
// ── Embedded data ───────────────────────────────────────────────────────────
const FLIGHTS = {flights_json};
const TOP_ROUTES = {top_routes_json};
const YEARLY = {yearly_json};
const MONTHLY = {monthly_json};
const AIRCRAFT = {aircraft_json};

// ── Tooltip helper ──────────────────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');
function showTip(evt, html) {{
    tooltip.innerHTML = html;
    tooltip.style.opacity = 1;
    tooltip.style.left = (evt.pageX + 12) + 'px';
    tooltip.style.top = (evt.pageY - 28) + 'px';
}}
function hideTip() {{
    tooltip.style.opacity = 0;
}}

// ── Slider state ────────────────────────────────────────────────────────────
const startSlider = document.getElementById('startYear');
const endSlider = document.getElementById('endYear');
const startLabel = document.getElementById('startLabel');
const endLabel = document.getElementById('endLabel');

function getRange() {{
    let s = parseInt(startSlider.value);
    let e = parseInt(endSlider.value);
    if (s > e) {{ [s, e] = [e, s]; }}
    return [s, e];
}}

function filterFlights() {{
    const [sy, ey] = getRange();
    return FLIGHTS.filter(f => {{
        if (!f.date || f.date.length < 4) return false;
        const yr = parseInt(f.date.substring(0, 4));
        return yr >= sy && yr <= ey;
    }});
}}

function onSliderChange() {{
    const [sy, ey] = getRange();
    startLabel.textContent = sy;
    endLabel.textContent = ey;
    renderAll();
}}

startSlider.addEventListener('input', onSliderChange);
endSlider.addEventListener('input', onSliderChange);

function resetRange() {{
    startSlider.value = 1997;
    endSlider.value = 2019;
    startLabel.textContent = '1997';
    endLabel.textContent = '2019';
    renderAll();
}}

// ── Recompute from filtered flights ─────────────────────────────────────────
function computeRoutes(filtered) {{
    const counter = {{}};
    filtered.forEach(f => {{
        if (f.origin && f.destination) {{
            const key = f.origin + ' \\u2192 ' + f.destination;
            if (!counter[key]) {{
                counter[key] = {{route: key, origin: f.origin, dest: f.destination, count: 0, oc: f.oc, dc: f.dc}};
            }}
            counter[key].count++;
        }}
    }});
    return Object.values(counter).sort((a, b) => b.count - a.count).slice(0, 20);
}}

function computeYearly(filtered) {{
    const y = {{}};
    filtered.forEach(f => {{
        if (f.date && f.date.length >= 4) {{
            const yr = f.date.substring(0, 4);
            y[yr] = (y[yr] || 0) + 1;
        }}
    }});
    return y;
}}

function computeMonthly(filtered) {{
    const m = {{}};
    filtered.forEach(f => {{
        if (f.date && f.date.length >= 7) {{
            const ym = f.date.substring(0, 7);
            m[ym] = (m[ym] || 0) + 1;
        }}
    }});
    return m;
}}

function computeAircraft(filtered) {{
    const c = {{}};
    filtered.forEach(f => {{
        const ac = (f.aircraft || '').trim() || 'Unknown';
        c[ac] = (c[ac] || 0) + 1;
    }});
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([name, count]) => ({{name, count}}));
}}

// ── Leaflet map ─────────────────────────────────────────────────────────────
const routeMap = L.map('routeMap', {{
    center: [28, -60],
    zoom: 3,
    zoomControl: true,
    preferCanvas: true
}});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png', {{
    attribution: '&copy; OpenStreetMap, &copy; CARTO',
    maxZoom: 18
}}).addTo(routeMap);

let routeLines = L.layerGroup().addTo(routeMap);

function drawRouteMap(topRoutes) {{
    routeLines.clearLayers();
    const maxCount = topRoutes.length > 0 ? topRoutes[0].count : 1;
    topRoutes.forEach(r => {{
        if (!r.oc || !r.dc) return;
        const weight = Math.max(2, Math.log2(r.count + 1) * 1.5);
        const line = L.polyline([r.oc, r.dc], {{
            color: '#cc0000',
            weight: weight,
            opacity: 0.7
        }}).addTo(routeLines);
        line.bindTooltip(r.route + ' (' + r.count + ')', {{ sticky: true }});
    }});
}}

// ── Render top routes table ─────────────────────────────────────────────────
function renderRouteTable(topRoutes) {{
    const tbody = document.getElementById('routeTableBody');
    const maxCount = topRoutes.length > 0 ? topRoutes[0].count : 1;
    tbody.innerHTML = topRoutes.map((r, i) => {{
        const pct = (r.count / maxCount * 100).toFixed(1);
        return '<tr>'
            + '<td class="route-rank">' + (i + 1) + '</td>'
            + '<td class="route-name">' + r.route + '</td>'
            + '<td class="route-count">' + r.count + '</td>'
            + '<td class="route-bar-cell"><div class="route-bar" style="width:' + pct + '%"></div></td>'
            + '</tr>';
    }}).join('');
}}

// ── Render yearly bar chart (D3) ────────────────────────────────────────────
function renderYearly(yearlyData) {{
    const container = document.getElementById('yearlyChart');
    container.innerHTML = '';
    const [sy, ey] = getRange();

    const entries = [];
    for (let yr = sy; yr <= ey; yr++) {{
        entries.push({{year: yr, count: yearlyData[String(yr)] || 0}});
    }}

    const margin = {{top: 20, right: 20, bottom: 40, left: 50}};
    const width = Math.max(container.clientWidth - margin.left - margin.right, 300);
    const height = 300 - margin.top - margin.bottom;

    const svg = d3.select(container).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    const x = d3.scaleBand()
        .domain(entries.map(d => d.year))
        .range([0, width])
        .padding(0.2);

    const y = d3.scaleLinear()
        .domain([0, d3.max(entries, d => d.count) || 1])
        .nice()
        .range([height, 0]);

    svg.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).tickFormat(d => d))
        .selectAll('text')
        .style('fill', '#888')
        .style('font-size', '11px')
        .attr('transform', 'rotate(-45)')
        .attr('text-anchor', 'end');

    svg.append('g')
        .call(d3.axisLeft(y).ticks(6))
        .selectAll('text')
        .style('fill', '#888')
        .style('font-size', '11px');

    svg.selectAll('.domain, .tick line').style('stroke', '#333');

    svg.selectAll('.bar')
        .data(entries)
        .enter().append('rect')
        .attr('class', 'bar')
        .attr('x', d => x(d.year))
        .attr('y', d => y(d.count))
        .attr('width', x.bandwidth())
        .attr('height', d => height - y(d.count))
        .attr('fill', '#cc0000')
        .attr('rx', 2)
        .on('mouseover', function(evt, d) {{
            d3.select(this).attr('fill', '#ff2222');
            showTip(evt, '<strong>' + d.year + '</strong>: ' + d.count + ' flights');
        }})
        .on('mousemove', function(evt) {{
            tooltip.style.left = (evt.pageX + 12) + 'px';
            tooltip.style.top = (evt.pageY - 28) + 'px';
        }})
        .on('mouseout', function() {{
            d3.select(this).attr('fill', '#cc0000');
            hideTip();
        }});
}}

// ── Render heatmap (D3) ─────────────────────────────────────────────────────
function renderHeatmap(monthlyData) {{
    const container = document.getElementById('heatmapChart');
    container.innerHTML = '';
    const [sy, ey] = getRange();

    const years = [];
    for (let yr = sy; yr <= ey; yr++) years.push(yr);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    const cellW = 40, cellH = 30;
    const margin = {{top: 30, right: 20, bottom: 10, left: 50}};
    const width = margin.left + months.length * cellW + margin.right;
    const height = margin.top + years.length * cellH + margin.bottom;

    // Compute max for color scale
    let maxVal = 0;
    years.forEach(yr => {{
        months.forEach((m, mi) => {{
            const key = yr + '-' + String(mi + 1).padStart(2, '0');
            const v = monthlyData[key] || 0;
            if (v > maxVal) maxVal = v;
        }});
    }});

    const colorScale = d3.scaleLinear()
        .domain([0, maxVal || 1])
        .range(['#1a1a1a', '#cc0000']);

    const svg = d3.select(container).append('svg')
        .attr('width', width)
        .attr('height', height);

    const g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Month headers
    months.forEach((m, mi) => {{
        g.append('text')
            .attr('x', mi * cellW + cellW / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .attr('class', 'heatmap-label')
            .text(m);
    }});

    // Year labels
    years.forEach((yr, yi) => {{
        g.append('text')
            .attr('x', -8)
            .attr('y', yi * cellH + cellH / 2 + 4)
            .attr('text-anchor', 'end')
            .attr('class', 'heatmap-label')
            .text(yr);
    }});

    // Cells
    years.forEach((yr, yi) => {{
        months.forEach((m, mi) => {{
            const key = yr + '-' + String(mi + 1).padStart(2, '0');
            const v = monthlyData[key] || 0;
            g.append('rect')
                .attr('x', mi * cellW + 1)
                .attr('y', yi * cellH + 1)
                .attr('width', cellW - 2)
                .attr('height', cellH - 2)
                .attr('rx', 3)
                .attr('fill', colorScale(v))
                .attr('stroke', '#0a0a0a')
                .attr('stroke-width', 1)
                .on('mouseover', function(evt) {{
                    d3.select(this).attr('stroke', '#fff').attr('stroke-width', 2);
                    showTip(evt, '<strong>' + months[mi] + ' ' + yr + '</strong>: ' + v + ' flights');
                }})
                .on('mousemove', function(evt) {{
                    tooltip.style.left = (evt.pageX + 12) + 'px';
                    tooltip.style.top = (evt.pageY - 28) + 'px';
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('stroke', '#0a0a0a').attr('stroke-width', 1);
                    hideTip();
                }});

            // Show count in cell if > 0
            if (v > 0) {{
                g.append('text')
                    .attr('x', mi * cellW + cellW / 2)
                    .attr('y', yi * cellH + cellH / 2 + 4)
                    .attr('text-anchor', 'middle')
                    .attr('fill', v > maxVal * 0.5 ? '#fff' : '#888')
                    .attr('font-size', '10px')
                    .attr('pointer-events', 'none')
                    .text(v);
            }}
        }});
    }});
}}

// ── Render aircraft breakdown ───────────────────────────────────────────────
function renderAircraft(aircraftData) {{
    const container = document.getElementById('aircraftChart');
    container.innerHTML = '';
    if (aircraftData.length === 0) return;

    const maxCount = aircraftData[0].count;
    const html = aircraftData.map(a => {{
        const pct = (a.count / maxCount * 100).toFixed(1);
        const isLolita = a.name.toLowerCase().includes('727');
        const cls = isLolita ? 'aircraft-bar-row aircraft-highlight' : 'aircraft-bar-row';
        const label = isLolita ? '<span class="lolita-label">Lolita Express</span>' : '';
        return '<div class="' + cls + '">'
            + '<div class="aircraft-name">' + a.name + label + '</div>'
            + '<div class="aircraft-bar-wrap"><div class="aircraft-bar" style="width:' + pct + '%"></div></div>'
            + '<div class="aircraft-count">' + a.count + '</div>'
            + '</div>';
    }}).join('');
    container.innerHTML = html;
}}

// ── Master render ───────────────────────────────────────────────────────────
function renderAll() {{
    const filtered = filterFlights();
    document.getElementById('filterCount').textContent = filtered.length.toLocaleString() + ' flights';

    const topRoutes = computeRoutes(filtered);
    renderRouteTable(topRoutes);
    drawRouteMap(topRoutes);

    const yearlyData = computeYearly(filtered);
    renderYearly(yearlyData);

    const monthlyData = computeMonthly(filtered);
    renderHeatmap(monthlyData);

    const aircraftData = computeAircraft(filtered);
    renderAircraft(aircraftData);
}}

// ── Initial render ──────────────────────────────────────────────────────────
renderAll();

// Fix Leaflet tile render after initial layout
setTimeout(() => {{ routeMap.invalidateSize(); }}, 200);
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
