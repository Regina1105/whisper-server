import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    data = request.get_json()
    voice_url = data.get("voice_url")
    if not voice_url:
        return jsonify({"message": "Ошибка: голосовое сообщение не передано!"}), 400

    try:
        voice_response = requests.get(voice_url, timeout=10)
        voice_response.raise_for_status()
        voice_file = voice_response.content
    except Exception as e:
        return jsonify({"message": f"Ошибка при загрузке аудио: {str(e)}"}), 500

    mime_type = "audio/ogg" if voice_url.endswith(".ogg") else "audio/mpeg"
    filename = "voice.ogg" if voice_url.endswith(".ogg") else "voice.mp3"

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {openai_api_key}"}
    files = {
        "file": (filename, voice_file, mime_type),
        "model": (None, "whisper-1"),
        "language": (None, "ru")
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        recognized_text = data.get("text", "Ошибка распознавания")
    except Exception as e:
        return jsonify({"message": f"Ошибка в обработке голосового: {str(e)}"}), 500

    return jsonify({"message": recognized_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)