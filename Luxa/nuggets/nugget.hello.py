# nuggets/hello_nugget.py

from nuggets import BaseNugget, NuggetContext

class HelloNugget(BaseNugget):
    def __init__(self):
        self._name = "hallo welt"
        self.greeting_keywords = [
            "hallo welt"
        ]

    @property
    def name(self) -> str:
        return self._name

    def can_handle(self, context: NuggetContext) -> bool:
        # Überprüft, ob eines der Begrüßungs-Keywords im Prompt vorkommt
        return any(keyword in context.original_prompt.lower() 
                  for keyword in self.greeting_keywords)

    def process(self, context: NuggetContext) -> str:
        # Fügt dem originalen Prompt eine zusätzliche Information hinzu
        return (f"Wie könntest du kreativ und persönlich folgendes formulieren?:" 
                "\"hallo welt!\"")