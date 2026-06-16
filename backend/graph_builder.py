"""
graph_builder.py
Membaca edges.json, halts.json, dan transit.json,
lalu membentuk adjacency list graph yang siap digunakan oleh A*.
Hasil disimpan ke data/graph.json.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def normalize(name: str) -> str:
    """Normalisasi nama halte: strip spasi ganda & lowercase."""
    return " ".join(name.strip().split()).lower()


def load_json(filename: str) -> list | dict:
    """Membaca file JSON dari direktori data/."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_graph() -> tuple[dict, dict, dict]:
    """
    Membentuk adjacency list graph dari edges.json.
    Juga memuat transit.json untuk info halte transit antar koridor.

    Returns:
        tuple: (graph, coords, transit_map)
            - graph      : adjacency list {halte: [{to, time, corridor}]}
            - coords     : {halte: {lat, lon}}
            - transit_map: {halte: [koridor1, koridor2, ...]} — hanya halte transit (>1 koridor)
    """
    edges  = load_json("edges.json")
    halts  = load_json("halts.json")
    transit = load_json("transit.json")

    # Koordinat halte — key dinormalisasi
    coords: dict[str, dict] = {
        normalize(h["name"]): {"lat": h["lat"], "lon": h["lon"]}
        for h in halts
    }

    # Inisialisasi graph kosong
    graph: dict[str, list] = {normalize(h["name"]): [] for h in halts}

    # Isi adjacency list dari edges
    for edge in edges:
        src      = normalize(edge["from"])
        dst      = normalize(edge["to"])
        waktu     = edge["waktu"]
        koridor = edge.get("koridor", "")

        if src not in graph:
            graph[src] = []
        if dst not in graph:
            graph[dst] = []

        graph[src].append({"to": dst, "time": waktu, "corridor": koridor})

    # Bangun transit_map dari transit.json
    # {halte: set(koridor)} dulu, lalu filter yang punya >1 koridor
    raw_transit: dict[str, set] = {}
    for item in transit:
        halte   = normalize(item["halte"])
        koridor = item["koridor"]
        raw_transit.setdefault(halte, set()).add(koridor)

    transit_map: dict[str, list] = {
        halte: sorted(kors)
        for halte, kors in raw_transit.items()
        if len(kors) > 1
    }

    return graph, coords, transit_map


def save_graph(graph: dict, coords: dict, transit_map: dict) -> None:
    """Menyimpan graph, coords, dan transit_map ke data/graph.json."""
    output = {
        "graph"      : graph,
        "coords"     : coords,
        "transit_map": transit_map
    }
    output_path = os.path.join(DATA_DIR, "graph.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[graph_builder] Disimpan ke      : {output_path}")
    print(f"[graph_builder] Total halte      : {len(graph)}")
    print(f"[graph_builder] Total edge       : {sum(len(v) for v in graph.values())}")
    print(f"[graph_builder] Total halte transit: {len(transit_map)}")


if __name__ == "__main__":
    graph, coords, transit_map = build_graph()
    save_graph(graph, coords, transit_map)