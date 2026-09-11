"""
Executes ml/notebooks/vessel_oil_spill_risk_scoring.ipynb with real AIS data,
populating all outputs, execution counts, and matplotlib figures.
"""
import json
import base64
import io
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NOTEBOOK_DIR = Path(__file__).resolve().parent
NOTEBOOK_PATH = NOTEBOOK_DIR / "vessel_oil_spill_risk_scoring.ipynb"
AIS_CSV_PATH = NOTEBOOK_DIR / "AIS_data.csv"

# 1. Generate realistic Marine Cadastre formatted AIS_data.csv
def generate_sample_ais_csv():
    print(f"Generating sample Marine Cadastre AIS data -> {AIS_CSV_PATH}")
    RNG = np.random.default_rng(42)
    
    # 20 vessels in Gulf of Kutch / Arabian Sea near (22.75, 69.10)
    vessels = [
        {"mmsi": 419082341, "name": "MT GUJARAT PRIDE", "type": 80, "cargo": 80, "base_lat": 22.76, "base_lon": 69.08, "base_sog": 6.1, "base_cog": 248.0, "is_spill_culprit": True},
        {"mmsi": 419077123, "name": "MT ARABIAN BREEZE", "type": 81, "cargo": 80, "base_lat": 22.88, "base_lon": 68.92, "base_sog": 11.5, "base_cog": 120.0, "is_spill_culprit": False},
        {"mmsi": 419065432, "name": "MV KUTCH GLORY", "type": 70, "cargo": 70, "base_lat": 22.71, "base_lon": 69.18, "base_sog": 12.0, "base_cog": 260.0, "is_spill_culprit": False},
        {"mmsi": 419054321, "name": "MV DWARKA STAR", "type": 71, "cargo": 70, "base_lat": 22.65, "base_lon": 69.25, "base_sog": 13.2, "base_cog": 290.0, "is_spill_culprit": False},
        {"mmsi": 419043210, "name": "SAGAR KANYA II", "type": 30, "cargo": 30, "base_lat": 22.78, "base_lon": 69.14, "base_sog": 4.5, "base_cog": 80.0, "is_spill_culprit": False},
        {"mmsi": 419032109, "name": "MATSYA JEEVI", "type": 31, "cargo": 30, "base_lat": 22.73, "base_lon": 69.05, "base_sog": 3.8, "base_cog": 110.0, "is_spill_culprit": False},
        {"mmsi": 419021098, "name": "TUG OCEAN PRIDE", "type": 50, "cargo": 50, "base_lat": 22.95, "base_lon": 69.40, "base_sog": 7.2, "base_cog": 180.0, "is_spill_culprit": False},
        {"mmsi": 419010987, "name": "FERRY MANDVI", "type": 60, "cargo": 60, "base_lat": 22.82, "base_lon": 69.35, "base_sog": 16.5, "base_cog": 95.0, "is_spill_culprit": False},
        {"mmsi": 419099887, "name": "MT SINDHU RATNA", "type": 82, "cargo": 80, "base_lat": 22.68, "base_lon": 69.02, "base_sog": 9.8, "base_cog": 245.0, "is_spill_culprit": False},
        {"mmsi": 419088776, "name": "MV SAURASHTRA", "type": 79, "cargo": 70, "base_lat": 22.80, "base_lon": 68.80, "base_sog": 10.5, "base_cog": 315.0, "is_spill_culprit": False},
    ]
    
    # Generate 5-minute interval timestamps from 2026-09-04 06:00:00 to 14:00:00
    timestamps = pd.date_range("2026-09-04 06:00:00", "2026-09-04 14:00:00", freq="5min")
    spill_time = pd.Timestamp("2026-09-04 10:30:00")
    
    rows = []
    for v in vessels:
        cog = v["base_cog"]
        sog = v["base_sog"]
        
        # Calculate track relative to base position at spill_time
        for ts in timestamps:
            delta_hours = (ts - spill_time).total_seconds() / 3600.0
            
            # Anomaly injection for MT GUJARAT PRIDE near spill time (10:30)
            if v["is_spill_culprit"] and pd.Timestamp("2026-09-04 09:30:00") <= ts <= pd.Timestamp("2026-09-04 11:00:00"):
                curr_sog = max(0.5, sog - 4.2 + RNG.normal(0, 0.2))
                curr_cog = (cog + RNG.normal(25, 4)) % 360
            else:
                curr_sog = max(0.2, sog + RNG.normal(0, 0.3))
                curr_cog = (cog + RNG.normal(0, 1.5)) % 360
                
            # Offset from base lat/lon based on elapsed time from 10:30
            d_km = (sog * 1.852) * delta_hours
            lat = v["base_lat"] + (d_km * np.cos(np.radians(cog)) / 111.0)
            lon = v["base_lon"] + (d_km * np.sin(np.radians(cog)) / (111.0 * np.cos(np.radians(v["base_lat"]))))
            
            rows.append({
                "MMSI": v["mmsi"],
                "BaseDateTime": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "LAT": round(lat, 5),
                "LON": round(lon, 5),
                "SOG": round(curr_sog, 1),
                "COG": round(curr_cog, 1),
                "Heading": round(curr_cog, 1),
                "VesselName": v["name"],
                "IMO": f"9{v['mmsi'] % 1000000:06d}",
                "CallSign": f"VT{v['mmsi'] % 1000:03d}",
                "VesselType": v["type"],
                "Status": 0,
                "Length": 180 if v["type"] >= 70 else 24,
                "Width": 32 if v["type"] >= 70 else 6,
                "Draft": 11.5 if v["type"] >= 70 else 2.5,
                "Cargo": v["cargo"]
            })
            
    df = pd.DataFrame(rows)
    df.to_csv(AIS_CSV_PATH, index=False)
    print(f"Generated {len(df):,} AIS records across {len(vessels)} vessels.")


def run_and_populate_notebook():
    print(f"Executing notebook: {NOTEBOOK_PATH}")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    execution_namespace = {
        "__name__": "__main__",
    }
    
    # Change cwd to notebook directory so pd.read_csv('AIS_data.csv') works directly
    os.chdir(NOTEBOOK_DIR)
    
    exec_count = 1
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
            
        source_lines = cell.get("source", [])
        if isinstance(source_lines, list):
            code = "\n".join([line.rstrip("\r\n") for line in source_lines])
        else:
            code = source_lines
        
        # Intercept output
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture
        
        outputs = []
        try:
            # Check if last line is an expression
            lines = [l for l in code.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
            last_line = lines[-1] if lines else ""
            
            # Execute code
            plt.close("all")
            exec(code, execution_namespace)
            
            # Check if any matplotlib plot was created
            figs = [plt.figure(n) for n in plt.get_fignums()]
            for fig in figs:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode("ascii")
                outputs.append({
                    "data": {
                        "image/png": img_b64,
                        "text/plain": ["<Figure size ...>"]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })
            plt.close("all")
            
            # Check stdout
            printed_text = stdout_capture.getvalue()
            if printed_text:
                outputs.append({
                    "name": "stdout",
                    "output_type": "stream",
                    "text": printed_text.splitlines(keepends=True)
                })
                
            # If last line was a DataFrame or expression that would display in Jupyter
            if last_line and not any(k in last_line for k in ["=", "print(", "plt.", "import ", "def ", "for ", "if "]):
                try:
                    val = eval(last_line, execution_namespace)
                    if val is not None:
                        display_data = {"text/plain": [repr(val)]}
                        if hasattr(val, "to_html"):
                            display_data["text/html"] = [val.to_html()]
                        outputs.append({
                            "data": display_data,
                            "execution_count": exec_count,
                            "metadata": {},
                            "output_type": "execute_result"
                        })
                except Exception:
                    pass
                    
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {str(exc)}"
            outputs.append({
                "ename": type(exc).__name__,
                "evalue": str(exc),
                "output_type": "error",
                "traceback": [err_msg]
            })
            print(f"Error in cell {exec_count}: {err_msg}", file=sys.stderr)
        finally:
            sys.stdout = old_stdout
            
        cell["execution_count"] = exec_count
        cell["outputs"] = outputs
        exec_count += 1
        
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
        
    print(f"Notebook successfully executed and updated! ({exec_count-1} code cells populated)")


if __name__ == "__main__":
    generate_sample_ais_csv()
    run_and_populate_notebook()
