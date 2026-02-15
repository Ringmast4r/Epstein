#!/usr/bin/env python3
"""
Build docs/network.html — interactive D3.js force-directed network graph
of passenger co-flight relationships from Epstein flight logs.
Reads data/flights.json and data/persons.json via build_utils.
"""

import json
import math
from pathlib import Path
from collections import Counter

from build_utils import (
    load_flights,
    load_persons,
    build_passenger_counts,
    build_name_to_slug,
    build_co_passenger_matrix,
    build_name_to_person,
    CATEGORY_COLORS,
    get_nav_html,
    NAV_CSS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "network.html"


def main():
    flights = load_flights()
    persons = load_persons()

    passenger_counts = build_passenger_counts(flights)
    name_to_slug = build_name_to_slug(persons)
    name_to_person = build_name_to_person(persons)
    co_matrix = build_co_passenger_matrix(flights)

    # ── Build nodes ──────────────────────────────────────────────────────
    nodes = []
    for name, count in passenger_counts.items():
        person = name_to_person.get(name)
        category = person["category"] if person else "other"
        slug = name_to_slug.get(name, "")
        nodes.append({
            "id": name,
            "flightCount": count,
            "category": category,
            "slug": slug,
        })

    # ── Build edges ──────────────────────────────────────────────────────
    edges = []
    for (a, b), weight in co_matrix.items():
        edges.append({
            "source": a,
            "target": b,
            "weight": weight,
        })

    # ── Build sidebar: top 30 by unique co-passengers ────────────────────
    connection_counts = Counter()
    for (a, b) in co_matrix:
        connection_counts[a] += 1
        connection_counts[b] += 1
    top_connected = connection_counts.most_common(30)

    # ── Collect categories that actually appear ──────────────────────────
    categories_in_use = sorted(set(n["category"] for n in nodes))

    # ── Serialize ────────────────────────────────────────────────────────
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    top_connected_json = json.dumps(top_connected)
    categories_json = json.dumps(categories_in_use)
    category_colors_json = json.dumps(CATEGORY_COLORS)

    nav_html = get_nav_html("network")

    html = build_html(
        nodes_json=nodes_json,
        edges_json=edges_json,
        top_connected_json=top_connected_json,
        categories_json=categories_json,
        category_colors_json=category_colors_json,
        nav_html=nav_html,
        node_count=len(nodes),
        edge_count=len(edges),
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT} ({len(nodes)} nodes, {len(edges)} edges)")


def build_html(nodes_json, edges_json, top_connected_json, categories_json,
               category_colors_json, nav_html, node_count, edge_count):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epstein Passenger Network</title>
    <meta name="description" content="Interactive force-directed network graph of Epstein flight passenger co-travel relationships. {node_count} individuals, {edge_count} connections.">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; overflow: hidden; }}

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
        .controls input[type="text"] {{
            background: #1a1a1a;
            color: #fff;
            border: 1px solid #333;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 13px;
            min-width: 200px;
        }}
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
        .controls button.btn-secondary {{
            background: #333;
        }}
        .controls button.btn-secondary:hover {{
            background: #555;
        }}
        .cat-filters {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .cat-filter-item {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: #ccc;
            cursor: pointer;
        }}
        .cat-filter-item input[type="checkbox"] {{
            accent-color: #cc0000;
        }}

        .main {{
            display: flex;
            height: calc(100vh - 150px);
        }}

        .graph-container {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        .graph-container svg {{
            width: 100%;
            height: 100%;
            display: block;
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
        .sidebar-item {{
            display: flex;
            align-items: center;
            padding: 8px 16px;
            border-bottom: 1px solid #1a1a1a;
            cursor: pointer;
            font-size: 13px;
            gap: 8px;
        }}
        .sidebar-item:hover {{ background: #1a1a1a; }}
        .sidebar-item.active {{ background: #1a0000; border-left: 3px solid #cc0000; }}
        .sidebar-rank {{
            color: #555;
            font-weight: 700;
            font-size: 11px;
            min-width: 24px;
        }}
        .sidebar-name {{ color: #fff; flex: 1; }}
        .sidebar-count {{
            color: #cc0000;
            font-weight: 700;
            font-size: 12px;
        }}

        /* Node click popup */
        .node-popup {{
            position: absolute;
            background: #111;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 16px;
            min-width: 260px;
            max-width: 320px;
            z-index: 100;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            pointer-events: auto;
        }}
        .node-popup .popup-close {{
            position: absolute;
            top: 8px;
            right: 10px;
            background: none;
            border: none;
            color: #666;
            font-size: 18px;
            cursor: pointer;
            padding: 0 4px;
        }}
        .node-popup .popup-close:hover {{ color: #fff; }}
        .node-popup .popup-name {{
            font-size: 16px;
            font-weight: 900;
            color: #cc0000;
            margin-bottom: 6px;
            padding-right: 24px;
        }}
        .node-popup .popup-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .node-popup .popup-flights {{
            font-size: 13px;
            color: #999;
            margin-bottom: 10px;
        }}
        .node-popup .popup-flights strong {{ color: #fff; }}
        .node-popup .popup-conn-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666;
            margin-bottom: 6px;
            font-weight: 700;
        }}
        .node-popup .popup-conn-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            padding: 3px 0;
            border-bottom: 1px solid #1a1a1a;
        }}
        .node-popup .popup-conn-count {{
            color: #cc0000;
            font-weight: 700;
            margin-left: 12px;
        }}
        .node-popup .popup-link {{
            display: inline-block;
            margin-top: 10px;
            color: #cc0000;
            text-decoration: none;
            font-size: 13px;
            font-weight: 700;
        }}
        .node-popup .popup-link:hover {{ text-decoration: underline; }}

        @media (max-width: 768px) {{
            .sidebar {{ display: none; }}
            .main {{ height: calc(100vh - 180px); }}
            .header {{ padding: 10px 12px; }}
            .header h1 {{ font-size: 16px; }}
            .controls {{ padding: 8px 12px; gap: 8px; }}
            .controls input[type="text"] {{ min-width: 140px; }}
            .cat-filters {{ display: none; }}
        }}
    </style>
</head>
<body>

{nav_html}

<div class="header">
    <h1><span>&#x1F578;</span> Passenger Network</h1>
    <div class="header-stats">
        <span><strong>{node_count:,}</strong> individuals</span>
        <span><strong>{edge_count:,}</strong> connections</span>
    </div>
</div>

<div class="controls">
    <label>Search</label>
    <input type="text" id="searchInput" placeholder="Type a name...">
    <button class="btn-secondary" id="resetBtn">Reset</button>
    <div class="cat-filters" id="catFilters"></div>
</div>

<div class="main">
    <div class="graph-container" id="graphContainer">
        <svg id="networkSvg"></svg>
    </div>
    <div class="sidebar">
        <div class="sidebar-title">Most Connected</div>
        <div id="sidebarList"></div>
    </div>
</div>

<script>
const NODES = {nodes_json};
const EDGES = {edges_json};
const TOP_CONNECTED = {top_connected_json};
const CATEGORIES = {categories_json};
const CATEGORY_COLORS = {category_colors_json};

// ── Build adjacency for popup connections ────────────────────────────
const adjacency = {{}};
EDGES.forEach(e => {{
    if (!adjacency[e.source]) adjacency[e.source] = {{}};
    if (!adjacency[e.target]) adjacency[e.target] = {{}};
    adjacency[e.source][e.target] = (adjacency[e.source][e.target] || 0) + e.weight;
    adjacency[e.target][e.source] = (adjacency[e.target][e.source] || 0) + e.weight;
}});

// ── Node map for quick lookup ────────────────────────────────────────
const nodeMap = {{}};
NODES.forEach(n => {{ nodeMap[n.id] = n; }});

// ── SVG setup ────────────────────────────────────────────────────────
const container = document.getElementById('graphContainer');
const svg = d3.select('#networkSvg');
const width = container.clientWidth;
const height = container.clientHeight;

const g = svg.append('g');

// Zoom behavior
const zoom = d3.zoom()
    .scaleExtent([0.1, 8])
    .on('zoom', (event) => {{
        g.attr('transform', event.transform);
    }});
svg.call(zoom);

// ── Force simulation ─────────────────────────────────────────────────
const simulation = d3.forceSimulation(NODES)
    .force('link', d3.forceLink(EDGES).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => getRadius(d) + 2));

// ── Draw edges ───────────────────────────────────────────────────────
const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(EDGES)
    .join('line')
    .attr('stroke', '#555')
    .attr('stroke-width', d => 0.5 + Math.log2(d.weight))
    .attr('stroke-opacity', d => 0.15 + Math.min(d.weight / 10, 0.4));

// ── Draw nodes ───────────────────────────────────────────────────────
function getRadius(d) {{
    return Math.min(4 + Math.sqrt(d.flightCount) * 1.5, 25);
}}

const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('circle')
    .data(NODES)
    .join('circle')
    .attr('r', d => getRadius(d))
    .attr('fill', d => CATEGORY_COLORS[d.category] || '#757575')
    .attr('stroke', '#333')
    .attr('stroke-width', 1)
    .attr('cursor', 'pointer')
    .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded))
    .on('click', (event, d) => {{
        event.stopPropagation();
        showPopup(d, event);
    }});

node.append('title').text(d => `${{d.id}} (${{d.flightCount}} flights)`);

// ── Tick ─────────────────────────────────────────────────────────────
simulation.on('tick', () => {{
    link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
    node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);
}});

// ── Drag behavior ────────────────────────────────────────────────────
function dragStarted(event, d) {{
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}}
function dragged(event, d) {{
    d.fx = event.x;
    d.fy = event.y;
}}
function dragEnded(event, d) {{
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}}

// ── Click popup ──────────────────────────────────────────────────────
let popupEl = null;

function showPopup(d, event) {{
    closePopup();

    const adj = adjacency[d.id] || {{}};
    const connections = Object.entries(adj)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    const catColor = CATEGORY_COLORS[d.category] || '#757575';

    let connHtml = '';
    connections.forEach(([name, count]) => {{
        connHtml += '<div class="popup-conn-row"><span>' + name + '</span><span class="popup-conn-count">' + count + '</span></div>';
    }});

    const profileLink = d.slug
        ? '<a class="popup-link" href="person.html#' + d.slug + '">View Profile &rarr;</a>'
        : '';

    popupEl = document.createElement('div');
    popupEl.className = 'node-popup';
    popupEl.innerHTML =
        '<button class="popup-close" onclick="closePopup()">&times;</button>' +
        '<div class="popup-name">' + d.id + '</div>' +
        '<span class="popup-badge" style="background:' + catColor + '22; color:' + catColor + '; border: 1px solid ' + catColor + ';">' + d.category + '</span>' +
        '<div class="popup-flights"><strong>' + d.flightCount + '</strong> flights</div>' +
        (connections.length > 0 ? '<div class="popup-conn-title">Top Connections</div>' + connHtml : '') +
        profileLink;

    // Position near the click, clamped to viewport
    const rect = container.getBoundingClientRect();
    let left = event.clientX - rect.left + 16;
    let top = event.clientY - rect.top - 20;
    if (left + 320 > rect.width) left = left - 340;
    if (top + 300 > rect.height) top = rect.height - 310;
    if (top < 0) top = 10;

    popupEl.style.left = left + 'px';
    popupEl.style.top = top + 'px';

    container.appendChild(popupEl);
}}

function closePopup() {{
    if (popupEl) {{
        popupEl.remove();
        popupEl = null;
    }}
}}

svg.on('click', () => {{ closePopup(); }});

// ── Search ───────────────────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');

searchInput.addEventListener('input', () => {{
    const query = searchInput.value.toLowerCase().trim();
    if (!query) {{
        resetView();
        return;
    }}
    node
        .attr('opacity', d => d.id.toLowerCase().includes(query) ? 1 : 0.08)
        .attr('stroke', d => d.id.toLowerCase().includes(query) ? '#fff' : '#333')
        .attr('stroke-width', d => d.id.toLowerCase().includes(query) ? 2 : 1);
    link.attr('stroke-opacity', 0.03);
}});

// ── Category checkboxes ──────────────────────────────────────────────
const catContainer = document.getElementById('catFilters');
const catState = {{}};

CATEGORIES.forEach(cat => {{
    catState[cat] = true;
    const label = document.createElement('label');
    label.className = 'cat-filter-item';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.addEventListener('change', () => {{
        catState[cat] = cb.checked;
        applyCategoryFilter();
    }});
    const colorDot = document.createElement('span');
    colorDot.style.cssText = 'display:inline-block;width:10px;height:10px;border-radius:50%;background:' + (CATEGORY_COLORS[cat] || '#757575');
    const txt = document.createTextNode(' ' + cat);
    label.appendChild(cb);
    label.appendChild(colorDot);
    label.appendChild(txt);
    catContainer.appendChild(label);
}});

function applyCategoryFilter() {{
    const activeNames = new Set();
    node
        .attr('opacity', d => {{
            const visible = catState[d.category];
            if (visible) activeNames.add(d.id);
            return visible ? 1 : 0.05;
        }})
        .attr('stroke', d => catState[d.category] ? '#333' : '#222')
        .attr('stroke-width', 1);
    link.attr('stroke-opacity', d => {{
        const sId = typeof d.source === 'object' ? d.source.id : d.source;
        const tId = typeof d.target === 'object' ? d.target.id : d.target;
        return (activeNames.has(sId) && activeNames.has(tId)) ? 0.15 + Math.min(d.weight / 10, 0.4) : 0.02;
    }});
}}

// ── Reset ────────────────────────────────────────────────────────────
document.getElementById('resetBtn').addEventListener('click', () => {{
    searchInput.value = '';
    // Reset category checkboxes
    document.querySelectorAll('#catFilters input[type="checkbox"]').forEach(cb => {{ cb.checked = true; }});
    CATEGORIES.forEach(cat => {{ catState[cat] = true; }});
    resetView();
    closePopup();
    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
}});

function resetView() {{
    node
        .attr('opacity', 1)
        .attr('stroke', '#333')
        .attr('stroke-width', 1);
    link
        .attr('stroke-opacity', d => 0.15 + Math.min(d.weight / 10, 0.4));
}}

// ── Sidebar ──────────────────────────────────────────────────────────
const sidebarList = document.getElementById('sidebarList');

TOP_CONNECTED.forEach(([name, count], i) => {{
    const div = document.createElement('div');
    div.className = 'sidebar-item';
    div.innerHTML = '<span class="sidebar-rank">' + (i + 1) + '</span>' +
        '<span class="sidebar-name">' + name + '</span>' +
        '<span class="sidebar-count">' + count + '</span>';
    div.addEventListener('click', () => {{
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        div.classList.add('active');
        highlightNode(name);
    }});
    sidebarList.appendChild(div);
}});

function highlightNode(name) {{
    searchInput.value = '';
    const connSet = new Set([name]);
    if (adjacency[name]) {{
        Object.keys(adjacency[name]).forEach(n => connSet.add(n));
    }}
    node
        .attr('opacity', d => connSet.has(d.id) ? 1 : 0.05)
        .attr('stroke', d => d.id === name ? '#fff' : '#333')
        .attr('stroke-width', d => d.id === name ? 3 : 1);
    link.attr('stroke-opacity', d => {{
        const sId = typeof d.source === 'object' ? d.source.id : d.source;
        const tId = typeof d.target === 'object' ? d.target.id : d.target;
        return (sId === name || tId === name) ? 0.6 : 0.02;
    }});

    // Pan to the highlighted node
    const target = NODES.find(n => n.id === name);
    if (target && target.x != null) {{
        const transform = d3.zoomTransform(svg.node());
        const newTransform = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(transform.k)
            .translate(-target.x, -target.y);
        svg.transition().duration(600).call(zoom.transform, newTransform);
    }}
}}

// ── Handle window resize ─────────────────────────────────────────────
window.addEventListener('resize', () => {{
    simulation.force('center', d3.forceCenter(container.clientWidth / 2, container.clientHeight / 2));
    simulation.alpha(0.3).restart();
}});
</script>

</body>
</html>'''


if __name__ == "__main__":
    main()
