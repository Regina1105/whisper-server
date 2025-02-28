from flask import Flask, request, jsonify
import requests
import os
import logging
import ffmpeg

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
        # Сохраняем файл с оригинальным расширением из URL
        temp_file = 'temp_audio' + os.path.splitext(voice_url)[1]
        with open(temp_file, 'wb') as f:
            f.write(voice_response.content)
        logger.info("Download successful")
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return jsonify({"message": f"Ошибка при загрузке аудио: {str(e)}"}), 500

    # Проверка размера файла
    max_size = 25 * 1024 * 1024  # 25 MB
    file_size = os.path.getsize(temp_file)
    logger.info(f"File size: {file_size} bytes")
    if file_size > max_size:
        logger.error("File too large")
        os.remove(temp_file)
        return jsonify({"message": "Ошибка: файл слишком большой (максимум 25 МБ)"}), 400

    # Конвертация в .wav для совместимости с OpenAI API
    temp_wav = 'temp_audio.wav'
    try:
        ffmpeg.input(temp_file).output(temp_wav, acodec='pcm_s16le', ac=1, ar='16k').run(overwrite_output=True)
        logger.info("Conversion to WAV successful")
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        os.remove(temp_file)
        return jsonify({"message": f"Ошибка конвертации аудио: {str(e)}"}), 500

    # Подготовка файла для OpenAI API
    try:
        with open(temp_wav, 'rb') as f:
            audio_file = f.read()
    except Exception as e:
        logger.error(f"Error reading converted file: {str(e)}")
        os.remove(temp_file)
        os.remove(temp_wav)
        return jsonify({"message": f"Ошибка при чтении файла: {str(e)}"}), 500

    # Отправка файла в OpenAI Whisper API
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
    }
    files = {
        "file": ("voice.wav", audio_file, "audio/wav")
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
        logger.info(f"Recognized text: {recognized_text}")
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        os.remove(temp_file)
        os.remove(temp_wav)
        return jsonify({"message": f"Ошибка в обработке голосового: {str(e)} - Подробности: {response.text if 'response' in locals() else 'Нет данных'}"}), 500
    finally:
        # Удаление временных файлов
        for file in [temp_file, temp_wav]:
            if os.path.exists(file):
                os.remove(file)

    return jsonify({"message": recognized_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)