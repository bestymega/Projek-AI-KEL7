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
// ─────────────────────────────────────────────────────────
// PUBLIC API findOptimalRoute() (INTEGRASI BACKEND)
// ─────────────────────────────────────────────────────────
async function findOptimalRoute(originName, destName) {
    try {
        const response = await fetch(`http://localhost:5000/route?start=${encodeURIComponent(originName)}&goal=${encodeURIComponent(destName)}`);
        if (!response.ok) {
            console.error('Gagal mengambil rute dari server');
            return null;
        }
        const data = await response.json();
        
        const annotatedPath = [];
        for (let i = 0; i < data.path.length; i++) {
            const rawName = data.path[i];
            const haltObj = getHalt(rawName);
            const stopName = haltObj ? haltObj.name : rawName;
            let corridor = null;
            if (i > 0) {
                corridor = data.path_edges[i - 1].corridor;
            }
            annotatedPath.push({ name: stopName, corridor: corridor });
        }
        
        const annotated = annotatedPath.map((stop, i) => {
            const prev = annotatedPath[i-1];
            const isTransit = prev && prev.corridor && stop.corridor && prev.corridor !== stop.corridor;
            return { ...stop, isTransit };
        });

        return {
            path: annotated,
            totalTime: data.total_time,
            corridors: data.corridors
        };
    } catch (e) {
        console.error("Backend fetch error:", e);
        return null;
    }
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
let allHaltMarkers = {};

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

async function fetchRouteGeometry(coords) {
    if (coords.length < 2) return coords;
    
    const CHUNK_SIZE = 25;
    let fullGeometry = [];
    
    for (let i = 0; i < coords.length - 1; i += (CHUNK_SIZE - 1)) {
        const chunk = coords.slice(i, i + CHUNK_SIZE);
        const coordString = chunk.map(c => `${c[0]},${c[1]}`).join(';');
        const url = `https://router.project-osrm.org/route/v1/driving/${coordString}?overview=full&geometries=geojson`;
        
        try {
            const res = await fetch(url);
            const data = await res.json();
            if (data.code === 'Ok' && data.routes.length > 0) {
                const geom = data.routes[0].geometry.coordinates;
                if (fullGeometry.length > 0 && geom.length > 0) {
                    fullGeometry = fullGeometry.concat(geom.slice(1));
                } else {
                    fullGeometry = fullGeometry.concat(geom);
                }
            } else {
                return coords;
            }
        } catch (e) {
            console.error("OSRM error:", e);
            return coords;
        }
    }
    return fullGeometry;
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

function updateMarkerStyles() {
    const origin = selOrigin.value.toLowerCase();
    const dest = selDest.value.toLowerCase();
    
    for (const [name, marker] of Object.entries(allHaltMarkers)) {
        const el = marker.customEl;
        if (name === origin) {
            el.style.background = '#16a34a'; // green
            el.style.width = '20px';
            el.style.height = '20px';
            el.style.zIndex = '10';
        } else if (name === dest) {
            el.style.background = '#dc2626'; // red
            el.style.width = '20px';
            el.style.height = '20px';
            el.style.zIndex = '10';
        } else {
            el.style.background = '#9ca3af'; // gray
            el.style.width = '14px';
            el.style.height = '14px';
            el.style.zIndex = '1';
        }
    }
}

document.getElementById('btn-swap').addEventListener('click', () => {
    const tmp = selOrigin.value;
    selOrigin.value = selDest.value;
    selDest.value = tmp;
    updateMarkerStyles();
});

['input', 'change'].forEach(evt => {
    selOrigin.addEventListener(evt, updateMarkerStyles);
    selDest.addEventListener(evt, updateMarkerStyles);
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

async function renderMap(result) {
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
        const lngs = coords.map(c => c[0]), lats = coords.map(c => c[1]);
        const bounds = [[Math.min(...lngs)-0.005, Math.min(...lats)-0.005], [Math.max(...lngs)+0.005, Math.max(...lats)+0.005]];
        map.fitBounds(bounds, { padding: 60, duration: 1000 });

        const routeGeometry = await fetchRouteGeometry(coords);
        drawRoute(routeGeometry);
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

    if (!getHalt(originVal) || !getHalt(destVal)) {
        alert('Nama halte yang Anda ketik tidak ada di sistem. Mohon pilih halte yang tersedia dari daftar yang muncul.');
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
        const edgesData = await edgesRes.json();

        HALTS_DATA.forEach(h => { haltMap[h.name.toLowerCase()] = h; });
        TRANSIT_DATA.forEach(({ halte, koridor }) => {
            const k = halte.toLowerCase();
            if (!transitMap[k]) transitMap[k] = [];
            if (!transitMap[k].includes(koridor)) transitMap[k].push(koridor);
        });

        const haltNamesInEdges = new Set();
        edgesData.forEach(e => {
            haltNamesInEdges.add(e.from.toLowerCase());
            haltNamesInEdges.add(e.to.toLowerCase());
        });

        const uniqueHaltNamesMap = new Map();
        HALTS_DATA.forEach(h => { 
            const k = h.name.toLowerCase();
            if (haltNamesInEdges.has(k) && !uniqueHaltNamesMap.has(k)) {
                uniqueHaltNamesMap.set(k, h.name);
            }
        });
        const uniqueHaltNames = Array.from(uniqueHaltNamesMap.values()).sort((a, b) => a.localeCompare(b, 'id'));

        const datalist = document.getElementById('halts-list');
        uniqueHaltNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            datalist.appendChild(opt);
            
            // Render interactive marker on map
            const h = getHalt(name);
            if (h) {
                const el = document.createElement('div');
                el.className = 'halt-marker';
                el.style.cssText = `
                    background: #9ca3af; color: #fff; border-radius: 50%;
                    width: 14px; height: 14px;
                    border: 2px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,.2); cursor: pointer;
                    transition: all 0.3s ease;
                `;
                
                const popupNode = document.createElement('div');
                popupNode.style.cssText = 'font-family:Poppins,sans-serif;font-size:12px;font-weight:600;padding:4px 6px;text-align:center;min-width:120px;';
                popupNode.innerHTML = `
                    <div style="margin-bottom:8px">${h.name}</div>
                    <div style="display:flex;gap:6px;justify-content:center;">
                        <button class="btn-set-origin" style="background:#16a34a;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;flex:1;">Set Asal</button>
                        <button class="btn-set-dest" style="background:#dc2626;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;flex:1;">Set Tujuan</button>
                    </div>
                `;
                
                const popup = new maptilersdk.Popup({ offset: 12, closeButton: true, maxWidth: '200px' }).setDOMContent(popupNode);
                
                const marker = new maptilersdk.Marker({ element: el })
                    .setLngLat([h.lon, h.lat])
                    .setPopup(popup)
                    .addTo(map);
                    
                marker.customEl = el;
                allHaltMarkers[name.toLowerCase()] = marker;

                // Event listeners for popup buttons
                popupNode.querySelector('.btn-set-origin').addEventListener('click', () => {
                    selOrigin.value = h.name;
                    updateMarkerStyles();
                    popup.remove();
                });
                
                popupNode.querySelector('.btn-set-dest').addEventListener('click', () => {
                    selDest.value = h.name;
                    updateMarkerStyles();
                    popup.remove();
                });
            }
        });
        
        updateMarkerStyles();
    } catch (e) {
        console.error("Gagal memuat data JSON dari backend:", e);
    }
}

initData();