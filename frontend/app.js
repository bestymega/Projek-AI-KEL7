// ─────────────────────────────────────────────────────────
// BUILD LOOKUP STRUCTURES
// ─────────────────────────────────────────────────────────
const haltMap = {};  // name (lower) -> halt object
const transitMap = {};
let HALTS_DATA = [];
let TRANSIT_DATA = [];
let EDGES_DATA_EMBED = [];

// Get halt coord by name (case-insensitive)
function getHalt(name) {
    return haltMap[name.toLowerCase()] || HALTS_DATA.find(h => h.name.toLowerCase() === name.toLowerCase());
}

function getCorridors(name) {
    return transitMap[name.toLowerCase()] || [];
}

// ─────────────────────────────────────────────────────────
// A* PATHFINDING
// ─────────────────────────────────────────────────────────
function buildGraph(edges) {
    const g = {};
    edges.forEach(e => {
        const f = e.from.toLowerCase(), t = e.to.toLowerCase();
        if (!g[f]) g[f] = [];
        g[f].push({ to: t, time: e.time, corridor: e.corridor });
    });
    return g;
}

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371, rad = Math.PI / 180;
    const dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
    const a = Math.sin(dLat/2)**2 + Math.cos(lat1*rad)*Math.cos(lat2*rad)*Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)) * 6; // ~6 min/km walking estimate
}

function aStar(graph, originName, destName) {
    const origin = originName.toLowerCase(), dest = destName.toLowerCase();
    const destHalt = getHalt(destName);

    function h(nodeName) {
        const node = getHalt(nodeName);
        if (!node || !destHalt) return 0;
        return haversine(node.lat, node.lon, destHalt.lat, destHalt.lon);
    }

    const TRANSIT_PENALTY = 5; // minutes per corridor change
    const open = [{ node: origin, corridor: null, cost: 0, f: h(origin), path: [{ name: originName, corridor: null }], corridors: [] }];
    const visited = new Map();

    while (open.length) {
        open.sort((a, b) => a.f - b.f);
        const cur = open.shift();

        const stateKey = `${cur.node}|${cur.corridor}`;
        if (visited.has(stateKey) && visited.get(stateKey) <= cur.cost) continue;
        visited.set(stateKey, cur.cost);

        if (cur.node === dest) {
            return { path: cur.path, totalTime: cur.cost, corridors: [...new Set(cur.corridors)] };
        }

        const neighbors = graph[cur.node] || [];
        for (const edge of neighbors) {
            const transitCost = (cur.corridor && cur.corridor !== edge.corridor) ? TRANSIT_PENALTY : 0;
            const newCost = cur.cost + edge.time + transitCost;
            const newKey = `${edge.to}|${edge.corridor}`;
            if (visited.has(newKey) && visited.get(newKey) <= newCost) continue;

            const edgeName = HALTS_DATA.find(h => h.name.toLowerCase() === edge.to)?.name || edge.to;
            open.push({
                node: edge.to,
                corridor: edge.corridor,
                cost: newCost,
                f: newCost + h(edge.to),
                path: [...cur.path, { name: edgeName, corridor: edge.corridor }],
                corridors: [...cur.corridors, edge.corridor]
            });
        }
    }
    return null;
}

// ─────────────────────────────────────────────────────────
// PUBLIC API findOptimalRoute()
// ─────────────────────────────────────────────────────────
async function findOptimalRoute(originName, destName) {
    // INTEGRATION POINT: Silahkan ganti EDGES_DATA_EMBED dengan hasil fetch('edges.json') jika pakai server lokal
    const edges = EDGES_DATA_EMBED;
    const graph = buildGraph(edges);

    // Efek loading simulasi network delay
    await new Promise(r => setTimeout(r, 600));

    const result = aStar(graph, originName, destName);
    if (!result) return null;

    const annotated = result.path.map((stop, i) => {
        const prev = result.path[i-1];
        const isTransit = prev && prev.corridor && stop.corridor && prev.corridor !== stop.corridor;
        return { ...stop, isTransit };
    });

    return {
        path: annotated,
        totalTime: result.totalTime,
        corridors: result.corridors
    };
}

// ─────────────────────────────────────────────────────────
// MAP INIT
// ─────────────────────────────────────────────────────────
maptilersdk.config.apiKey = 'qXVFiRaNFXzFbyYuiRQN';
const map = new maptilersdk.Map({
    container: 'map',
    style: maptilersdk.MapStyle.STREETS,
    center: [110.8243, -7.5666],
    zoom: 13
});

let currentMarkers = [];
let currentPolyline = null;

function clearMapLayers() {
    currentMarkers.forEach(m => m.remove());
    currentMarkers = [];
    if (currentPolyline) {
        if (map.getLayer('route-line')) map.removeLayer('route-line');
        if (map.getSource('route-src')) map.removeSource('route-src');
        currentPolyline = null;
    }
}

function addMarker(lat, lon, type, label) {
    const colors = { origin: '#16a34a', dest: '#dc2626', transit: '#d97706', via: '#1a56db' };
    const el = document.createElement('div');
    el.style.cssText = `
        background:${colors[type]};color:#fff;border-radius:50%;
        width:${type==='via'?'10px':'28px'};height:${type==='via'?'10px':'28px'};
        display:flex;align-items:center;justify-content:center;
        font-size:${type==='via'?'6px':'12px'};
        border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3);cursor:pointer;
    `;
    
    if (type !== 'via') {
        el.innerHTML = type === 'origin' ? '<i class="fa-solid fa-location-crosshairs" style="font-size:12px"></i>' : type === 'dest' ? '<i class="fa-solid fa-flag-checkered" style="font-size:11px"></i>' : '<i class="fa-solid fa-shuffle" style="font-size:11px"></i>';
    }

    const popup = new maptilersdk.Popup({ offset: 16, closeButton: false })
        .setHTML(`<div style="font-family:Poppins,sans-serif;font-size:12px;font-weight:600;padding:4px 6px">${label}</div>`);

    const marker = new maptilersdk.Marker({ element: el })
        .setLngLat([lon, lat])
        .setPopup(popup)
        .addTo(map);
    currentMarkers.push(marker);
    return marker;
}

function drawRoute(coords) {
    if (map.getLayer('route-line')) map.removeLayer('route-line');
    if (map.getSource('route-src')) map.removeSource('route-src');

    map.addSource('route-src', {
        type: 'geojson',
        data: {
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: coords }
        }
    });
    map.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'route-src',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#1a56db', 'line-width': 5, 'line-opacity': 0.85 }
    });
    currentPolyline = true;
}

// ─────────────────────────────────────────────────────────
// POPULATE DROPDOWNS & INTERACTION
// ─────────────────────────────────────────────────────────
const selOrigin = document.getElementById('sel-origin');
const selDest = document.getElementById('sel-dest');

document.getElementById('btn-swap').addEventListener('click', () => {
    const tmp = selOrigin.value;
    selOrigin.value = selDest.value;
    selDest.value = tmp;
});

// ─────────────────────────────────────────────────────────
// RENDER RESULTS
// ─────────────────────────────────────────────────────────
function formatTime(mins) {
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins/60)}j ${mins%60}m`;
}

function countTransits(path) {
    let t = 0;
    for (let i = 1; i < path.length; i++) {
        if (path[i].isTransit) t++;
    }
    return t;
}

function corridorBadge(k) {
    return `<span class="s-badge ${k}">${k}</span>`;
}

function renderSummary(result) {
    const uniqueCorridors = [...new Set(result.path.map(p => p.corridor).filter(Boolean))];
    document.getElementById('sum-corridor').innerHTML = uniqueCorridors.map(corridorBadge).join('') || '–';
    document.getElementById('sum-time').textContent = formatTime(result.totalTime);
    document.getElementById('sum-stops').textContent = result.path.length;
    document.getElementById('sum-transit').textContent = countTransits(result.path);
}

function renderTimeline(result) {
    const tl = document.getElementById('timeline');
    tl.innerHTML = '';

    const segments = [];
    let seg = [];
    result.path.forEach((stop, i) => {
        if (i === 0) { seg.push(stop); return; }
        if (stop.isTransit) {
            segments.push(seg);
            seg = [stop];
        } else {
            seg.push(stop);
        }
    });
    segments.push(seg);

    function stopCard(stop, type) {
        const corridors = getCorridors(stop.name);
        const tagsHtml = stop.corridor ? corridorBadge(stop.corridor) : corridors.map(corridorBadge).join('');
        if (type === 'transit') {
            return `<div class="tl-card transit-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
                    <div><div class="tl-name">${stop.name}</div><div class="tl-sub">Titik transit — ganti koridor</div></div>
                    <span class="transit-badge">Transit</span>
                </div>
                <div class="tl-tags">${tagsHtml}</div>
            </div>`;
        } else if (type === 'dest') {
            return `<div class="tl-card dest-card"><div class="tl-name">${stop.name}</div><div class="tl-tags">${tagsHtml}</div></div>`;
        } else {
            return `<div class="tl-card"><div class="tl-name">${stop.name}</div><div class="tl-tags">${tagsHtml}</div></div>`;
        }
    }

    segments.forEach((seg, si) => {
        const isLast = si === segments.length - 1;
        seg.forEach((stop, idx) => {
            const isOrigin = si === 0 && idx === 0;
            const isDest = isLast && idx === seg.length - 1;
            const isTransitStop = stop.isTransit;
            const isIntermediate = !isOrigin && !isDest && !isTransitStop;

            if (isIntermediate) return;

            let dotClass = 'via', dotIcon = '';
            if (isOrigin) { dotClass = 'origin'; dotIcon = '<i class="fa-solid fa-location-crosshairs"></i>'; }
            else if (isDest) { dotClass = 'destination'; dotIcon = '<i class="fa-solid fa-flag-checkered"></i>'; }
            else if (isTransitStop) { dotClass = 'transit'; dotIcon = '<i class="fa-solid fa-shuffle"></i>'; }

            const div = document.createElement('div');
            div.className = 'tl-stop';

            let lineHtml = '';
            if (isOrigin && seg.length > 2) lineHtml = `<div class="tl-line dashed"></div>`;
            else if (isOrigin && seg.length > 1) lineHtml = `<div class="tl-line"></div>`;
            else if (!isDest) lineHtml = `<div class="tl-line dashed"></div>`;

            div.innerHTML = `
                <div class="tl-left"><div class="tl-dot ${dotClass}">${dotIcon}</div>${lineHtml}</div>
                <div class="tl-content ${isDest?'dest':''}">${stopCard(stop, isOrigin ? 'origin' : isDest ? 'dest' : 'transit')}</div>
            `;
            tl.appendChild(div);

            if (isOrigin && seg.length > 2) {
                const skipped = seg.length - 2;
                const noteDiv = document.createElement('div');
                noteDiv.className = 'tl-stop';
                noteDiv.innerHTML = `
                    <div class="tl-left"><div class="tl-line"></div></div>
                    <div class="tl-content small"><div class="skip-note"><i class="fa-solid fa-ellipsis-vertical"></i> Melewati ${skipped} halte berikutnya</div></div>
                `;
                tl.appendChild(noteDiv);
            }
        });
    });
}

function renderMap(result) {
    clearMapLayers();
    const coords = [];
    result.path.forEach((stop, i) => {
        const h = getHalt(stop.name);
        if (!h) return;
        coords.push([h.lon, h.lat]);

        let type = 'via';
        if (i === 0) type = 'origin';
        else if (i === result.path.length - 1) type = 'dest';
        else if (stop.isTransit) type = 'transit';

        addMarker(h.lat, h.lon, type, stop.name);
    });

    if (coords.length > 1) {
        map.once('idle', () => drawRoute(coords));
        setTimeout(() => drawRoute(coords), 200);
        
        const lngs = coords.map(c => c[0]), lats = coords.map(c => c[1]);
        const bounds = [[Math.min(...lngs)-0.005, Math.min(...lats)-0.005], [Math.max(...lngs)+0.005, Math.max(...lats)+0.005]];
        map.fitBounds(bounds, { padding: 60, duration: 1000 });
    }
}

// ─────────────────────────────────────────────────────────
// SEARCH HANDLER
// ─────────────────────────────────────────────────────────
document.getElementById('btn-search').addEventListener('click', async () => {
    const originVal = selOrigin.value;
    const destVal   = selDest.value;
    const btn = document.getElementById('btn-search');
    const panel = document.getElementById('result-panel');

    if (!originVal || !destVal) {
        alert('Pilih halte asal dan tujuan terlebih dahulu.');
        return;
    }

    btn.classList.add('loading');
    btn.innerHTML = '<i class="fa-solid fa-spinner spin"></i> Mencari...';
    panel.classList.remove('visible');

    try {
        const result = await findOptimalRoute(originVal, destVal);
        if (!result) {
            panel.innerHTML = `<div class="error-box"><i class="fa-solid fa-circle-exclamation"></i> Tidak ditemukan rute dari <b>${originVal}</b> ke <b>${destVal}</b>. Coba halte lain.</div>`;
        } else {
            // Restore original panel structure if it was overwritten by an error before
            panel.innerHTML = `
                <div class="divider"></div>
                <div class="summary-grid" id="summary-grid">
                    <div class="summary-card"><div class="s-icon"><i class="fa-solid fa-bus"></i></div><div class="s-label">Koridor</div><div class="s-value" id="sum-corridor">–</div></div>
                    <div class="summary-card"><div class="s-icon"><i class="fa-regular fa-clock"></i></div><div class="s-label">Waktu</div><div class="s-value" id="sum-time">–</div></div>
                    <div class="summary-card"><div class="s-icon"><i class="fa-solid fa-map-pin"></i></div><div class="s-label">Halte</div><div class="s-value" id="sum-stops">–</div></div>
                    <div class="summary-card"><div class="s-icon"><i class="fa-solid fa-shuffle"></i></div><div class="s-label">Transit</div><div class="s-value" id="sum-transit">–</div></div>
                </div>
                <div class="timeline-header"><i class="fa-solid fa-route"></i> Detail Perjalanan</div>
                <div class="timeline" id="timeline"></div>
            `;
            renderSummary(result);
            renderTimeline(result);
            renderMap(result);
        }
        panel.classList.add('visible');
    } catch (err) {
        console.error(err);
        panel.innerHTML = `<div class="error-box"><i class="fa-solid fa-circle-exclamation"></i> Terjadi kesalahan saat mencari rute.</div>`;
        panel.classList.add('visible');
    } finally {
        btn.classList.remove('loading');
        btn.innerHTML = '<i class="fa-solid fa-route"></i> Cari Rute';
    }
});

// ─────────────────────────────────────────────────────────
// INIT DATA
// ─────────────────────────────────────────────────────────
async function initData() {
    try {
        const [haltsRes, transitRes, edgesRes] = await Promise.all([
            fetch('../backend/data/halts.json'),
            fetch('../backend/data/transit.json'),
            fetch('../backend/data/edges.json')
        ]);
        
        HALTS_DATA = await haltsRes.json();
        TRANSIT_DATA = await transitRes.json();
        EDGES_DATA_EMBED = await edgesRes.json();

        HALTS_DATA.forEach(h => { haltMap[h.name.toLowerCase()] = h; });
        TRANSIT_DATA.forEach(({ halte, koridor }) => {
            const k = halte.toLowerCase();
            if (!transitMap[k]) transitMap[k] = [];
            if (!transitMap[k].includes(koridor)) transitMap[k].push(koridor);
        });

        const haltNamesInEdges = new Set();
        EDGES_DATA_EMBED.forEach(e => { haltNamesInEdges.add(e.from); haltNamesInEdges.add(e.to); });
        const uniqueHaltNames = [...haltNamesInEdges].sort((a, b) => a.localeCompare(b, 'id'));

        uniqueHaltNames.forEach(name => {
            [selOrigin, selDest].forEach(sel => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = name.charAt(0).toUpperCase() + name.slice(1);
                sel.appendChild(opt);
            });
        });
    } catch (e) {
        console.error("Gagal memuat data JSON dari backend:", e);
    }
}

initData();