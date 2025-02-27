from flask import Flask, request, jsonify
import requests
import os
import ffmpeg
import logging

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

    # Сохраняем временный .ogg файл
    temp_ogg = "/tmp/temp_audio.ogg"
    with open(temp_ogg, "wb") as f:
        f.write(voice_file)

    # Конвертируем .ogg в .mp3
    temp_mp3 = "/tmp/temp_audio.mp3"
    try:
        logger.info("Converting .ogg to .mp3")
        stream = ffmpeg.input(temp_ogg)
        stream = ffmpeg.output(stream, temp_mp3)
        ffmpeg.run(stream)
        logger.info("Conversion successful")
    except ffmpeg.Error as e:
        logger.error(f"Error converting audio: {str(e)}")
        return jsonify({"message": f"Ошибка при конверсии аудио: {str(e)}"}), 500

    # Читаем конвертированный файл
    with open(temp_mp3, "rb") as f:
        voice_file = f.read()

    mime_type = "audio/mpeg"
    filename = "voice.mp3"

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {openai_api_key}"}
    files = {
        "file": (filename, voice_file, mime_type),
        "model": (None, "whisper-1"),
        "language": (None, "ru")
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

if name == "__main__":
    app.run(host="0.0.0.0", port=5000)