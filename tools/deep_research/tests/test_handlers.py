# /home/litec/dev/open-webui/tools/deep_research/tests/test_handlers.py

import pytest
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

# IMPORTANT: These imports are relative to the 'deep_research' package.
# When pytest is run from 'deep_research', 'deep_research' is added to sys.path.
# If run from 'open-webui', then 'tools.deep_research' would be the import path.
# For simplicity and robustness when running pytest from `deep_research`,
# we'll assume `deep_research` is the top-level package being tested.

# Use absolute imports relative to the 'deep_research' package
from tools.deep_research.event_management.event_handler_registry import EventHandlerRegistry, IEventHandler, HandlerConfig
from tools.deep_research.event_management.handlers import DifyEventHandler, OpenWebUIEventHandler, AnotherEventHandler

@pytest.fixture
def config_file_path(tmp_path) -> Path:
    file_path = tmp_path / "test_event_handlers.yaml"
    yield file_path
    if file_path.exists():
        file_path.unlink()

@pytest.mark.asyncio
async def test_event_handler_registry_flow(config_file_path):
    registry = EventHandlerRegistry(str(config_file_path))

    dify_handler = DifyEventHandler(api_key="dify_secret_key_test", endpoint="https://api.dify.ai/test")
    openwebui_handler = OpenWebUIEventHandler(base_url="http://localhost:8080/test", user_id="test_user123")
    another_handler = AnotherEventHandler(some_param="value_A")

    # No manual __class__.__module__ assignments needed here anymore!
    # Python automatically sets it to 'event_management.handlers' because that's where they are defined.

    registry.register("dify_chat_event", dify_handler)
    registry.register("openwebui_message", openwebui_handler)
    registry.register("another_event", another_handler)

    assert "dify_chat_event" in registry._handlers
    assert "openwebui_message" in registry._handlers
    assert "another_event" in registry._handlers
    assert isinstance(registry._handlers["dify_chat_event"], DifyEventHandler)
    assert isinstance(registry._handlers["openwebui_message"], OpenWebUIEventHandler)
    assert isinstance(registry._handlers["another_event"], AnotherEventHandler)

    registry.save_to_yaml()

    assert config_file_path.exists()
    assert config_file_path.read_text() is not None

    with open(config_file_path, 'r') as f:
        loaded_yaml_content = yaml.safe_load(f)

    assert "dify_chat_event" in loaded_yaml_content
    assert loaded_yaml_content["dify_chat_event"]["module"] == "tools.deep_research.event_management.handlers"
    assert loaded_yaml_content["dify_chat_event"]["class_name"] == "DifyEventHandler"
    assert loaded_yaml_content["dify_chat_event"]["config"]["api_key"] == "dify_secret_key_test"

    assert "openwebui_message" in loaded_yaml_content
    assert loaded_yaml_content["openwebui_message"]["module"] == "tools.deep_research.event_management.handlers"
    assert loaded_yaml_content["openwebui_message"]["class_name"] == "OpenWebUIEventHandler"
    assert loaded_yaml_content["openwebui_message"]["config"]["user_id"] == "test_user123"

    assert "another_event" in loaded_yaml_content
    assert loaded_yaml_content["another_event"]["module"] == "tools.deep_research.event_management.handlers"
    assert loaded_yaml_content["another_event"]["class_name"] == "AnotherEventHandler"
    assert loaded_yaml_content["another_event"]["config"]["some_param"] == "value_A"


    new_registry = EventHandlerRegistry(str(config_file_path))
    loaded_registry = new_registry.load_from_yaml()

    assert "dify_chat_event" in loaded_registry._handlers
    assert "openwebui_message" in loaded_registry._handlers
    assert "another_event" in loaded_registry._handlers
    assert isinstance(loaded_registry._handlers["dify_chat_event"], DifyEventHandler)
    assert isinstance(loaded_registry._handlers["openwebui_message"], OpenWebUIEventHandler)
    assert isinstance(loaded_registry._handlers["another_event"], AnotherEventHandler)

    dify_response = await loaded_registry._handlers["dify_chat_event"].handle({"message": "Test message from Pytest"})
    assert dify_response == {"status": "Dify handled", "api_key_used": "dify_secret_key_test"}

    openwebui_response = await loaded_registry._handlers["openwebui_message"].handle({"text": "Another test query"})
    assert openwebui_response == {"status": "OpenWebUI handled", "user_id": "test_user123"}

    another_response = await loaded_registry._handlers["another_event"].handle({"data": 123})
    assert another_response == {"status": "Another handled", "param": "value_A"}


def test_empty_config_file_load(config_file_path):
    registry = EventHandlerRegistry(str(config_file_path))
    loaded_registry = registry.load_from_yaml()

    assert not loaded_registry._handlers
    assert not config_file_path.exists()

    config_file_path.touch()
    loaded_registry = registry.load_from_yaml()
    assert not loaded_registry._handlers

@pytest.mark.asyncio
async def test_handler_config_default_empty_dict():
    config = HandlerConfig(module="some.module", class_name="SomeClass")
    assert config.config == {}

    class SimpleHandler(IEventHandler):
        async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            return {"status": "simple"}

    registry = EventHandlerRegistry("dummy.yaml")
    simple_handler = SimpleHandler()
    # If SimpleHandler is defined directly in this test file, its module is tests.test_handlers.
    # For a robust setup, it would ideally be in event_management.handlers or a dedicated test_handlers_for_registry.py
    simple_handler.__class__.__module__ = "tests.test_handlers"

    registry.register("simple_event", simple_handler)

    assert "simple_event" in registry._handler_configs
    assert registry._handler_configs["simple_event"].config == {}