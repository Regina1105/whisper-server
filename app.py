from flask import Flask, request, jsonify
import requests
import os
import ffmpeg

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

    # Сохраняем файл временно
    temp_ogg = "/tmp/temp_audio.ogg"
    with open(temp_ogg, "wb") as f:
        f.write(voice_file)

    # Конвертируем .ogg в .mp3
    temp_mp3 = "/tmp/temp_audio.mp3"
    try:
        stream = ffmpeg.input(temp_ogg)
        stream = ffmpeg.output(stream, temp_mp3)
        ffmpeg.run(stream)
    except ffmpeg.Error as e:
        return jsonify({"message": f"Ошибка при конверсии аудио: {str(e)}"}), 500

    # Читаем конвертированный файл
    with open(temp_mp3, "rb") as f:
        voice_file = f.read()

    mime_type = "audio/mpeg"  # Теперь это .mp3
    filename = "voice.mp3"

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

if name == "__main__":
    app.run(host="0.0.0.0", port=5000)