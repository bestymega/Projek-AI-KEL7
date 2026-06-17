"""
visualizer.py
Fungsi untuk menggambar graph BST per step A* menggunakan NetworkX + Matplotlib.

Warna node:
  Abu-abu  : belum dikunjungi
  Kuning   : open set
  Biru     : closed set
  Merah    : current node
  Hijau    : goal node
  Putih    : start node (dengan border biru)

Garis merah tebal : path sementara (path_so_far)
Garis hitam tipis : semua edge graph
"""

import math
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend untuk Streamlit
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from typing import Optional

# Warna
COLOR_UNVISITED = "#b0bec5"   # abu-abu
COLOR_OPEN      = "#fdd835"   # kuning
COLOR_CLOSED    = "#42a5f5"   # biru
COLOR_CURRENT   = "#e53935"   # merah
COLOR_GOAL      = "#43a047"   # hijau
COLOR_START     = "#ffffff"   # putih
COLOR_PATH_EDGE = "#e53935"   # merah tebal
COLOR_EDGE      = "#cfd8dc"   # abu-abu muda

LABEL_FONT_SIZE = 8
NODE_SIZE_NORMAL  = 240
NODE_SIZE_KEY     = 450


def build_networkx_graph(graph: dict, coords: dict) -> tuple[nx.DiGraph, dict]:
    """
    Membangun DiGraph NetworkX dan posisi tetap dari koordinat GPS.
    pos[node] = (longitude, latitude)
    """
    G = nx.DiGraph()

    for node in graph:
        G.add_node(node)

    for src, neighbors in graph.items():
        for nb in neighbors:
            G.add_edge(src, nb["to"], time=nb["time"], corridor=nb.get("corridor", ""))

    # Posisi tetap — pakai lon, lat
    pos = {}
    for node, c in coords.items():
        if node in G:
            pos[node] = (c["lon"], c["lat"])

    # Node tanpa koordinat → posisi default (0,0)
    for node in G.nodes():
        if node not in pos:
            pos[node] = (0.0, 0.0)

    return G, pos


def draw_step(
    G: nx.DiGraph,
    pos: dict,
    step_data: dict,
    start: str,
    goal: str,
    ax: Optional[plt.Axes] = None,
    show_labels: bool = True,
    label_nodes: Optional[list[str]] = None,
) -> plt.Figure:
    """
    Menggambar satu step A* pada axes yang diberikan (atau buat Figure baru).

    Args:
        G          : NetworkX graph
        pos        : dict posisi tetap node
        step_data  : snapshot satu step dari astar_with_steps()
        start/goal : nama node awal & tujuan
        ax         : plt.Axes opsional; jika None akan dibuat Figure baru
        show_labels: tampilkan label node
        label_nodes: jika diisi, hanya node ini yang dilabeli

    Returns:
        plt.Figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 7))
    else:
        fig = ax.get_figure()

    ax.clear()
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    current       = step_data["current"]
    open_nodes    = {item["node"] for item in step_data["open_set"]}
    closed_nodes  = set(step_data["closed_set"])
    path_so_far   = step_data["path_so_far"]
    goal_found    = step_data.get("goal_found", False)

    # ── Tentukan Node yang Aktif di Rute Ini ────────────────────
    active_nodes = {start, goal, current} | open_nodes | closed_nodes | set(path_so_far)
    active_nodes_list = list(active_nodes)

    # ── Warna node ──────────────────────────────────────────────
    node_colors  = []
    node_sizes   = []
    node_borders = []

    for node in active_nodes_list:
        if node == current:
            node_colors.append(COLOR_CURRENT)
            node_sizes.append(NODE_SIZE_KEY)
            node_borders.append(2.0)
        elif node == goal:
            node_colors.append(COLOR_GOAL)
            node_sizes.append(NODE_SIZE_KEY)
            node_borders.append(2.0)
        elif node == start:
            node_colors.append(COLOR_START)
            node_sizes.append(NODE_SIZE_KEY)
            node_borders.append(2.0)
        elif node in closed_nodes:
            node_colors.append(COLOR_CLOSED)
            node_sizes.append(NODE_SIZE_NORMAL)
            node_borders.append(0.5)
        elif node in open_nodes:
            node_colors.append(COLOR_OPEN)
            node_sizes.append(NODE_SIZE_NORMAL)
            node_borders.append(0.5)

    # ── Gambar edge yang menghubungkan node aktif (tipis, abu-abu) ──
    active_edges = [(u, v) for u, v in G.edges() if u in active_nodes and v in active_nodes]
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edgelist=active_edges,
        edge_color=COLOR_EDGE,
        alpha=0.25,
        arrows=False,
        width=0.4,
    )

    # ── Gambar path sementara (merah tebal) ────────────────────
    if len(path_so_far) > 1:
        path_edges = list(zip(path_so_far[:-1], path_so_far[1:]))
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edgelist=path_edges,
            edge_color=COLOR_PATH_EDGE,
            width=2.5,
            alpha=0.9,
            arrows=False,
        )

    # ── Gambar node aktif ─────────────────────────────────────────────
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=active_nodes_list,
        node_color=node_colors,
        node_size=node_sizes,
        linewidths=node_borders,
        edgecolors="#ffffff",
    )

    # ── Label ───────────────────────────────────────────────────
    if show_labels:
        # Tentukan node yang akan dilabeli
        key_nodes = {current, goal, start} | open_nodes | closed_nodes
        if label_nodes:
            key_nodes = set(label_nodes) & active_nodes

        label_dict = {n: _short_label(n) for n in active_nodes_list if n in key_nodes}
        
        # Offset posisi label sedikit ke atas (latitude + 0.0006) agar tidak menutupi node
        label_pos = {n: (x, y + 0.0006) for n, (x, y) in pos.items() if n in key_nodes}
        
        nx.draw_networkx_labels(
            G, label_pos, labels=label_dict, ax=ax,
            font_size=LABEL_FONT_SIZE,
            font_color="#ffffff",
            font_weight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="#1b1b2f", ec="none", alpha=0.75)
        )

    # ── Auto-zoom ke area aktif rute saja ───────────────────────────────
    x_coords = [pos[node][0] for node in active_nodes_list if node in pos]
    y_coords = [pos[node][1] for node in active_nodes_list if node in pos]
    if x_coords and y_coords:
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        # Margin 10% agar tidak terpotong di tepi canvas
        x_margin = (x_max - x_min) * 0.1 if x_max != x_min else 0.005
        y_margin = (y_max - y_min) * 0.1 if y_max != y_min else 0.005
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)

    # ── Judul ───────────────────────────────────────────────────
    status = "✅ GOAL DITEMUKAN!" if goal_found else f"Step {step_data['step']}"
    ax.set_title(
        f"{status}  |  Current: {_short_label(current)}",
        fontsize=9, color="#ffffff", pad=8,
        fontfamily="monospace",
    )

    # ── Legenda ─────────────────────────────────────────────────
    legend_items = [
        mpatches.Patch(color=COLOR_CURRENT,   label="Halte sedang diproses (Current)"),
        mpatches.Patch(color=COLOR_OPEN,      label="Halte tetangga (Open Set)"),
        mpatches.Patch(color=COLOR_CLOSED,    label="Halte yang sudah dikunjungi (Closed Set)"),
        mpatches.Patch(color=COLOR_GOAL,      label="Halte tujuan (Goal)"),
        mpatches.Patch(color=COLOR_START,     label="Halte start pertama (Start)"),
        mpatches.Patch(color=COLOR_PATH_EDGE, label="Rute sementara"),
    ]
    ax.legend(
        handles=legend_items,
        loc="lower left",
        fontsize=6,
        framealpha=0.7,
        facecolor="#0d0d1a",
        labelcolor="#ffffff",
        edgecolor="none",
    )

    ax.axis("off")
    plt.tight_layout(pad=0.5)
    return fig


def _short_label(name: str, max_len: int = 22) -> str:
    """Potong nama halte jika terlalu panjang."""
    name = name.title()
    return name if len(name) <= max_len else name[:max_len - 1] + "…"