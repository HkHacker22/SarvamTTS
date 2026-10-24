import os
import base64
from pathlib import Path
from flask import Flask, request, render_template, send_file, jsonify
from sarvamai import SarvamAI

app = Flask(__name__)

def get_client():
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("SARVAM_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key or api_key.strip() == "":
        raise Exception("Missing API key")
    return SarvamAI(api_subscription_key=api_key)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/synthesize", methods=["POST"])
def synthesize():
    try:
        data = request.json
        text = data.get("text", "").strip()
        lang = data.get("lang", "en-IN")
        speaker = data.get("speaker") or None
        model = data.get("model", "bulbul:v4-flash")
        pace = data.get("pace")
        preset = data.get("preset")
        if not text:
            return jsonify({"error": "Empty text"}), 400
        # simple preset
        if preset == "news" and pace is None:
            pace = 0.95
        elif preset == "fiction" and pace is None:
            pace = 0.9
        elif preset == "education" and pace is None:
            pace = 0.85
        client = get_client()
        kwargs = {"text": text, "language_code": lang, "model": model}
        if speaker:
            kwargs["speaker"] = speaker
        if pace is not None:
            try:
                kwargs["pace"] = float(pace)
            except:
                pass
        resp = client.text_to_speech.convert(**kwargs)
        audios = getattr(resp, "audios", []) or []
        if not audios:
            return jsonify({"error": "No audio generated"}), 500
        audio_bytes = base64.b64decode(audios[0])
        out_path = Path("/tmp") / f"sarvam_{os.getpid()}.wav"
        out_path.write_bytes(audio_bytes)
        return send_file(str(out_path), mimetype="audio/wav", as_attachment=False, download_name="output.wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
