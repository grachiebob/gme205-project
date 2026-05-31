import os
import json
import geopandas as gpd
import folium
import pyproj
from spatial import (Dormitory,HealthcareFacility)
from RoadNetwork import RoadNetwork
from ODCostMatrix import ODCostMatrix
from TwoStepFCA import TwoStepFCA

GEOJSON_DIR = r"C:\Users\Gracie\Documents\Acads\GmE 205\Project\gme205-project\data"
OUTPUT_DIR  = r"C:\Users\Gracie\Documents\Acads\GmE 205\Project\gme205-project\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DORM_FILE = os.path.join(GEOJSON_DIR, "Dorm.geojson")
HCF_FILE  = os.path.join(GEOJSON_DIR, "HCF.geojson")
ROAD_FILE = os.path.join(GEOJSON_DIR, "Roads.geojson")

_PROJ = pyproj.Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)

def to_wgs84(x, y):
    """
    Convert EPSG:32651 metres to WGS84 for Folium
    """
    lon, lat = _PROJ.transform(x, y)
    return lat, lon

print(f"[RoadNetwork] Loading {ROAD_FILE} ...")
road_network = RoadNetwork()
road_network.load(ROAD_FILE)

print(
    f"[RoadNetwork] "
    f"{road_network.road_count:,} "
    f"drivable road segments"
)

print("\nGeometry Types:")

for geom, count in (
    road_network.geometry_types.items()
):
    print(f"{geom}: {count:,}")

print(
    f"[RoadNetwork] Graph built: "
    f"{road_network.graph.number_of_nodes():,} nodes, "
    f"{road_network.graph.number_of_edges():,} edges."
)

def _time_color(minutes:float) -> str:

    if minutes is None:
        return "#888888"
    if minutes <= 3:   return "#1a9641"
    if minutes <= 5:   return "#52b347"
    if minutes <= 8:   return "#a8d96c"
    if minutes <= 11:  return "#fdae61"
    return                    "#d7191c"

def _ai_color(ai: float, vmin: float, vmax: float) -> str:
    if vmax == vmin:
        return "#3399ff"
    t = (ai - vmin) / (vmax - vmin)
    if t <= 0.5:
        t2 = t / 0.5
        r = int(217 + (255 - 217) * t2)
        g = int(25  + (255 - 25)  * t2)
        b = int(28  + (191 - 28)  * t2)
    else:
        t2 = (t - 0.5) / 0.5
        r = int(255 + (26  - 255) * t2)
        g = int(255 + (150 - 255) * t2)
        b = int(191 + (65  - 191) * t2)
    return f"#{r:02x}{g:02x}{b:02x}"

def build_closest_facility_map(
    dormitories,
    facilities,
    fca,
    output_path
):
    """
    Build and save an interactive Folium map showing: Healthcare Facilities, Closest-Facility Line, All OD Connections,Dormitory Markers, Accessibility Choropleth
    """
    all_x = [e.x for e in dormitories + facilities]
    all_y = [e.y for e in dormitories + facilities]
    centre_lat, centre_lon = to_wgs84(
        sum(all_x) / len(all_x),
        sum(all_y) / len(all_y),
    )

    fmap = folium.Map(location=[centre_lat, centre_lon], zoom_start=14)
    folium.TileLayer("CartoDB positron",
                     name="CartoDB Positron",
                     attr="© OpenStreetMap contributors © CARTO").add_to(fmap)
    folium.TileLayer("OpenStreetMap",
                     name="OpenStreetMap",
                     attr="© OpenStreetMap contributors").add_to(fmap) #different basemaps

    # Pre-compute WGS84 coords for every entity
    dorm_wgs  = {d.name: to_wgs84(d.x, d.y) for d in dormitories}
    hcf_wgs   = {h.name: to_wgs84(h.x, h.y) for h in facilities}

    ai_vals   = [d.accessibility_index for d in dormitories]
    ai_min, ai_max = min(ai_vals), max(ai_vals)

    # Healthcare Facilities
    fg_hcf = folium.FeatureGroup(name="Healthcare Facilities", show=True)
    for hcf in facilities:
        lat, lon = hcf_wgs[hcf.name]
        rj       = fca.supply_ratios.get(hcf.name, 0.0)
        popup_html = f"""
        <div style="font-family:Arial;min-width:230px">
          <h4 style="margin:4px 0;color:#1a5276">🏥 {hcf.name}</h4>
          <hr style="margin:4px 0">
          <b>Fac ID   :</b> {hcf.fac_id}<br>
          <b>Address  :</b> {hcf.address}<br>
          <b>Beds (Sⱼ):</b> {hcf.bed_capacity:,}<br>
          <b>Catchment:</b> {hcf.catchment_population:,} people<br>
          <b>Rⱼ       :</b> {rj * 1_000:.4f} beds / 1 000
        </div>"""
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"🏥 {hcf.name}  |  {hcf.bed_capacity} beds",
            icon=folium.Icon(icon="plus-sign", prefix="glyphicon", color="blue"),
        ).add_to(fg_hcf)
    fg_hcf.add_to(fmap)

    # Closest-Facility Lines
    fg_lines = folium.FeatureGroup(name="Closest-Facility Lines", show=True)
    for dorm in dormitories:
        if dorm.closest_facility is None:
            continue
        dlat, dlon = dorm_wgs[dorm.name]
        hlat, hlon = hcf_wgs[dorm.closest_facility.name]
        t = dorm.closest_time_min
        folium.PolyLine(
            locations=[[dlat, dlon], [hlat, hlon]],
            color=_time_color(t),
            weight= 3.5,
            opacity=0.85,
            tooltip=(
                f"{dorm.name}  →  {dorm.closest_facility.name}  |  "
                f"{t:.2f} min"
            ),
        ).add_to(fg_lines)
    fg_lines.add_to(fmap)

    # OD Connections (≤15 min)
    fg_od = folium.FeatureGroup(name="All OD Connections (≤15 min)", show=False)
    for dorm in dormitories:
        dlat, dlon = dorm_wgs[dorm.name]
        for hcf_name, t in dorm.travel_times.items():
            if hcf_name in hcf_wgs:
                hlat, hlon = hcf_wgs[hcf_name]
                folium.PolyLine(
                    locations=[[dlat, dlon], [hlat, hlon]],
                    color=_time_color(t),
                    weight=2,
                    opacity=0.35,
                    tooltip=f"{dorm.name} → {hcf_name}  |  {t:.2f} min",
                ).add_to(fg_od)
    fg_od.add_to(fmap)

    # DOrmitory
    fg_dorm = folium.FeatureGroup(name="Dormitories (closest HCF travel time)", show=True)
    for dorm in dormitories:
        lat, lon = dorm_wgs[dorm.name]
        t        = dorm.closest_time_min
        color    = _time_color(t)
        cf_name  = dorm.closest_facility.name if dorm.closest_facility else "—"

        reachable_rows = "".join(
            f"<tr><td>{fn}</td><td style='text-align:right'>{tv:.2f} min</td></tr>"
            for fn, tv in sorted(dorm.travel_times.items(), key=lambda kv: kv[1])
        )
        popup_html = f"""
        <div style="font-family:Arial;min-width:270px">
          <h4 style="margin:4px 0;color:#1a5276">🏠 {dorm.name}</h4>
          <hr style="margin:4px 0">
          <b>Dorm ID      :</b> {dorm.dorm_id}<br>
          <b>Population   :</b> {dorm.population:,}<br>
          <b>Closest HCF  :</b> {cf_name}<br>
          <b>Travel time  :</b> {t:.2f} min<br>
          <b>Aᵢ  (2SFCA) :</b> {dorm.accessibility_index:.6f} beds/1 000<br>
          <b>SUM_Servic   :</b> {dorm.sum_service:.6f}<br>
          <b>Reachable ({len(dorm.travel_times)}):</b>
          <table style="font-size:11px;width:100%;margin-top:4px">
            <tr><th style="text-align:left">Facility</th>
                <th style="text-align:right">Time</th></tr>
            {reachable_rows}
          </table>
        </div>"""
        folium.CircleMarker(
            location=[lat, lon],
            radius=10,
            color="#222",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.88,
            popup=folium.Popup(popup_html, max_width=310),
            tooltip=f"🏠 {dorm.name} | Pop: {dorm.population:,} | Aᵢ: {dorm.accessibility_index:.2f}"
        ).add_to(fg_dorm)

        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=(
                    f"<div style='font-size:9px;font-weight:bold;"
                    f"color:#111;white-space:nowrap;"
                    f"text-shadow:1px 1px 2px white;margin-top:12px'>"
                    f"{dorm.name.split()[0]}</div>"
                ),
                icon_size=(120, 20),
                icon_anchor=(0, 0),
            ),
        ).add_to(fg_dorm)
    fg_dorm.add_to(fmap)

    # Accessbility Choropleth
    fg_ai = folium.FeatureGroup(name="Dormitories (2SFCA Accessibility Aᵢ)", show=False)
    for dorm in dormitories:
        lat, lon = dorm_wgs[dorm.name]
        ai       = dorm.accessibility_index
        color    = _ai_color(ai, ai_min, ai_max)
        radius   = 7 + (ai - ai_min) / max(ai_max - ai_min, 1e-9) * 9
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="#222",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=f"{dorm.name}  Aᵢ={ai:.4f} beds/1_000",
        ).add_to(fg_ai)
    fg_ai.add_to(fmap)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
                background:white;padding:14px 16px;border-radius:8px;
                border:1px solid #ccc;font-family:Arial,sans-serif;
                font-size:12px;box-shadow:2px 2px 8px rgba(0,0,0,0.18);
                min-width:180px">
      <b style="font-size:13px">Travel Time to Closest HCF</b><br>
      <div style="margin-top:6px">
        <span style="background:#1a9641;display:inline-block;
              width:14px;height:14px;border-radius:50%;margin-right:5px"></span>≤ 3 min<br>
        <span style="background:#52b347;display:inline-block;
              width:14px;height:14px;border-radius:50%;margin-right:5px"></span>3 – 5 min<br>
        <span style="background:#a8d96c;display:inline-block;
              width:14px;height:14px;border-radius:50%;margin-right:5px"></span>5 – 8 min<br>
        <span style="background:#fdae61;display:inline-block;
              width:14px;height:14px;border-radius:50%;margin-right:5px"></span>8 – 11 min<br>
        <span style="background:#d7191c;display:inline-block;
              width:14px;height:14px;border-radius:50%;margin-right:5px"></span>&gt; 11 min
      </div>
      <hr style="margin:8px 0">
      <b>Markers</b><br>
      <span style="color:#1a5276">✚</span> Healthcare Facility<br>
      <span>⬤</span> Dormitory (travel time)<br>
      <hr style="margin:8px 0">
      <i style="color:#555">Toggle layers via top-right control</i>
    </div>"""
    fmap.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.save(output_path)
    print(f"[Map] Saved → {output_path}")


# Main pipeline
def load_dormitories(filepath):

    gdf = gpd.read_file(filepath)

    dormitories = [
        Dormitory(
            name=row["Dorm_name"],
            geometry=row.geometry,
            population=int(row["Demand_Pop"]),
            dorm_id=int(row["Dorm_ID"]),
            sum_service=float(row.get("SUM_Servic", 0.0))
        )
        for _, row in gdf.iterrows()
    ]

    print(f"[Loader] {len(dormitories)} dormitories loaded from {filepath}")

    return dormitories

def load_facilities(filepath):

    gdf = gpd.read_file(filepath)

    facilities = [
        HealthcareFacility(
            name=row["HCF_name"],
            geometry=row.geometry,
            bed_capacity=int(row["bed_capaci"]),
            fac_id=int(row["Fac_ID"]),
            node_type=row.get("Node_Type", "Hospital"),
            address=row.get("addr_stree", "")
        )
        for _, row in gdf.iterrows()
    ]

    print(f"[Loader] {len(facilities)} healthcare facilities loaded from {filepath}")

    return facilities

def print_supply_ratios(fca, facilities):

    sep = "─" * 68

    print(f"\n{sep}")
    print("2SFCA STEP 1 — Supply-to-Demand Ratios Rⱼ")
    print(sep)
    print(
        f"{'Healthcare Facility':<44}"
        f"{'Beds':>6}"
        f"{'Demand':>10}"
        f"{'Beds/1k':>9}"
    )
    print(sep)

    facilities = sorted(
        facilities,
        key=lambda h: fca.supply_ratios.get(h.name, 0),
        reverse=True
    )

    for hcf in facilities:

        rj = fca.supply_ratios.get(hcf.name, 0)

        print(
            f"{hcf.name:<44}"
            f"{hcf.bed_capacity:>6,}"
            f"{hcf.catchment_population:>10,}"
            f"{rj * 1000:>9.4f}"
        )

    print(sep)

def print_accessibility_indices(dormitories, fca):

    sep = "─" * 75

    ranked = sorted(
        fca.results.items(),
        key=lambda item: item[1],
        reverse=True
    )

    dorm_lookup = {d.name: d for d in dormitories}

    print(f"\n{sep}")
    print("2SFCA STEP 2 — Accessibility Indices")
    print(sep)
    print(
        f"{'Dormitory':<36}"
        f"{'Pop':>8}"
        f"{'Aᵢ':>14}"
        f"{'Rank':>8}"
    )
    print(sep)

    for rank, (name, ai) in enumerate(ranked, 1):

        print(
            f"{name:<36}"
            f"{dorm_lookup[name].population:>8,}"
            f"{ai:>14.2f}"
            f"{rank:>8}"
        )

    print(sep)

def print_od_matrix(od, facilities, dormitories):

    hospital_labels = {
        "Lung Center of the Philippines": "LCP",
        "UP Health Service": "UPHS",
        "Quezon City General Hospital": "QCGH",
        "National Kidney and Transplant Institute": "NKTI",
        "Quirino Memorial Medical Center": "QMMC",
        "Armed Forces of the Philippines Medical Center": "AFPMC",
        "East Avenue Medical Center": "EAMC",
        "Philippine Heart Center": "PHC",
        "Veterans Memorial Medical Center": "VMMC",
        "New Era General Hospital": "NEGH",
        "Philippine Children's Medical Center": "PCMC",
        "World Citi Medical Center": "WCMC",
        "Diliman Doctors Hospital": "DDH",
        "Rosario Maclang Bautista General Hospital": "RMBGH",
        "Dr. Montano G. Ramos General Hospital": "DMRGH",
        "Metro North Medical Center Hospital": "MNMC",
        "Providence Hospital": "PH",
        "General Malvar Hospital": "GMH"
    }

    print("\nHospital Codes:")
    for full, short in hospital_labels.items():
        print(f"{short:<6} = {full}")

    col = 8

    header = f"{'Dormitory':<36}"

    for hcf in facilities:
        header += f"{hospital_labels.get(hcf.name, hcf.name[:col]):<{col}}"

    sep = "─" * len(header)

    print(f"\n{sep}")
    print("OD COST MATRIX (minutes)")
    print(sep)
    print(header)
    print(sep)

    for dorm in dormitories:

        row = f"{dorm.name:<36}"

        for hcf in facilities:

            t = od.get(dorm.name, hcf.name)

            if t is None:
                row += " " * col
            else:
                row += f"{t:<{col}.2f}"

        print(row)

    print(sep)

def main() -> None:
    print("=" * 62)
    print("  GIS-Based Healthcare Accessibility Analysis")
    print("  UP Diliman Dormitories, Quezon City, Philippines")
    print("=" * 62)

    # Loading data
    print("\n[1/6] Loading GeoJSON files …")
    dormitories = load_dormitories(DORM_FILE)
    facilities = load_facilities(HCF_FILE)

    # Building road network
    print("\n[2/6] Building road network …")
    road_network = RoadNetwork()
    road_network.load(ROAD_FILE)

    # Snap entities to network 
    print("\n[3/6] Snapping entities to nearest road nodes …")
    road_network.snap(dormitories + facilities)

    print(
        f"[RoadNetwork] Snapped "
        f"{road_network.snapped_count} entities "
        f"to nearest nodes."
    )
    # OD Cost Matrix 
    print("\n[4/6] Computing OD Cost Matrix...")

    od = ODCostMatrix(
        road_network,
        dormitories,
        facilities,
        TwoStepFCA.CATCHMENT_MIN
    )

    od.compute()

    print(
        f"[ODCostMatrix] {od.served_dormitories}/{len(dormitories)} "
        f"dormitories served within {TwoStepFCA.CATCHMENT_MIN} min."
    )

    print(
        f"[ODCostMatrix] {od.served_dormitories}/{len(dormitories)} served | "
        f"{len(dormitories) * len(facilities)} pairs | "
        f"threshold = {TwoStepFCA.CATCHMENT_MIN} min"
    )

    print_od_matrix(od, facilities, dormitories)

    # 2SFCA 
    print("\n[5/6] Running 2SFCA …")
    fca = TwoStepFCA(
        od,
        dormitories,
        facilities,
        TwoStepFCA.CATCHMENT_MIN
    )
    
    print("\n[5/6] Running 2SFCA …")
    print("[2SFCA] Step 1 — supply-to-demand ratios …")
    print("[2SFCA] Step 2 — accessibility indices …")

    fca.run()

    print("[2SFCA] Complete.")
    print_supply_ratios(fca,facilities)
    print_accessibility_indices(dormitories,fca)

    # Folium map 
    print("\n[6/6] Generating Folium map …")
    map_path = os.path.join(OUTPUT_DIR, "closest_facility_map.html")
    build_closest_facility_map(dormitories, facilities, fca, map_path)

    # Summary 
    ai_vals = [d.accessibility_index for d in dormitories]
    mean_ai = sum(ai_vals) / len(ai_vals)

    sep = "=" * 62

    print(f"\n{sep}")
    print("  FINAL SUMMARY")
    print(sep)

    for dorm in sorted(
        dormitories,
        key=lambda d: d.accessibility_index,
        reverse=True
    ):
        print(
            f"  {dorm.name:<32}  "
            f"Aᵢ={dorm.accessibility_index:.2f}  "
            f"closest={dorm.closest_facility.name if dorm.closest_facility else '—'} "
            f"({f'{dorm.closest_time_min:.2f}' if dorm.closest_time_min else '—'} min)"
        )

    print(f"\n  Mean Aᵢ : {mean_ai:.2f} beds/1 000 residents")
    print(f"  Map     : {map_path}")

    save_summary_json(
        dormitories,
        facilities,
        fca,
        OUTPUT_DIR
    )

    print(sep)

def save_summary_json(dormitories, facilities, fca, output_dir):

    summary = {
        "study_area": "UP Diliman Dormitories",
        "number_of_dormitories": len(dormitories),
        "number_of_facilities": len(facilities),
        "facilities": [],
        "dormitories": []
    }

    # Healthcare Facilities
    for hcf in facilities:
        rj = fca.supply_ratios.get(hcf.name, 0)

        summary["facilities"].append({
        "facility_name": hcf.name,
        "facility_id": hcf.fac_id,
        "address": hcf.address,
        "bed_capacity": hcf.bed_capacity,
        "catchment_population": hcf.catchment_population,
        "supply_ratio": round(rj, 5),
        "beds_per_1000_residents": round(rj * 1000, 2)
    })

    # Dormitories
    for dorm in dormitories:

        nearest_list = sorted(
            dorm.travel_times.items(),
            key=lambda item: item[1]
        )

        summary["dormitories"].append({
            "dormitory_name": dorm.name,
            "dormitory_id": dorm.dorm_id,
            "population": dorm.population,

            "accessibility_index": round(
                dorm.accessibility_index, 2
            ),

            "closest_facility": (
                dorm.closest_facility.name
                if dorm.closest_facility
                else None
            ),

            "closest_travel_time_minutes": (
                round(dorm.closest_time_min, 2)
                if dorm.closest_time_min is not None
                else None
            ),

            "reachable_facilities": [
                {
                    "facility_name": facility,
                    "travel_time_minutes": round(time, 2)
                }
                for facility, time in nearest_list
            ]
        })

    json_path = os.path.join(
        output_dir,
        "analysis_summary.json"
    )

    try:
        with open(
            json_path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                summary,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(f"[JSON] Saved -> {json_path}")

    except Exception as e:
        print("JSON ERROR:", e)

if __name__ == "__main__":
    main()