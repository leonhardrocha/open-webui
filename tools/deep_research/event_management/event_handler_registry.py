# /home/litec/dev/open-webui/tools/deep_research/event_management/event_handler_registry.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import yaml
from pathlib import Path
import importlib

class IEventHandler(ABC):
    @abstractmethod
    async def handle(
        self,
        event_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        pass

class HandlerConfig(BaseModel):
    module: str
    class_name: str
    config: Dict[str, Any] = Field(default_factory=dict)

class IEventHandlerRegistry(ABC):
    @abstractmethod
    def register(self, event_type: str, handler: IEventHandler):
        pass

    @abstractmethod
    def save_to_yaml(self) -> None:
        pass

    @abstractmethod
    def load_from_yaml(self) -> 'IEventHandlerRegistry':
        pass

class EventHandlerRegistry(IEventHandlerRegistry):

    def __init__(self, config_path: str = "event_handlers.yaml"):
        self._handlers: Dict[str, IEventHandler] = {}
        self._config_path = Path(config_path)
        self._handler_configs: Dict[str, HandlerConfig] = {}

    def register(self, event_type: str, handler: IEventHandler) -> 'EventHandlerRegistry':
        self._handlers[event_type] = handler
        handler_class = handler.__class__
        self._handler_configs[event_type] = HandlerConfig(
            module=handler_class.__module__,
            class_name=handler_class.__name__,
            config=getattr(handler, 'config', {})
        )
        return self

    def save_to_yaml(self) -> None:
        config_data_for_yaml = {
            event_type: config.model_dump()
            for event_type, config in self._handler_configs.items()
        }
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, 'w') as f:
            yaml.safe_dump(config_data_for_yaml, f, default_flow_style=False)

    def load_from_yaml(self) -> 'IEventHandlerRegistry':
        if not self._config_path.exists():
            return self

        with open(self._config_path, 'r') as f:
            raw_config_data = yaml.safe_load(f) or {}

        for event_type, handler_data in raw_config_data.items():
            config = HandlerConfig(**handler_data)
            self._handler_configs[event_type] = config
            try:
                module = importlib.import_module(config.module)
                handler_class = getattr(module, config.class_name)
                handler_instance = handler_class(**config.config)
                self._handlers[event_type] = handler_instance
            except (ImportError, AttributeError, TypeError) as e:
                print(f"Warning: Could not load handler for event type '{event_type}': {e}")
        return self