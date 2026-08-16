print("Homemade National Weather Service (NWS) Map with KLOT/NWS on Web Interface in Python, JavaScipt, HTML, and CSS.")

import http.server
import socketserver
import json

# Minimal Python backend to serve the files
PORT = 8000

class WeatherHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/weather-data':
            # Example: Fetching KLOT (Chicago) data from NWS API
            # In a real app, use 'requests' to hit https://api.weather.gov/stations/KLOT/observations/latest
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = {"station": "KLOT", "temperature": 72, "forecast": "Sunny"}
            self.wfile.write(json.dumps(data).encode())
        else:
            super().do_GET()

# HTML (index.html)
html_content = """
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <style>#map { height: 500px; }</style>
</head>
<body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([41.59, -88.1], 8);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        fetch('/weather-data').then(r => r.json()).then(data => {
            L.marker([41.59, -88.1).addTo(map).bindPopup("KLOT: " + data.temperature + "°F");
        });
    </script>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)

print(f"Server running at http://localhost:{PORT}. Press Ctrl+C to stop.")
with socketserver.TCPServer(("", PORT), WeatherHandler) as httpd:
    httpd.serve_forever()