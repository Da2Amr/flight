from flask import Flask, jsonify, request, render_template
import requests
import math
import os
from datetime import datetime, timedelta

app = Flask(__name__)

MAX_RADIUS_KM = 300

# Simpan histori data per bandara
history_data = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def ambil_data_opensky():
    url = "https://opensky-network.org/api/states/all"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("states", [])
    except Exception as e:
        print("Gagal ambil data:", e)
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    airport_coords = {
        "letung": (3.346028, 106.2666007),
        "jakarta": (-6.1256, 106.6558),
        "palembang": (-2.898, 104.699),
        "pontianak": (0.1507, 109.403),
        "aceh": (5.522, 95.4204),
        "medan": (3.5591, 98.6717),
        "padang": (-0.8761, 100.351),
        "bali": (-8.7482, 115.1675),
        "balikpapan": (-1.267, 116.893),
        "semarang": (-6.9728, 110.375),
        "yia": (-7.906, 110.061),
        "surabaya": (-7.3798, 112.7871)
    }

    airport = request.args.get("airport", "letung").lower()
    manual_lat = request.args.get("lat")
    manual_lon = request.args.get("lon")

    if airport == "manual":
        if manual_lat is None or manual_lon is None:
            return jsonify({"error": "Latitude and longitude required for manual input"}), 400
        try:
            center_lat = float(manual_lat)
            center_lon = float(manual_lon)
        except ValueError:
            return jsonify({"error": "Invalid lat/lon values"}), 400
    else:
        if airport not in airport_coords:
            return jsonify({"error": "Unknown airport"}), 400
        center_lat, center_lon = airport_coords[airport]

    states = ambil_data_opensky()
    now = datetime.utcnow() + timedelta(hours=7)  # WIB timezone
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    filtered = []
    for s in states:
        lat = s[6]
        lon = s[5]
        if lat is not None and lon is not None:
            dist = haversine(center_lat, center_lon, lat, lon)
            if dist <= MAX_RADIUS_KM:
                filtered.append({
                    "timestamp": timestamp,
                    "icao24": s[0],
                    "callsign": s[1].strip() if s[1] else "",
                    "country": s[2],
                    "longitude": lon,
                    "latitude": lat,
                    "altitude": s[7],
                    "distance_km": round(dist, 2)
                })

    # Simpan histori
    if airport not in history_data:
        history_data[airport] = []
    history_data[airport].extend(filtered)

    # Hapus data > 30 hari
    cutoff = now - timedelta(days=30)
    history_data[airport] = [d for d in history_data[airport]
                             if datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") >= cutoff]

    return jsonify(history_data[airport])

if __name__ == "__main__":
    app.run(debug=True)