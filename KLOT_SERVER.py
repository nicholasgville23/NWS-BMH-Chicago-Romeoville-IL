print("Homemade WFO (Weather Forecast Office) Map with KLOT/NWS on Web Interface in Python, HTML and JavaScript.")

from flask import Flask, render_template_string
import folium

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>KLOT NWS Map</title>
    {{ map_html|safe }}
</head>
<body>
    <h1>Homemade WFO Map (KLOT - Chicago)</h1>
</body>
</html>
"""

@app.route('/')
def index():
    # KLOT Chicago/Romeoville coordinates
    klot_coords = [41.6047, -88.0847]
    m = folium.Map(location=klot_coords, zoom_start=8)
    folium.Marker(klot_coords, popup="NWS Chicago (KLOT)").add_to(m)

    # Add NWS Radar WMS layer (example)
    folium.WmsTileLayer(
        url="https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r.cgi",
        layers="nexrad-n0r-900913",
        name="NEXRAD Radar",
        transparent=True,
        fmt="image/png"
    ).add_to(m)

    return render_template_string(HTML_TEMPLATE, map_html=m._repr_html_())

if __name__ == '__main__':
    app.run(debug=True)
