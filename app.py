from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "message": "Shortify backend is working!"
    })


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400

    video = request.files["video"]

    if video.filename == "":
        return jsonify({"error": "No video selected"}), 400

    filename = secure_filename(video.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    video.save(filepath)

    return jsonify({
        "success": True,
        "message": "Video uploaded successfully!",
        "filename": filename
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
