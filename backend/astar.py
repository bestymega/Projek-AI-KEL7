"""
astar.py
Implementasi algoritma A* untuk pencarian rute Batik Solo Trans (BST).

- g(n) : waktu tempuh kumulatif dari start ke node n
- h(n) : estimasi waktu ke goal menggunakan Haversine Distance
- f(n) : g(n) + h(n)

PERUBAHAN dari versi sebelumnya:
- came_from sekarang menyimpan (node_sebelumnya, corridor) bukan hanya node
- Return tambahan: path_edges — list edge yang dilalui beserta corridor-nya
  → digunakan app.py untuk ekstrak info koridor & transit tanpa mengubah logika A*
- [BARU] Parameter transit_penalty: penalti waktu (menit) saat pindah koridor
"""

import heapq
import math
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ---------------------------------------------------------------------------
# Haversine Distance
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Menghitung jarak (km) antara dua koordinat dengan rumus Haversine."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def heuristic(node: str, goal: str, coords: dict) -> float:
    """
    h(n): estimasi waktu tempuh (menit) dari node ke goal via Haversine.
    Asumsi kecepatan rata-rata bus 30 km/jam.
    """
    if node not in coords or goal not in coords:
        return 0.0
    c1 = coords[node]
    c2 = coords[goal]
    distance_km  = haversine(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
    speed_kmpm   = 30.0 / 60.0
    return distance_km / speed_kmpm


# ---------------------------------------------------------------------------
# Algoritma A* — dengan transit penalty
# ---------------------------------------------------------------------------

def astar(
    graph: dict,
    coords: dict,
    start: str,
    goal: str,
    transit_penalty: float = 5.0,   # [BARU] penalti (menit) saat ganti koridor
) -> dict:
    """
    Mencari rute tercepat dari start ke goal menggunakan A*.

    Args:
        graph           (dict) : Adjacency list {halte: [{to, time, corridor}]}.
        coords          (dict) : {halte: {lat, lon}}.
        start           (str)  : Nama halte asal.
        goal            (str)  : Nama halte tujuan.
        transit_penalty (float): Biaya tambahan (menit) saat berpindah koridor.
                                 Default 5 menit. Set 0 untuk menonaktifkan.

    Returns:
        dict:
            path          : list nama halte yang dilalui
            path_edges    : list {from, to, corridor, time} tiap segmen
            total_time    : total waktu tempuh (menit), sudah termasuk penalti transit
            nodes_visited : jumlah node yang dieksplorasi
            transit_count : jumlah perpindahan koridor yang terjadi

    Raises:
        ValueError  : Jika start atau goal tidak ada di graph.
        RuntimeError: Jika tidak ada rute yang bisa ditemukan.
    """
    if start not in graph:
        raise ValueError(f"Halte asal '{start}' tidak ditemukan dalam graph.")
    if goal not in graph:
        raise ValueError(f"Halte tujuan '{goal}' tidak ditemukan dalam graph.")

    counter  = 0
    open_set: list[tuple] = []
    heapq.heappush(open_set, (0.0, counter, start))

    g_score: dict[str, float] = {start: 0.0}

    # came_from menyimpan (node_sebelumnya, corridor, time_edge)
    came_from: dict[str, tuple | None] = {start: None}

    closed_set: set[str] = set()
    nodes_visited = 0

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current in closed_set:
            continue

        closed_set.add(current)
        nodes_visited += 1

        if current == goal:
            # Rekonstruksi path dan path_edges sekaligus
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
            }

        # Eksplorasi tetangga
        # Ambil koridor saat ini dari came_from agar tahu apakah ganti koridor
        current_meta    = came_from.get(current)
        current_corridor = current_meta[1] if current_meta else None

        for neighbor in graph.get(current, []):
            next_node  = neighbor["to"]
            edge_cost  = neighbor["time"]
            corridor   = neighbor.get("corridor", "")

            if next_node in closed_set:
                continue

            tentative_g = g_score[current] + edge_cost

            # [BARU] Tambahkan penalti jika koridor berubah
            if current_corridor is not None and corridor != current_corridor:
                tentative_g += transit_penalty

            if tentative_g < g_score.get(next_node, float("inf")):
                g_score[next_node]   = tentative_g
                came_from[next_node] = (current, corridor, edge_cost)
                f_score = tentative_g + heuristic(next_node, goal, coords)
                counter += 1
                heapq.heappush(open_set, (f_score, counter, next_node))

    raise RuntimeError(
        f"Tidak ditemukan rute dari '{start}' ke '{goal}'. "
        "Periksa koneksi antar halte di edges.json."
    )


# ---------------------------------------------------------------------------
# Helper: load graph dari file
# ---------------------------------------------------------------------------

def load_graph_from_file() -> tuple[dict, dict, dict]:
    """
    Memuat graph, coords, dan transit_map dari data/graph.json.

    Returns:
        tuple: (graph, coords, transit_map)
    """
    graph_path = os.path.join(DATA_DIR, "graph.json")
    if not os.path.exists(graph_path):
        raise FileNotFoundError(
            "File data/graph.json tidak ditemukan. "
            "Jalankan 'python graph_builder.py' terlebih dahulu."
        )
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["graph"], data["coords"], data.get("transit_map", {})