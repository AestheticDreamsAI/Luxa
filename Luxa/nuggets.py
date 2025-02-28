# nuggets.py
from colorama import init, Fore, Style
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import importlib.util
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class NuggetContext:
    """Context information passed to nuggets"""
    original_prompt: str
    devices: List[str]
    location: Optional[str] = None
    user_data: Dict[str, Any] = None

class BaseNugget(ABC):
    """Base class for all nuggets"""
    @abstractmethod
    def can_handle(self, context: NuggetContext) -> bool:
        """Determine if this nugget can handle the given prompt"""
        pass

    @abstractmethod
    def process(self, context: NuggetContext) -> str:
        """Process the prompt and return modified version"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return nugget name"""
        pass

class NuggetManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, nuggets_directory: str = "nuggets"):
        if not hasattr(self, 'initialized'):
            self.nuggets: List[BaseNugget] = []
            self.nuggets_directory = nuggets_directory
            self.load_nuggets()
            self.initialized = True

    def load_nuggets(self):
        """Load all nugget plugins from the nuggets directory"""
        if not os.path.exists(self.nuggets_directory):
            os.makedirs(self.nuggets_directory)
            logger.info(f"Created nuggets directory: {self.nuggets_directory}")

        for filename in os.listdir(self.nuggets_directory):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    self._load_nugget_from_file(os.path.join(self.nuggets_directory, filename))
                    logger.info(f"Loaded nugget: {filename}")
                except Exception as e:
                    logger.error(f"Error loading nugget {filename}: {e}")

    def _load_nugget_from_file(self, filepath: str):
        """Load a single nugget from a file"""
        try:
            spec = importlib.util.spec_from_file_location("nugget_module", filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if (isinstance(item, type) and 
                        issubclass(item, BaseNugget) and 
                        item != BaseNugget):
                        nugget_instance = item()
                        self.nuggets.append(nugget_instance)
                        logger.debug(f"Loaded nugget: {nugget_instance.name}")
        except Exception as e:
            logger.error(f"Failed to load nugget from {filepath}: {e}")

    def process_prompt(self, prompt: str, devices: List[str], 
                      location: Optional[str] = None,
                      user_data: Optional[Dict[str, Any]] = None) -> str:
        """Process prompt through all applicable nuggets"""
        context = NuggetContext(
            original_prompt=prompt,
            devices=devices,
            location=location,
            user_data=user_data or {}
        )

        modified_prompt = prompt
        for nugget in self.nuggets:
            if nugget.can_handle(context):
                try:
                    modified_prompt = nugget.process(context)
                    context.original_prompt = modified_prompt
                    print(Fore.YELLOW +f"- [Nugget: {nugget.name}]"  + Style.RESET_ALL)
                except Exception as e:
                    logger.error(f"Error in nugget {nugget.name}: {e}")

        return modified_prompt