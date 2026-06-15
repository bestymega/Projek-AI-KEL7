import pandas as pd
import json

EXCEL_FILE = "data/BST.xlsx"
# =====================================
# SHEET 10 - WAKTU TEMPUH
# =====================================

edge_df = pd.read_excel(
    EXCEL_FILE,
    sheet_name="Sheet10"
)

edges = []

for _, row in edge_df.iterrows():

    if pd.isna(row["from"]):
        continue

    edges.append({
        "from": str(row["from"]).strip(),
        "to": str(row["to"]).strip(),
        "time": int(row["waktu"]),
        "corridor": str(row["koridor"]).strip()
    })

with open("data/edges.json", "w", encoding="utf-8") as f:
    json.dump(edges, f, indent=4, ensure_ascii=False)

print(f"Edges: {len(edges)}")

print("\nSelesai convert data!")