print("Homemade IEMBot Monitor - KLOT on Web Interface in JavaScipt, HTML, and CSS.")

from flask import Flask, jsonify, render_template
import random
import os

app = Flask(__name__)

# Ensure templates directory exists for the web interface
if not os.path.exists('templates'):
    os.makedirs('templates')

with open('templates/index.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html>
<head><title>IEMBot Monitor</title></head>
<body>
    <h1>KLOT IEM Status</h1>
    <div id="status">Loading...</div>
    <script>
        setInterval(() => {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').innerText =
                    `Device: ${data.device} | Battery: ${data.battery}% | Volume: ${data.volume}`;
                });
        }, 2000);
    </script>
</body>
</html>
""")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        "device": "KLOT-IEM-01",
        "status": "Online",
        "battery": 85,
        "volume": random.randint(40, 60)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
