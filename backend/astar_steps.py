"""
astar_steps.py
Versi A* yang mencatat setiap iterasi untuk keperluan visualisasi step-by-step.
Logika A* TIDAK DIUBAH — hanya ditambahkan pencatatan state per iterasi.

PERUBAHAN dari versi sebelumnya:
- [BARU] Parameter transit_penalty: penalti waktu (menit) saat pindah koridor
- [BARU] Setiap step snapshot menyertakan field `transit_here` (bool) agar
  visualisasi Streamlit dapat menandai halte transit dengan warna berbeda.
"""

import heapq
import math
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ---------------------------------------------------------------------------
# Haversine & Heuristic (sama persis dengan astar.py)
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def heuristic(node: str, goal: str, coords: dict) -> float:
    if node not in coords or goal not in coords:
        return 0.0
    c1 = coords[node]
    c2 = coords[goal]
    distance_km = haversine(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
    speed_kmpm  = 30.0 / 60.0
    return distance_km / speed_kmpm


# ---------------------------------------------------------------------------
# Helper: rekonstruksi path sementara dari came_from
# ---------------------------------------------------------------------------

def _reconstruct_path(came_from: dict, node: str) -> list[str]:
    path = []
    cur  = node
    while cur is not None:
        path.append(cur)
        meta = came_from.get(cur)
        cur  = meta[0] if meta else None
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# A* dengan pencatatan steps dan transit penalty
# ---------------------------------------------------------------------------

def astar_with_steps(
    graph: dict,
    coords: dict,
    start: str,
    goal: str,
    transit_penalty: float = 5.0,   # [BARU] penalti (menit) saat ganti koridor
) -> dict:
    """
    Sama dengan astar() tetapi menyimpan snapshot setiap iterasi ke `steps`.

    Args:
        graph           (dict) : Adjacency list {halte: [{to, time, corridor}]}.
        coords          (dict) : {halte: {lat, lon}}.
        start           (str)  : Nama halte asal.
        goal            (str)  : Nama halte tujuan.
        transit_penalty (float): Biaya tambahan (menit) saat berpindah koridor.
                                 Default 5 menit. Set 0 untuk menonaktifkan.

    Returns:
        dict:
            path          : rute optimal
            path_edges    : edge yang dilalui beserta corridor
            total_time    : total waktu (menit), sudah termasuk penalti transit
            nodes_visited : jumlah node dieksplorasi
            transit_count : jumlah perpindahan koridor
            steps         : list snapshot per iterasi A*
                            Setiap step memiliki field tambahan:
                            - transit_here (bool): apakah terjadi transit di node ini
                            - penalty_applied (float): besar penalti yang ditambahkan
    """
    if start not in graph:
        raise ValueError(f"Halte asal '{start}' tidak ditemukan dalam graph.")
    if goal not in graph:
        raise ValueError(f"Halte tujuan '{goal}' tidak ditemukan dalam graph.")

    counter   = 0
    open_set: list[tuple] = []
    heapq.heappush(open_set, (0.0, counter, start))

    g_score: dict[str, float] = {start: 0.0}
    came_from: dict[str, tuple | None] = {start: None}
    closed_set: set[str] = set()
    nodes_visited = 0

    # Hitung h untuk semua node di awal agar konsisten
    h_score: dict[str, float] = {}
    for node in graph:
        h_score[node] = heuristic(node, goal, coords)

    steps: list[dict] = []
    step_num = 0

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current in closed_set:
            continue

        closed_set.add(current)
        nodes_visited += 1
        step_num += 1

        neighbors_added = []
        is_goal = (current == goal)

        # [BARU] Cek apakah node ini merupakan titik transit
        current_meta     = came_from.get(current)
        current_corridor = current_meta[1] if current_meta else None
        transit_here     = False   # akan di-set True jika ada pergantian koridor masuk
        penalty_applied  = 0.0

        if not is_goal:
            for neighbor in graph.get(current, []):
                next_node = neighbor["to"]
                edge_cost = neighbor["time"]
                corridor  = neighbor.get("corridor", "")

                if next_node in closed_set:
                    continue

                neighbors_added.append(next_node)
                tentative_g = g_score[current] + edge_cost

                # [BARU] Tambahkan penalti jika koridor berubah
                added_penalty = 0.0
                if current_corridor is not None and corridor != current_corridor:
                    added_penalty = transit_penalty
                    tentative_g  += added_penalty
                    transit_here  = True   # current adalah titik transit

                if tentative_g < g_score.get(next_node, float("inf")):
                    g_score[next_node]   = tentative_g
                    came_from[next_node] = (current, corridor, edge_cost)
                    f_val = tentative_g + h_score.get(next_node, 0)
                    counter += 1
                    heapq.heappush(open_set, (f_val, counter, next_node))
                    if added_penalty > 0:
                        penalty_applied = added_penalty

        # Snapshot open_set saat ini (ambil nilai unik per node, ambil f terbaik)
        open_nodes: dict[str, float] = {}
        for f, _, n in open_set:
            if n not in open_nodes or f < open_nodes[n]:
                open_nodes[n] = f
        open_list_snapshot = [
            {"node": n, "f": round(f, 2)} for n, f in open_nodes.items()
            if n not in closed_set
        ]

        # g, f, h score snapshot
        g_snap = {n: round(v, 2) for n, v in g_score.items()}
        f_snap = {n: round(g_score.get(n, 0) + h_score.get(n, 0), 2) for n in g_score}
        h_snap = {n: round(h_score.get(n, 0), 2) for n in g_score}

        # Parent snapshot
        parent_snap = {}
        for n, meta in came_from.items():
            parent_snap[n] = meta[0] if meta else None

        # Path sementara ke current
        path_so_far = _reconstruct_path(came_from, current)

        steps.append({
            "step"            : step_num,
            "current"         : current,
            "open_set"        : open_list_snapshot,
            "closed_set"      : list(closed_set),
            "neighbors_added" : neighbors_added,
            "g_score"         : g_snap,
            "h_score"         : h_snap,
            "f_score"         : f_snap,
            "parent"          : parent_snap,
            "path_so_far"     : path_so_far,
            "goal_found"      : is_goal,
            # [BARU] info transit untuk visualisasi
            "transit_here"    : transit_here,
            "penalty_applied" : penalty_applied,
        })

        if is_goal:
            # Rekonstruksi path & path_edges
            path       = []
            path_edges = []
            node = goal

            while node is not None:
                path.append(node)
                meta = came_from[node]
                if meta is not None:
                    prev_node, corridor, edge_time = meta
                    path_edges.append({
                        "from"    : prev_node,
                        "to"      : node,
                        "corridor": corridor,
                        "time"    : edge_time,
                    })
                node = meta[0] if meta else None

            path.reverse()
            path_edges.reverse()

            # Hitung jumlah transit (perpindahan koridor)
            transit_count = sum(
                1
                for i in range(1, len(path_edges))
                if path_edges[i]["corridor"] != path_edges[i - 1]["corridor"]
            )

            return {
                "path"         : path,
                "path_edges"   : path_edges,
                "total_time"   : round(g_score[goal], 2),
                "nodes_visited": nodes_visited,
                "transit_count": transit_count,
                "steps"        : steps,
            }

    raise RuntimeError(
        f"Tidak ditemukan rute dari '{start}' ke '{goal}'."
    )


# ---------------------------------------------------------------------------
# Load graph (sama dengan astar.py)
# ---------------------------------------------------------------------------

def load_graph_from_file() -> tuple[dict, dict, dict]:
    graph_path = os.path.join(DATA_DIR, "graph.json")
    if not os.path.exists(graph_path):
        raise FileNotFoundError("File data/graph.json tidak ditemukan.")
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["graph"], data["coords"], data.get("transit_map", {})