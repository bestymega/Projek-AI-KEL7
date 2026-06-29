"""
streamlit_app.py
Halaman Streamlit untuk visualisasi proses A* step-by-step pada rute BST.

Cara menjalankan:
    streamlit run streamlit_app.py
"""

import time
import streamlit as st
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from astar_steps import astar_with_steps, load_graph_from_file
from visualizer import build_networkx_graph, draw_step, _short_label

# ─────────────────────────────────────────────────────────────────────────────
# Konfigurasi halaman
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BST A* Visualizer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load FontAwesome Icons CDN
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />', unsafe_allow_html=True)

# CSS kustom agar tampilan lebih rapi
st.markdown("""
<style>
    .block-container { padding-top: 4.5rem; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
    }
    .summary-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,.05);
    }
    .summary-card .s-icon {
        font-size: 20px;
        color: #1a56db;
        margin-bottom: 6px;
    }
    .summary-card .s-label {
        font-size: 10px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: .5px;
        font-weight: 500;
    }
    .summary-card .s-value {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 3px;
    }
    .step-info-table { font-size: 12px; }
    .highlight-row { background: #fff3cd; font-weight: bold; }
    .timeline-item { padding: 4px 8px; border-radius: 6px; margin: 2px 0; font-size: 12px; }
    .timeline-active { background: #fff3cd; border-left: 3px solid #f59e0b; font-weight: bold; }
    .timeline-done   { background: #e8f5e9; border-left: 3px solid #43a047; color: #555; }
    .timeline-future { color: #aaa; padding-left: 11px; }
    .goal-banner {
        background: linear-gradient(135deg, #43a047, #1b5e20);
        color: white;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Load data (cache agar tidak reload setiap interaksi)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Memuat graph BST…")
def load_data():
    graph, coords, transit_map = load_graph_from_file()
    G, pos = build_networkx_graph(graph, coords)
    haltes_sorted = sorted(graph.keys())
    return graph, coords, transit_map, G, pos, haltes_sorted


graph, coords, transit_map, G, pos, haltes_sorted = load_data()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — input & kontrol
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
        <div style="width: 40px; height: 40px; background: #0f2d5e; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff;">
            <i class="fa-solid fa-bus"></i>
        </div>
        <div>
            <div style="font-size: 14px; font-weight: 700; color: #0f2d5e; line-height: 1.2;">Optimasi Rute<br>Batik Solo Trans</div>
            <div style="font-size: 10px; color: #6b7280; margin-top: 2px;">Pencarian Rute Optimal · Algoritma A*</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Pilih halte
    def fmt(h): return h.title()

    def clear_result():
        st.session_state.result = None
        st.session_state.current_step = 0
        st.session_state.playing = False

    st.markdown('<div style="font-size:11px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;"><i class="fa-solid fa-location-crosshairs" style="color:#1a56db; font-size:13px; margin-right:4px;"></i> Halte Asal</div>', unsafe_allow_html=True)
    start_halte = st.selectbox(
        "Halte Asal",
        options=haltes_sorted,
        format_func=fmt,
        index=None,
        placeholder="Pilih halte asal...",
        label_visibility="collapsed",
        on_change=clear_result
    )
    
    st.markdown('<div style="font-size:11px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; margin-top:10px;"><i class="fa-solid fa-location-dot" style="color:#dc2626; font-size:13px; margin-right:4px;"></i> Halte Tujuan</div>', unsafe_allow_html=True)
    goal_halte = st.selectbox(
        "Halte Tujuan",
        options=haltes_sorted,
        format_func=fmt,
        index=None,
        placeholder="Pilih halte tujuan...",
        label_visibility="collapsed",
        on_change=clear_result
    )

    cari_btn = st.button("Cari Rute & Visualisasi", type="primary")
    st.divider()

    # Opsi tampilan
    st.markdown('<div style="font-size:14px; font-weight:600; margin-bottom:10px;"><i class="fa-solid fa-gear" style="margin-right:6px;"></i> Opsi Tampilan</div>', unsafe_allow_html=True)
    show_labels = st.checkbox("Tampilkan label node", value=True)
    play_speed  = st.slider("Kecepatan (detik/step)", 0.1, 2.0, 0.5, 0.1)

    st.divider()
    st.caption(f"Total halte: **{len(graph)}**")
    st.caption(f"Total halte transit: **{len(transit_map)}**")


# ─────────────────────────────────────────────────────────────────────────────
# State management
# ─────────────────────────────────────────────────────────────────────────────

if "result"       not in st.session_state: st.session_state.result       = None
if "current_step" not in st.session_state: st.session_state.current_step = 0
if "playing"      not in st.session_state: st.session_state.playing      = False


# ─────────────────────────────────────────────────────────────────────────────
# Jalankan A* saat tombol ditekan
# ─────────────────────────────────────────────────────────────────────────────

if cari_btn:
    if start_halte is None or goal_halte is None:
        st.warning("Silakan pilih halte asal dan halte tujuan terlebih dahulu.")
    elif start_halte == goal_halte:
        st.warning("Halte asal dan tujuan tidak boleh sama.")
    else:
        with st.spinner("Menjalankan A*…"):
            try:
                result = astar_with_steps(graph, coords, start_halte, goal_halte)
                result["start"] = start_halte
                result["goal"] = goal_halte
                st.session_state.result       = result
                st.session_state.current_step = 0
                st.session_state.playing      = False
            except (ValueError, RuntimeError) as e:
                st.error(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Tampilan utama
# ─────────────────────────────────────────────────────────────────────────────

result = st.session_state.result

if result is None:
    st.markdown('## Selamat datang di BST A\* Visualizer', unsafe_allow_html=True)
    st.info("Pilih halte asal dan tujuan di sidebar, lalu klik **Cari Rute & Visualisasi**.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **<i class="fa-solid fa-circle" style="color: #3b82f6;"></i> Open Set**  
        Node yang sudah dideteksi tapi belum diekspansi
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        **<i class="fa-solid fa-circle" style="color: #eab308;"></i> Current**  
        Node yang sedang diproses A* pada step ini
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        **<i class="fa-solid fa-circle" style="color: #22c55e;"></i> Closed Set**  
        Node yang sudah selesai diekspansi
        """, unsafe_allow_html=True)

else:
    if st.button("Kembali ke Awal", icon=":material/arrow_back:"):
        st.session_state.result = None
        st.session_state.current_step = 0
        st.session_state.playing = False
        st.rerun()

    steps       = result["steps"]
    total_steps = len(steps)
    path        = result["path"]
    path_edges  = result["path_edges"]

    # ── Banner goal jika sudah selesai ──────────────────────────────────────
    if st.session_state.current_step == total_steps - 1 and steps[-1]["goal_found"]:
        st.markdown(f"""
        <div class="goal-banner">
            <i class="fa-solid fa-circle-check"></i> Goal Ditemukan! &nbsp;·&nbsp; {len(path)} halte &nbsp;·&nbsp; {result['total_time']} menit
        </div>
        """, unsafe_allow_html=True)

    # ── Summary metrics ──────────────────────────────────────────────────────
    corridors_used = list(dict.fromkeys(e["corridor"] for e in path_edges))
    transit_count  = sum(
        1 for i in range(1, len(path_edges))
        if path_edges[i]["corridor"] != path_edges[i-1]["corridor"]
    )

    st.markdown(f"""
    <div class="summary-grid">
        <div class="summary-card">
            <div class="s-icon"><i class="fa-regular fa-clock"></i></div>
            <div class="s-label">Waktu</div>
            <div class="s-value">{result['total_time']} mnt</div>
        </div>
        <div class="summary-card">
            <div class="s-icon"><i class="fa-solid fa-map-pin"></i></div>
            <div class="s-label">Halte</div>
            <div class="s-value">{len(path)}</div>
        </div>
        <div class="summary-card">
            <div class="s-icon"><i class="fa-solid fa-shuffle"></i></div>
            <div class="s-label">Transit</div>
            <div class="s-value">{transit_count}</div>
        </div>
        <div class="summary-card">
            <div class="s-icon"><i class="fa-solid fa-shoe-prints"></i></div>
            <div class="s-label">Total Step A*</div>
            <div class="s-value">{total_steps}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Kontrol step ────────────────────────────────────────────────────────
    # Penyempurnaan proporsi UI reponsiveness
    ctrl_cols = st.columns([1, 1, 1, 1, 1.2, 1.2])
    is_playing = st.session_state.playing

    with ctrl_cols[0]:
        if st.button("⏮ Reset", disabled=is_playing):
            st.session_state.current_step = 0

    with ctrl_cols[1]:
        if st.button("◀ Prev", disabled=is_playing):
            st.session_state.current_step = max(0, st.session_state.current_step - 1)

    with ctrl_cols[2]:
        if st.button("▶ Next", disabled=is_playing):
            st.session_state.current_step = min(total_steps - 1, st.session_state.current_step + 1)

    with ctrl_cols[3]:
        if st.button("⏭ Akhir", disabled=is_playing):
            st.session_state.current_step = total_steps - 1

    with ctrl_cols[4]:
        if st.button("▶▶ Play"):
            if is_playing:
                # Menambah alert peringatan interaktif jika Play ditekan berulang kali
                st.toast("⚠️ Peringatan: Simulasi sedang berjalan! Jangan tekan tombol Play berulang kali untuk mencegah error.", icon="⚠️")
            elif st.session_state.current_step >= total_steps - 1:
                st.toast("ℹ️ Simulasi sudah berada di akhir step. Silakan tekan Reset.", icon="ℹ️")
            else:
                st.session_state.playing = True
                st.rerun()

    with ctrl_cols[5]:
        if st.button("⏸ Pause", disabled=not is_playing):
            st.session_state.playing = False
            st.rerun()

    # Slider
    selected = st.slider(
        f"Step (1 – {total_steps})",
        min_value=1,
        max_value=total_steps,
        value=st.session_state.current_step + 1,
        key="step_slider",
        disabled=is_playing
    )
    if selected - 1 != st.session_state.current_step:
        st.session_state.current_step = selected - 1
        st.session_state.playing      = False

    st.divider()

    step_idx  = st.session_state.current_step
    step_data = steps[step_idx]

    # ── Layout utama: graph kiri | info kanan ───────────────────────────────
    col_graph, col_info = st.columns([3, 2])

    # ── Gambar graph ────────────────────────────────────────────────────────
    with col_graph:
        st.markdown(f'#### <i class="fa-solid fa-earth-asia"></i> Graph — Step {step_idx + 1} / {total_steps}', unsafe_allow_html=True)

        # Hanya render node yang relevan agar cepat
        # Agar tidak bertumpuk, kita batasi label hanya untuk start, goal, dan current node
        label_nodes = None
        used_start = result.get("start", start_halte)
        used_goal = result.get("goal", goal_halte)
        
        show_all_labels = st.checkbox("Tampilkan Nama Semua Halte Aktif", value=False, help="Centang untuk melihat nama seluruh halte di rute saat ini (bisa sedikit berantakan)")
        
        if show_labels:
            if show_all_labels:
                label_nodes = None
            else:
                label_nodes = list({step_data["current"], used_start, used_goal})

        fig = draw_step(
            G, pos, step_data,
            start=used_start,
            goal=used_goal,
            show_labels=show_labels,
            label_nodes=label_nodes,
        )
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # ── Panel info step ──────────────────────────────────────────────────────
    with col_info:
        st.markdown(f'#### <i class="fa-solid fa-clipboard-list" style="color:#d97706;"></i> Info Step {step_idx + 1}', unsafe_allow_html=True)

        current = step_data["current"]
        g_val   = step_data["g_score"].get(current, 0)
        h_val   = step_data["h_score"].get(current, 0)
        f_val   = step_data["f_score"].get(current, 0)
        parent  = step_data["parent"].get(current, "–") or "– (start)"

        # Tabel nilai A*
        st.markdown("**Nilai A\\* untuk current node:**")
        st.table({
            "Parameter": ["Current Node", "Parent", "g(n)", "h(n)", "f(n)"],
            "Nilai"    : [
                _short_label(current),
                _short_label(str(parent)) if parent else "–",
                f"{g_val:.2f} mnt",
                f"{h_val:.2f} mnt",
                f"{f_val:.2f} mnt",
            ],
        })

        # Open set
        with st.expander(f"Open Set ({len(step_data['open_set'])} node)", expanded=False):
            if step_data["open_set"]:
                open_data = sorted(step_data["open_set"], key=lambda x: x["f"])
                st.dataframe(
                    [{"Halte": _short_label(i["node"]), "f(n)": i["f"]} for i in open_data],
                    use_container_width=True,
                    height=180,
                )
            else:
                st.caption("Open set kosong.")

        # Closed set
        with st.expander(f"Closed Set ({len(step_data['closed_set'])} node)", expanded=False):
            if step_data["closed_set"]:
                st.write(", ".join(_short_label(n) for n in sorted(step_data["closed_set"])))
            else:
                st.caption("Closed set kosong.")

        # Neighbors added
        with st.expander(f"Tetangga Ditambahkan ({len(step_data['neighbors_added'])})", expanded=False):
            if step_data["neighbors_added"]:
                for nb in step_data["neighbors_added"]:
                    g_nb = step_data["g_score"].get(nb, "?")
                    h_nb = step_data["h_score"].get(nb, "?")
                    f_nb = step_data["f_score"].get(nb, "?")
                    st.caption(f"• {_short_label(nb)} — g={g_nb}, h={h_nb}, f={f_nb}")
            else:
                st.caption("Tidak ada tetangga baru.")

        # Path sementara
        st.markdown('**<i class="fa-solid fa-road"></i> Path Sementara:**', unsafe_allow_html=True)
        path_sf = step_data["path_so_far"]
        path_str = " → ".join(_short_label(n) for n in path_sf)
        st.code(path_str, language=None)

    # ── Timeline ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown('#### <i class="fa-solid fa-map-pin" style="color: #ec4899;"></i> Timeline Langkah A*', unsafe_allow_html=True)

    # Tampilkan window ±5 step dari current agar tidak terlalu panjang
    win_start = max(0, step_idx - 5)
    win_end   = min(total_steps, step_idx + 6)

    timeline_html = ""
    if win_start > 0:
        timeline_html += f'<div class="timeline-item timeline-future">… {win_start} step sebelumnya</div>'

    for i in range(win_start, win_end):
        s    = steps[i]
        name = _short_label(s["current"])
        label = "Goal ditemukan!" if s["goal_found"] else f"Ekspansi: {name}"
        if i == step_idx:
            timeline_html += f'<div class="timeline-item timeline-active">➤ Step {i+1} · {label}</div>'
        elif i < step_idx:
            timeline_html += f'<div class="timeline-item timeline-done">✓ Step {i+1} · {label}</div>'
        else:
            timeline_html += f'<div class="timeline-item timeline-future">○ Step {i+1} · {label}</div>'

    if win_end < total_steps:
        timeline_html += f'<div class="timeline-item timeline-future">… {total_steps - win_end} step berikutnya</div>'

    st.markdown(timeline_html, unsafe_allow_html=True)

    if steps[step_idx]["goal_found"]:
        st.markdown(f'### GOAL DITEMUKAN!', unsafe_allow_html=True)

    # ── Rute optimal (tampil setelah goal ditemukan) ─────────────────────────
    if step_idx == total_steps - 1 and steps[-1]["goal_found"]:
        st.divider()
        st.markdown('#### <i class="fa-solid fa-trophy" style="color: #eab308;"></i> Rute Optimal', unsafe_allow_html=True)

        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            route_text = "\n↓\n".join(_short_label(h) for h in path)
            st.code(route_text, language=None)
        with col_r2:
            st.metric("Waktu Tempuh", f"{result['total_time']} menit")
            st.metric("Jumlah Halte", len(path))
            st.metric("Jumlah Transit", transit_count)
            st.metric("Koridor", ", ".join(corridors_used))

    # ── Auto-play ────────────────────────────────────────────────────────────
    if st.session_state.playing:
        if step_idx < total_steps - 1:
            time.sleep(play_speed)
            st.session_state.current_step += 1
            st.rerun()
        else:
            st.session_state.playing = False
            st.rerun()