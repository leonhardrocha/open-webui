# /home/litec/dev/open-webui/tools/deep_research/event_management/handlers.py

from typing import Dict, Any, Optional
# Relative import from the same package:
from .event_handler_registry import IEventHandler

class DifyEventHandler(IEventHandler):
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.config = {"api_key": api_key, "endpoint": endpoint}

    async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "Dify handled", "api_key_used": self.api_key}

class OpenWebUIEventHandler(IEventHandler):
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url
        self.user_id = user_id
        self.config = {"base_url": base_url, "user_id": user_id}

    async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "OpenWebUI handled", "user_id": self.user_id}

class AnotherEventHandler(IEventHandler):
    def __init__(self, some_param: str):
        self.some_param = some_param
        self.config = {"some_param": some_param}

    async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "Another handled", "param": self.some_param}