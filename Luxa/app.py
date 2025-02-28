# app.py
from colorama import init, Fore, Style
from flask import Flask, request, jsonify, Response
from luxa import Luxa
import requests
import json
import re
import threading
import time
import os
from dataclasses import dataclass
from typing import Optional, Dict, List
from functools import lru_cache
import logging
from nuggets import NuggetManager
import struct  # <-- Füge diese Zeile hinzu
import subprocess
# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)

class FilterOutSpecificLogs(logging.Filter):
    def filter(self, record):
        return "/api/chat" not in record.getMessage()

logger = logging.getLogger(__name__)
logger.addFilter(FilterOutSpecificLogs())

# Configuration
class Config:
    TARGET_URL = "http://localhost:11500"
    VOICE_SERVICE_URL = "http://192.168.1.14:9020"
    OLLAMA_CHECK_INTERVAL = 43200  # 12 hours in seconds

# Response rules template
RESPONSE_RULES_TEMPLATE = """
Regeln:
1. Antworten erfolgen ausschließlich im JSON-Format.
2. Grammatik und Rechtschreibung müssen fehlerfrei sein.
3. Keine zusätzlichen Informationen oder kreativen Ergänzungen.
4. JSON-Felder:
   - response: (string) Deine motivierende Antwort.
   - action: (string) Die Aktion (z. B. "turn_on" oder "turn_off"), wenn relevant. Andernfalls null.
   - devices: (string) Die relevanten Geräte (z. B. "light.philipp" oder "light.wohnzimmer_decke, light.wohnzimmer"). Andernfalls null.
   - location: (string) Der Ort, wenn relevant. Andernfalls null.
   - status: (string) Der Status der Anfrage (z. B. "success" oder "no_action").

Beispiele:
Befehl: "Schalte alle Lampen im Büro aus."
Antwort:
{
  "response": "Die Lampen im Büro sind aus. Zeit für Fokus.",
  "action": "turn_off",
  "devices": "light",
  "location": "office",
  "status": "success"
}

Befehl: "Was ist das Wetter?"
Antwort:
{
  "response": "Egal, ob Sonne oder Regen – mach das Beste aus deinem Tag.",
  "action": null,
  "devices": null,
  "location": null,
  "status": "no_action"
}

Befehl: "Wie geht es dir?"
Antwort:
{
  "response": "Danke, mir geht's gut. Ich hoffe, dir auch!",
  "action": null,
  "devices": null,
  "location": null,
  "status": "no_action"
}

Befehl: "Temperatur auf 21 Grad."
Antwort:
{
  "response": "21 Grad eingestellt. Perfekte Temperatur für Höchstleistungen.",
  "action": "set_temperature",
  "devices": "thermostat",
  "location": "living_room",
  "status": "success"
}

Befehl: "Gute Nacht."
Antwort:
{
  "response": "Schlaf gut. Morgen rockst du's wieder.",
  "action": null,
  "devices": null,
  "location": null,
  "status": "no_action"
}

Deine Mission: Unterstütze den Nutzer mit präzisen, fehlerfreien und motivierenden Antworten, immer im JSON-Format.
"""

@dataclass
class LuxaResponse:
    response: str
    action: Optional[str] = None
    devices: Optional[str] = None
    location: Optional[str] = None
    status: str = "no_action"

@dataclass
class Message:
    role: str
    content: str

class DeviceManager:
    def __init__(self):
        self.luxa = Luxa()
        self._character_prompts = None
        self._character_prompts = None
        self._character_triggers = None

import os
import struct
import json
import subprocess
import logging
from typing import Optional

class DeviceManager:
    def __init__(self):
        self.luxa = Luxa()
        self._character_prompts = None
        self._character_triggers = {}  # Stelle sicher, dass dieses Attribut initialisiert wird
        self._character_prompts = None
        # Weitere Initialisierungen, falls erforderlich

    def _generate_character_triggers(self, characters: List[dict]) -> Dict[str, List[str]]:
        """Generate trigger phrases for each character."""
        triggers = {}
        for char in characters:
            char_id = char['id']
            # Base triggers for each character
            char_triggers = [
                char_id,
                f"mit {char_id}",
                f"mit {char_id} sprechen",
                f"sprich mit {char_id}",
                f"wechsel zu {char_id}",
                f"ändere zu {char_id}",
                f"ich möchte mit {char_id} sprechen"
            ]

            # Add triggers for each alias
            if 'alias' in char:
                for alias in char['alias']:
                    alias = alias.lower()
                    clean_alias = re.sub(r'^(der|die)\s+', '', alias, flags=re.IGNORECASE)
                    char_triggers.extend([
                        clean_alias,
                        f"mit {clean_alias}",
                        f"mit {clean_alias} sprechen",
                        f"sprich mit {clean_alias}",
                        f"wechsel zu {clean_alias}",
                        f"ändere zu {clean_alias}",
                        f"ich möchte mit {clean_alias} sprechen"
                    ])
            triggers[char_id] = char_triggers
        
        return triggers

    def load_character(self, filename: str) -> Optional[dict]:
        """Lädt und gibt die Charakterdaten aus der .lux-Datei zurück und speichert die Audiodaten."""
        try:
            with open(filename, 'rb') as f:
                # Überprüfe den magic number
                magic = f.read(4)
                if magic != b'LUX1':
                    raise ValueError("Invalid character file format")

                version = f.read(1)  # Version lesen
                json_length = struct.unpack('<I', f.read(4))[0]  # Länge der JSON-Daten
                json_data = f.read(json_length).decode('utf-8')  # JSON-Daten lesen

                # JSON in ein Python-Dictionary umwandeln
                character = json.loads(json_data)

                audio_length = struct.unpack('<I', f.read(4))[0]  # Länge der Audiodaten
                audio_data = f.read(audio_length)  # Audiodaten lesen

                # Speichern der Audiodaten in eine WAV-Datei
                audio_path = '/root/f5-tts-serve/voices/main.wav'  # Absoluter Pfad
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)  # Erstelle das Verzeichnis, falls es nicht existiert

                # Schreibe Audiodaten in die WAV-Datei
                with open(audio_path, 'wb') as audio_file:
                    audio_file.write(audio_data)

                character['audio_data'] = audio_data  # Füge die Audiodaten hinzu

                # Führe confgen.py aus
                confgen_path = '/root/f5-tts-serve/confgen.py'
                if os.path.isfile(confgen_path):
                    try:
                        result = subprocess.run(['python3', confgen_path], check=True, capture_output=True, text=True)
                        logger.info(f"confgen.py output: {result.stdout}")  # Protokolliere die Standardausgabe
                    except subprocess.CalledProcessError as e:
                        logger.error(f"confgen.py failed with error:\nOutput: {e.stdout}\nError: {e.stderr}")
                else:
                    logger.error(f"confgen.py not found at {confgen_path}")

                return character  # Gib die geladenen Charakterdaten zurück
        except Exception as e:
            logger.error(f"Failed to load character: {e}")
            return None

    def _generate_character_triggers(self, characters: List[dict]) -> Dict[str, List[str]]:
        """Generate trigger phrases for each character."""
        triggers = {}
        for char in characters:
            char_id = char['id']
            # Base triggers for each character
            char_triggers = [
                char_id,  # direct name
                f"mit {char_id}",  # "mit X"
                f"mit {char_id} sprechen",  # "mit X sprechen"
                f"sprich mit {char_id}",  # "sprich mit X"
                f"wechsel zu {char_id}",  # "wechsel zu X"
                f"ändere zu {char_id}",  # "ändere zu X"
                f"ich möchte mit {char_id} sprechen"  # "ich möchte mit X sprechen"
            ]
            
            # Add triggers for each alias
            if 'alias' in char:
                for alias in char['alias']:
                    alias = alias.lower()
                    # Remove "Der/Die" prefix if present
                    clean_alias = re.sub(r'^(der|die)\s+', '', alias, flags=re.IGNORECASE)
                    
                    # Add alias triggers to character's trigger list
                    char_triggers.extend([
                        clean_alias,  # direct alias
                        f"mit {clean_alias}",  # "mit X"
                        f"mit {clean_alias} sprechen",  # "mit X sprechen"
                        f"sprich mit {clean_alias}",  # "sprich mit X"
                        f"wechsel zu {clean_alias}",  # "wechsel zu X"
                        f"ändere zu {clean_alias}",  # "ändere zu X"
                        f"ich möchte mit {clean_alias} sprechen"  # "ich möchte mit X sprechen"
                    ])
            
            # Add all triggers for this character to the triggers dictionary
            triggers[char_id] = char_triggers
        
        return triggers
    @lru_cache(maxsize=1)
    def load_character_prompts(self) -> Dict:
        """Load and cache character prompts from JSON file."""
        try:
            with open('characters.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._character_triggers = self._generate_character_triggers(data['characters'])
                return {char['id']: char['prompt'] for char in data['characters']}
        except Exception as e:
            logger.error(f"Failed to load character prompts: {e}")
            return {}

    def get_character_from_message(self, message: str) -> Optional[str]:
        """Extract character from user message."""
        if not self._character_triggers:
            self.load_character_prompts()  # Ensure triggers are loaded

        message = message.lower()
        for char_id, triggers in self._character_triggers.items():
            if any(trigger in message for trigger in triggers):
                return char_id
        return None

    def get_devices_info(self) -> str:
        """Get formatted device information."""
        try:
            devices = self.luxa.send_post_request()
            return "Devices:\n" + "\n".join(devices) + "\n"
        except Exception as e:
            logger.error(f"Failed to get devices info: {e}")
            return "No devices available"

    def update_voice(self, character: str) -> bool:
        """Update voice settings for the character."""
        try:
            response = requests.get(
                f"{Config.VOICE_SERVICE_URL}/process?svoice=main",
                timeout=5
            )

            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Voice update failed: {e}")
            return False

class OllamaProxy:
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.conversation_history: List[Message] = []
        self.nugget_manager = NuggetManager()  # Singleton instance
        print("OllamaProxy initialized with NuggetManager")

    def modify_request_payload(self, original_json: dict, prompt_character: str, _character: str) -> dict:
        """Modify the request payload with device information and character prompt."""
        if not original_json or "messages" not in original_json:
            return original_json

        try:
            messages = original_json["messages"]
            if not messages:
                return original_json

            # Get the original prompt from the last user message
            user_messages = [m for m in messages if m.get("role") == "user"]
            if not user_messages:
                return original_json
            
            original_prompt = user_messages[-1]["content"]
            
            # Get device information
            devices_info = self.device_manager.get_devices_info()
            devices_list = [d.strip() for d in devices_info.split('\n') if d.strip()]
            
            # Process through nuggets
            modified_prompt = self.nugget_manager.process_prompt(
                original_prompt,
                devices_list,
                user_data={
                    "character": prompt_character,
                    "history": self.conversation_history
                }
            )
            
            # Update the message content with the modified prompt
            user_messages[-1]["content"] = modified_prompt
            
            # Add character prompt and device information
            character_prompt = _character
            
            # Replace placeholders in the first message
            if messages:
                messages[0]["content"] = messages[0]["content"].replace(
                    "[devices]", devices_info
                ).replace("[agent]", character_prompt)
            
            logger.debug(f"Original prompt: {original_prompt}")
            logger.debug(f"Modified prompt: {modified_prompt}")
            
            return original_json
            
        except Exception as e:
            logger.error(f"Failed to modify payload: {e}")
            return original_json

    def parse_response(self, response_text: str) -> LuxaResponse:
        """Parse the response from Ollama."""
        try:
            json_data = json.loads(response_text)
            return LuxaResponse(**json_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response_text}")
            return LuxaResponse(response=response_text)

# Initialize Flask app
app = Flask(__name__)
device_manager = DeviceManager()
ollama_proxy = OllamaProxy(device_manager)
prompt_character = ""

@app.before_request
def before_request():
    if request.path == '/api/chat':
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    """Main proxy route handler."""
    if request.path in ['/chat', '/ask']:
        return Response("This path is not proxied.", status=403)
    
    target_url = f"{Config.TARGET_URL}/{path}"
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    
    try:
        global prompt_character
        client_ip = request.remote_addr
        method = request.method
        full_url = request.url
        headers = dict(request.headers)
        form_data = request.form
        query_params = request.args
        cookies = request.cookies
        json_data = request.get_json(silent=True)
        
        # Ausgabe der gesammelten Informationen
        print()
        print(f"Request von IP: {client_ip}")
        print(f"Methode: {method}")
        print(f"Vollständige URL: {full_url}")
        print(f"Headers: {headers}")
        print(f"Formulardaten: {form_data}")
        print(f"Query-Parameter: {query_params}")
        print(f"Cookies: {cookies}")
        print()
        
        if path == 'api/tags' and method == 'GET':
            return requests.get(
                f"{Config.TARGET_URL}/api/tags",
                json="",
                headers=headers,
                timeout=30
            ).json() 

        # Extract character from user message if present
        if request.method in ['POST', 'PUT']:
            payload_json = request.get_json()
            if payload_json and "messages" in payload_json and payload_json["messages"]:
                user_message = payload_json["messages"][-1]["content"].lower()
                print(f"- {user_message}")
                
                # Versuche, einen Charakter aus der Nachricht zu extrahieren
                detected_character = device_manager.get_character_from_message(user_message)
                if detected_character:
                    prompt_character = detected_character
                    print(f"Character changed to: {detected_character}")
                    os.environ['luxa_character'] = detected_character
        
        # Update voice settings for the selected character
        device_manager.update_voice(prompt_character)
        
        # Handle the request
        payload = None
        if request.method in ['POST', 'PUT']:
            payload = ollama_proxy.modify_request_payload(
                request.get_json(),
                prompt_character,
                prompt_character
            )
        
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            json=payload if request.method in ['POST', 'PUT'] else None,
            params=request.args if request.method == 'GET' else None,
            timeout=30
        )
        
        # Initialize luxa_response before using
        luxa_response = None
        
        # Process the response
        if response.ok:
            ollama_response = response.json()
            if "message" in ollama_response:
                luxa_response = ollama_proxy.parse_response(
                    ollama_response["message"]["content"]
                )
        
        res = ""
        if luxa_response is not None:
            ollama_response["message"]["content"] = luxa_response.response
            if luxa_response.status != "no_action" and luxa_response.devices:
                print("Handling devices", flush=True)
                device_manager.luxa.handle_devices(
                    luxa_response,
                    device_manager.get_devices_info()
                )
  
        res = ollama_response["message"]["content"]           
        print(f"- {res}", flush=True)              
        return jsonify(ollama_response), response.status_code
    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy request failed: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500

def is_valid_json(json_string):
    json_string = json_string.strip()
    return (json_string.startswith("{") and json_string.endswith("}")) or \
           (json_string.startswith("[") and json_string.endswith("]"))

def extract_json(response_content):
    match = re.search(r"\{(.|\n)*\}", response_content)
    if match:
        return match.group(0)
    return response_content

def check_ollama_health():
    """Background task to check Ollama's health."""
    while True:
        try:
            prompt = "Let's play the ping pong game together. I'll start: Ping"
            response = requests.post(
                f"{Config.TARGET_URL}/api/chat",
                json={"prompt": prompt},
                timeout=10
            )
            
            if '@@@@@@@@@@@@@@' in response.text:
                logger.critical("Unwanted response pattern detected. Initiating reboot.")
                os.system("reboot")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
        time.sleep(Config.OLLAMA_CHECK_INTERVAL)

if __name__ == '__main__':
    character = device_manager.load_character("main.lux")
    if character:
        # Setze den prompt_character auf die geladene ID
        prompt_character = character['prompt']
        print(f"- Loaded character: {character['id']}")
        print(f"- Prompt: {character['prompt']}")
    # Start background health check
    health_check_thread = threading.Thread(
        target=check_ollama_health,
        daemon=True
    )
    health_check_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000)