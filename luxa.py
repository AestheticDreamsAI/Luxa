import requests
import re
from colorama import init, Fore, Style

from typing import List, Optional

# Initialize Colorama
init()

class Luxa:
    def __init__(self):
        self.client = requests.Session()
        self.init()

    def init(self):
        # Hardcoded token
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIzYTE0ZThmM2E4YzA0OTgwOWQ4ZDBiNjk2ZGU1OWVmMCIsImlhdCI6MTczODA2NTA4MCwiZXhwIjoyMDUzNDI1MDgwfQ.o00hWa31LK5kYu5jnXqdCWGGMejw4FB8u5Lo1iFEWwU"
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    def lamp(self, id: str, option: str) -> None:
        # Replace "lights." with "light."
        if "lights." in id:
            id = id.replace("lights.", "light.")
        
        if not id.startswith("light."):
            id = f"light.{id}"

        payload = {
            "entity_id": id
        }

        # Send the API request
        response = self.client.post(f"https://home.local.freilab.ink/api/services/light/{option}", json=payload)
        
        # Assume you have defined 'response', 'option', and 'id' somewhere in your code

        if response.status_code == 200:
            print(Fore.GREEN + f"- Successfully executed {option} on {id}" + Style.RESET_ALL)
        else:
            print(Fore.RED + f"- Failed to execute {option} on {id}: {response.text}" + Style.RESET_ALL)

    def get_light_entities(self, json_data: str) -> List[str]:
        light_entities = set()
        
        # Regex pattern to find light entities
        pattern = r'"(light\.[^"]+)"'
        matches = re.findall(pattern, json_data)
        
        for match in matches:
            light_entities.add(match)
            
        print(f"- [Lights: {len(light_entities)}]")
        # Return sorted entities
        return sorted(light_entities)

    def send_post_request(self) -> Optional[List[str]]:
        url = "https://home.local.freilab.ink/api/template"
        json_content = {
            "template": "{% set devices = states | map(attribute=\"entity_id\") | map(\"device_id\") | unique | reject(\"eq\", None) | list %}"
                        "{% set ns = namespace(devices = []) %}{% for device in devices %}{% set entities = device_entities(device) | list %}"
                        "{% if entities %}{% set ns.devices = ns.devices +  [ {device: {\"name\": device_attr(device, \"name\"), \"entities\": entities}} ] %}{% endif %}{% endfor %}"
                        "{{ ns.devices | tojson }}"
        }

        try:
            response = self.client.post(url, json=json_content)
            if response.status_code == 200:
                return self.get_light_entities(response.text)
            else:
                print("Failed to get light entities: ", response.text)
                return None
        except Exception as ex:
            print(f"Error during POST request: {ex}")
            return None

    def handle_devices(self, luxa_response, devices: List[str]) -> None:
        if not luxa_response.devices:
            luxa_response.devices = self.get_devices(luxa_response.devices, devices, luxa_response.response, luxa_response.status)
        
        separator = ',' if ',' in luxa_response.devices else ' '
        for device in luxa_response.devices.split(separator):
            device = device.strip()
            self.lamp(device, luxa_response.action)

    def get_devices(self, dev: str, devices: List[str], response: str, status: str) -> str:
        if status == "no_action":
            return ""
        d = set()

        if dev:
            d.add(dev)

        if not response or not devices:
            return ", ".join(d)

        response = response.replace("lampe", "")
        
        # Check words in the response text
        for s in response.lower().split(' '):
            for device in devices:
                if device in s:
                    if not dev or device not in dev:
                        d.add(device)

        return ", ".join(d)