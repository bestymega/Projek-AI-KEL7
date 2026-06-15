import json
from pathlib import Path

base = Path(__file__).resolve().parent
with open(base / "data" / "edges.json", encoding="utf-8") as f:
    edges = json.load(f)
with open(base / "data" / "halts.json", encoding="utf-8") as f:
    halts = json.load(f)

halt_names = {h["name"] for h in halts}
edge_froms = {e["from"] for e in edges}
edge_tos = {e["to"] for e in edges}

print("=== Nama di edges.json tapi TIDAK ADA di halts.json ===")
missing = (edge_froms | edge_tos) - halt_names
for n in sorted(missing):
    print(f"  {repr(n)}")

print()
print("=== Edge yang FROM-nya 'Terminal Palur' (atau mirip) ===")
for e in edges:
    if "palur" in e["from"].lower() or "palur" in e["to"].lower():
        print(f"  {repr(e['from'])} → {repr(e['to'])}")
