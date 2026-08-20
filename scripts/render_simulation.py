"""Injects reports/simulation_log.json into scripts/simulation_template.html
and writes reports/simulation_engine.html. Re-run this after editing the
template or regenerating the simulation log -- never hand-edit the output
file directly, it's 500KB+ with embedded data.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
TEMPLATE = os.path.join(os.path.dirname(__file__), "simulation_template.html")
DATA = os.path.join(ROOT, "reports", "simulation_log.json")
OUT = os.path.join(ROOT, "reports", "simulation_engine.html")


def main():
    data = json.load(open(DATA))
    html = open(TEMPLATE).read()
    html = html.replace("__DATA_JSON__", json.dumps(data))
    with open(OUT, "w") as f:
        f.write(html)
    print(f"wrote {OUT} ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
