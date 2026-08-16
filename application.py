from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Set the path to the directory containing the resources
BASE_DIR = r"C:\Users\nicho\Downloads\NWS-BMH-Chicago-Romeoville-IL-main\NWS-BMH-Chicago-Romeoville-IL-main\data\resources\runtime\WNG689"

@app.route('/')
def index():
    # List files in the directory to display them
    files = os.listdir(BASE_DIR)
    return render_template('index.html', files=files)

@app.route('/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)