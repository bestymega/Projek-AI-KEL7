"""
app.py
Flask API untuk pencarian rute Batik Solo Trans (BST) menggunakan A*.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from astar import astar, load_graph_from_file
from graph_builder import normalize

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Load graph sekali saat startup
# ---------------------------------------------------------------------------

try:
    GRAPH, COORDS, TRANSIT_MAP = load_graph_from_file()
    print(f"[app] Graph dimuat  : {len(GRAPH)} halte")
    print(f"[app] Transit points: {len(TRANSIT_MAP)} halte")
except FileNotFoundError as e:
    GRAPH, COORDS, TRANSIT_MAP = {}, {}, {}
    print(f"[app] WARNING: {e}")

# Lookup case-insensitive — dibuat sekali di startup
GRAPH_KEYS_LOWER: dict[str, str] = {k.lower(): k for k in GRAPH}


# ---------------------------------------------------------------------------
# Helper: ekstrak info koridor & transit dari path_edges
# ---------------------------------------------------------------------------

def extract_route_info(path: list[str], path_edges: list[dict]) -> dict:
    """
    Menganalisis path_edges hasil A* untuk menghasilkan info koridor & transit.

    Args:
        path       : list nama halte yang dilalui.
        path_edges : list {from, to, corridor, time} tiap segmen.

    Returns:
        dict:
            corridors     : list koridor unik yang digunakan (urut kemunculan)
            transit_points: list halte tempat penumpang ganti koridor
            total_transits: jumlah perpindahan koridor
            total_haltes  : jumlah halte yang dilewati (termasuk start & goal)
    """
    corridors_ordered = []
    seen_corridors    = set()
    transit_points    = []

    prev_corridor = None

    for edge in path_edges:
        corridor = edge["corridor"]

        # Kumpulkan koridor unik sesuai urutan kemunculan
        if corridor not in seen_corridors:
            corridors_ordered.append(corridor)
            seen_corridors.add(corridor)

        # Deteksi perpindahan koridor → catat halte transit
        if prev_corridor is not None and corridor != prev_corridor:
            transit_points.append(edge["from"])

        prev_corridor = corridor

    return {
        "corridors"     : corridors_ordered,
        "transit_points": transit_points,
        "total_transits": len(transit_points),
        "total_haltes"  : len(path)
    }


# ---------------------------------------------------------------------------
# Endpoint: GET /route
# ---------------------------------------------------------------------------

@app.route("/route", methods=["GET"])
def get_route():
    """
    Mencari rute tercepat antara dua halte BST.

    Query Params:
        start (str): Nama halte asal.
        goal  (str): Nama halte tujuan.

    Response JSON:
        start, goal, path, corridors, transit_points,
        total_transits, total_haltes, total_time, nodes_visited
    """
    # 1. Cek graph tersedia
    if not GRAPH:
        return jsonify({
            "error": "Graph belum tersedia. Jalankan 'python graph_builder.py' terlebih dahulu."
        }), 503

    # 2. Ambil parameter
    start_raw = request.args.get("start", "").strip()
    goal_raw  = request.args.get("goal",  "").strip()

    # 3. Validasi tidak kosong
    if not start_raw or not goal_raw:
        return jsonify({
            "error": "Parameter 'start' dan 'goal' wajib diisi.",
            "contoh": "/route?start=Terminal Palur&goal=UNS"
        }), 400

    # 4. Normalisasi & lookup case-insensitive
    start_key = GRAPH_KEYS_LOWER.get(normalize(start_raw))
    goal_key  = GRAPH_KEYS_LOWER.get(normalize(goal_raw))

    if not start_key:
        return jsonify({"error": f"Halte '{start_raw}' tidak ditemukan."}), 400
    if not goal_key:
        return jsonify({"error": f"Halte '{goal_raw}' tidak ditemukan."}), 400

    # 5. Kasus start == goal
    if start_key == goal_key:
        return jsonify({
            "start"         : start_key,
            "goal"          : goal_key,
            "path"          : [start_key],
            "path_edges"    : [],
            "corridors"     : [],
            "transit_points": [],
            "total_transits": 0,
            "total_haltes"  : 1,
            "total_time"    : 0,
            "nodes_visited" : 1
        }), 200

    # 6. Jalankan A*
    try:
        result     = astar(GRAPH, COORDS, start_key, goal_key)
        route_info = extract_route_info(result["path"], result["path_edges"])

        return jsonify({
            "start"         : start_key,
            "goal"          : goal_key,
            "path"          : result["path"],
            "path_edges"    : result["path_edges"],
            "corridors"     : route_info["corridors"],
            "transit_points": route_info["transit_points"],
            "total_transits": route_info["total_transits"],
            "total_haltes"  : route_info["total_haltes"],
            "total_time"    : result["total_time"],
            "nodes_visited" : result["nodes_visited"]
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Terjadi kesalahan internal."}), 500


# ---------------------------------------------------------------------------
# Endpoint: GET /haltes
# ---------------------------------------------------------------------------

@app.route("/haltes", methods=["GET"])
def list_haltes():
    """Mengembalikan daftar semua halte dalam graph."""
    return jsonify({
        "total" : len(GRAPH),
        "haltes": sorted(GRAPH.keys())
    }), 200


# ---------------------------------------------------------------------------
# Endpoint: GET /transit — bonus: daftar semua halte transit
# ---------------------------------------------------------------------------

@app.route("/transit", methods=["GET"])
def list_transit():
    """Mengembalikan semua halte yang melayani lebih dari satu koridor."""
    return jsonify({
        "total"  : len(TRANSIT_MAP),
        "transit": TRANSIT_MAP
    }), 200


# ---------------------------------------------------------------------------
# Health check & debug
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status"       : "ok",
        "service"      : "BST Route Finder",
        "graph_loaded" : bool(GRAPH),
        "total_haltes" : len(GRAPH)
    }), 200


@app.route("/debug/neighbors/<path:halte>")
def debug_neighbors(halte):
    key = GRAPH_KEYS_LOWER.get(normalize(halte))
    if not key:
        return jsonify({"error": f"Halte '{halte}' tidak ditemukan."}), 404
    return jsonify({"halte": key, "tetangga": GRAPH.get(key, [])})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)