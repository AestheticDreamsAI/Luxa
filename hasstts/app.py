from flask import Flask, request, jsonify, send_file
import requests
import json
import os
from urllib.parse import parse_qs
from pydub import AudioSegment
from pydub.playback import play

app = Flask(__name__)
svoice = "jarvis"

@app.route('/process', methods=['GET', 'POST'])
def handle_request():
    global svoice
    input_text = None
    locale = None
    print("Request method:", request.method)
    print("Request data:", request.data)
    
    type="wav"
    if request.method == 'GET':
        if 'svoice' in request.args:
            svoice = request.args.get('svoice')
            return jsonify({"succeed": "voice switched"}), 200
        # Check GET request parameters
        input_text = request.args.get('INPUT_TEXT')
        locale = request.args.get('LOCALE')
    if request.args.get('type'):
        type = request.args.get('type')
    elif request.method == 'POST':
        # Decode and parse the data
        body = request.data.decode('utf-8')
        parsed_params = parse_qs(body)
        input_text = parsed_params.get('INPUT_TEXT', [None])[0]
        locale = parsed_params.get('LOCALE', [None])[0]
        
    if not input_text:
        return jsonify({"error": "INPUT_TEXT is required"}), 400
    
    if input_text and '"response"' in input_text:
        # Extrahiere den Response-Text, indem wir den Teil nach dem Schlüssel "response": extrahieren
        # Wir gehen davon aus, dass das Format wie oben angegeben ist und dass keine Zeilenumbrüche enthalten sind.
        response_start = input_text.find('"response": "')
        if response_start != -1:
            response_start += len('"response": "')
            response_end = input_text.find('",', response_start)
            if response_end == -1:  # wenn kein Komma gefunden wird, bis das Ende der Zeichenfolge
                response_end = input_text.find('}', response_start)
            if response_end != -1:
                input_text = input_text[response_start:response_end]

    # Call the TTS API
    audio_file_path = synthesize_speech(input_text, svoice, locale,type)
    if audio_file_path:
        # Process the audio file to enhance it
        if type == "wav":
            audio_file_path = enhance_audio(audio_file_path)
        return send_file(audio_file_path, mimetype='audio/'+type)
    else:
        return jsonify({"error": "Failed to synthesize speech."}), 500

def synthesize_speech(text, voice, locale,type="wav"):    
    print(text)  # Just for debugging
    text = text.replace("Jones", "Tschohns").replace("Jessica", "Tschessica").replace("Assistant", "Assistent").replace("Justin", "Tschastin").replace("Cherry", "Scherry").replace("Jarvis", "Tscharwis").replace("KI", "ka ih")
    url = "http://192.168.1.14:8000/v1/audio/speech"
    json_content = {
        "model": "tts-1",
        "input": text.lower().replace("%20"," "),
        "voice": voice,
        "response_format": type
    }
    try:
        # Send the POST request
        response = requests.post(url, json=json_content, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            audio_bytes = response.content
            output_file_path = f"test.{type}"
            
            with open(output_file_path, 'wb') as audio_file:
                audio_file.write(audio_bytes)
            print(f"Audio file saved as test.{type}")
            return output_file_path
        else:
            print(f"Error: {response.status_code}, {response.text}")
    except Exception as ex:
        print(f"Exception occurred: {ex}")
    return ""

def enhance_audio(input_file_path):
    # Load audio file
    audio = AudioSegment.from_wav(input_file_path)
    # Normalize audio
    audio = audio.apply_gain(-audio.max_dBFS)
    # Example of applying a low pass filter
    audio = audio.low_pass_filter(3000)  # Only keep frequencies below 3000 Hz
    # Enhance clarity using a bandpass filter by boosting mid frequencies
    mid_frequencies_boosted = audio.high_pass_filter(2000).low_pass_filter(4000).apply_gain(5)  # Boost mid frequencies between 2 kHz and 4 kHz
    # Combine original with the boosted version to enhance clarity
    enhanced_audio = audio.overlay(mid_frequencies_boosted)
    output_file_path = "enhanced_test.wav"
    enhanced_audio.export(output_file_path, format="wav")
    return output_file_path

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9020)
