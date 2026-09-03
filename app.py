from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from google import genai
import os
import time
import json
import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# Gemini API key GitHub में नहीं रखनी है.
# इसे server Environment Variable में GEMINI_API_KEY नाम से रखना होगा.
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "gemini": "configured" if client else "not_configured"
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


@app.route("/api/analyze", methods=["POST"])
def analyze_video():

    if not client:
        return jsonify({
            "error": "Gemini API key is not configured on the server."
        }), 500

    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    filename = secure_filename(filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "Video file not found"}), 404

    try:
        # Upload video to Gemini
        video_file = client.files.upload(file=filepath)

        # Wait until Gemini finishes processing the video
        while not video_file.state or video_file.state.name != "ACTIVE":

            if video_file.state and video_file.state.name == "FAILED":
                return jsonify({
                    "error": "Gemini could not process the video."
                }), 500

            time.sleep(3)
            video_file = client.files.get(name=video_file.name)

        prompt = """
You are the AI engine of a short-video clipping website.

Analyze the entire video and find the 5 BEST moments for short-form content.

Choose moments that have:
- a strong hook
- surprising information
- funny moments
- emotional reactions
- useful information
- important statements
- high audience engagement potential

Each clip should normally be between 10 and 60 seconds.

Do not create overlapping clips.

Return ONLY valid JSON in this exact format:

{
  "clips": [
    {
      "start_time": "00:00",
      "end_time": "00:15",
      "score": 95,
      "reason": "Strong and engaging moment"
    }
  ]
}

Important:
- start_time and end_time must be timestamps from the video.
- score must be from 1 to 100.
- Return the best 5 clips.
- Do not include Markdown.
- Do not include any text outside the JSON.
"""

        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=[video_file, prompt]
        )

        text = response.text.strip()

        # Remove accidental markdown fences
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text)

        return jsonify({
            "success": True,
            "clips": result.get("clips", [])
        })

    except Exception as e:
        return jsonify({
            "error": "AI analysis failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
