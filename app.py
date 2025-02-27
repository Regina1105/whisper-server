from flask import Flask, request, jsonify
import requests
import os
import logging
import mimetypes  # Для определения MIME-типа

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    logger.info("Received request")

    # Получение URL голосового сообщения
    data = request.get_json()
    voice_url = data.get("voice_url")
    if not voice_url:
        logger.info("No voice_url provided")
        return jsonify({"message": "Ошибка: голосовое сообщение не передано!"}), 400

    # Загрузка аудиофайла
    try:
        logger.info(f"Downloading from {voice_url}")
        voice_response = requests.get(voice_url, timeout=10)
        voice_response.raise_for_status()
        voice_file = voice_response.content
        logger.info("Download successful")
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return jsonify({"message": f"Ошибка при загрузке аудио: {str(e)}"}), 500

    # Проверка размера файла
    max_size = 25 * 1024 * 1024  # 25 MB
    file_size = len(voice_file)
    logger.info(f"File size: {file_size} bytes")
    if file_size > max_size:
        logger.error("File too large")
        return jsonify({"message": "Ошибка: файл слишком большой (максимум 25 МБ)"}), 400

    # Определение MIME-типа файла
    mime_type = voice_response.headers.get("Content-Type", "")
    logger.info(f"Detected MIME type: {mime_type}")

    # Проверка поддерживаемых форматов
    supported_formats = {
        "audio/mpeg": "voice.mp3",
        "audio/wav": "voice.wav",
        "audio/ogg": "voice.ogg",
        "audio/webm": "voice.webm"
    }

    filename = supported_formats.get(mime_type)
    if not filename:
        logger.error("Unsupported audio format")
        return jsonify({"message": "Ошибка: неподдерживаемый формат аудио"}), 400

    # ✅ Отправка файла в OpenAI Whisper API
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "multipart/form-data"  # ✅ Добавлен Content-Type
    }
    
    files = {
        "file": (filename, voice_file, mime_type)
    }
    data = {
        "model": "whisper-1",
        "language": "ru"
    }

    try:
        logger.info("Sending to OpenAI")
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        logger.info("OpenAI response received")
        
        # Получение результата распознавания
        result = response.json()
        recognized_text = result.get("text", "Ошибка распознавания")
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"message": f"Ошибка в обработке голосового: {str(e)}"}), 500

    return jsonify({"message": recognized_text})

# ✅ Исправлена ошибка в запуске приложения
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)