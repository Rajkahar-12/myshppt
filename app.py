
import os
import re
import time
import logging
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

load_dotenv()

from ai import AIError, generate_deck
from pptx_builder import THEMES, build_pptx

app = Flask(__name__)

# Limit request size to help prevent unnecessarily large requests.
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

logging.basicConfig(level=logging.INFO)

# Basic in-memory limit for local testing.
LIMIT, WINDOW = 5, 600
hits = {}


def too_many():
    ip = request.remote_addr or "unknown"
    now = time.time()

    recent = [
        t for t in hits.get(ip, [])
        if now - t < WINDOW
    ]

    if len(recent) >= LIMIT:
        hits[ip] = recent
        return True

    recent.append(now)
    hits[ip] = recent
    return False


def read_json():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None

    return data


@app.route("/")
def home():
    return render_template("index.html", themes=THEMES)


@app.post("/api/generate")
def api_generate():
    data = read_json()

    if data is None:
        return jsonify(error="Please send valid JSON data."), 400

    topic = data.get("topic", "")

    if not isinstance(topic, str):
        return jsonify(error="Topic must be text."), 400

    topic = topic.strip()

    if len(topic) < 3:
        return jsonify(error="Please type a topic first."), 400

    if len(topic) > 200:
        return jsonify(error="Keep the topic under 200 characters."), 400

    try:
        count = int(data.get("slides", 8))
    except (ValueError, TypeError, OverflowError):
        return jsonify(error="Slide count must be a number."), 400

    if not 4 <= count <= 20:
        return jsonify(error="Choose between 4 and 20 slides."), 400

    if too_many():
        return jsonify(
            error="Too many requests. Please wait a few minutes and try again."
        ), 429

    audience = data.get("audience", "College students")
    language = data.get("language", "English")
    tone = data.get("tone", "Professional")

    # Validate optional text fields before calling the AI.
    for value, label in [
        (audience, "Audience"),
        (language, "Language"),
        (tone, "Tone"),
    ]:
        if not isinstance(value, str) or len(value) > 100:
            return jsonify(error=f"{label} must be text under 100 characters."), 400

    try:
        deck = generate_deck(
            topic,
            count,
            audience,
            language,
            tone,
        )
        return jsonify(deck)

    except AIError as e:
        app.logger.warning("AI generation failed: %s", e)
        return jsonify(error=str(e)), 502

    except Exception:
        app.logger.exception("Unexpected presentation generation error")
        return jsonify(
            error="Something went wrong. Please try again."
        ), 500


@app.post("/api/download")
def api_download():
    data = read_json()

    if data is None:
        return jsonify(error="Please send valid JSON data."), 400

    deck = data.get("deck")
    theme = data.get("theme", "ocean")

    if not isinstance(deck, dict):
        return jsonify(error="Invalid presentation data."), 400

    if theme not in THEMES:
        return jsonify(error="Please select a valid theme."), 400

    slides = deck.get("slides")

    if not isinstance(slides, list) or not slides:
        return jsonify(error="Generate a presentation first."), 400

    if len(slides) > 20:
        return jsonify(error="A presentation can have at most 20 slides."), 400

    if not all(isinstance(slide, dict) for slide in slides):
        return jsonify(error="Invalid slide data."), 400

    try:
        file = build_pptx(deck, theme)

    except Exception:
        app.logger.exception("PowerPoint generation failed")
        return jsonify(
            error="Could not build the PowerPoint. Please try again."
        ), 500

    title = deck.get("title", "presentation")
    if not isinstance(title, str):
        title = "presentation"

    name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        title
    )[:40] or "presentation"

    return send_file(
        file,
        as_attachment=True,
        download_name=f"{name}.pptx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "").lower() == "1",
    )
