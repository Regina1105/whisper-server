from flask import Flask, request, jsonify
import requests
import os
import logging
import mimetypes

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    logger.info("Received request")
    data = request.get_json()
    voice_url = data.get("voice_url")
    if not voice_url:
        logger.info("No voice_url provided")
        return jsonify({"message": "Ошибка: голосовое сообщение не передано!"}), 400

    try:
        logger.info(f"Downloading from {voice_url}")
        voice_response = requests.get(voice_url, timeout=10)
        voice_response.raise_for_status()
        voice_file = voice_response.content
        logger.info("Download successful")
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return jsonify({"message": f"Ошибка при загрузке аудио: {str(e)}"}), 500

    # Проверка поддерживаемого формата и размера
    max_size = 25 * 1024 * 1024  # 25 MB in bytes
    if len(voice_file) > max_size:
        logger.error("File too large")
        return jsonify({"message": "Ошибка: файл слишком большой (максимум 25 МБ)"}), 400

    mime_type, _ = mimetypes.guess_type(voice_url)
    if not mime_type or 'audio' not in mime_type:
        logger.error("Unsupported audio format")
        return jsonify({"message": "Ошибка: неподдерживаемый формат аудио"}), 400

    # Проверка расширения
    mime_type = "audio/mpeg" if voice_url.endswith(".mp3") else "audio/wav"
    filename = "voice.mp3" if voice_url.endswith(".mp3") else "voice.wav"
    if not mime_type.startswith("audio"):
        return jsonify({"message": "Ошибка: поддерживаются только .mp3 и .wav"}), 400

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {openai_api_key}"}
    files = {
        "file": (filename, voice_file, mime_type),
        "model": "whisper-1"
    }

    try:
        logger.info("Sending to OpenAI")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        logger.info("OpenAI response received")
        data = response.json()
        recognized_text = data.get("text", "Ошибка распознавания")
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"message": f"Ошибка в обработке голосового: {str(e)}"}), 500

    return jsonify({"message": recognized_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)