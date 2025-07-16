"""
title: Deep Research
author: Leonardo Rocha
author_url https://github.com/leonhardrocha
git_url: https://github.com/leonhardrocha/open-webui
description: This tool seach topics for a query using deep research RAG
required_open_webui_version: 0.5.11
requirements: langchain-openai, langgraph, ollama, langchain_ollama
version: 0.2.0
licence: International (CC BY-NC-SA 4.0)
"""

import sys
import os
import requests
import json
import logging
from typing import (
    List,
    Union,
    Generator,
    Iterator,
    Optional,
    Callable,
    Any,
    Dict,
    AsyncGenerator,
)
from pydantic import BaseModel, Field
from open_webui.utils.misc import pop_system_message
from open_webui.config import (
    UPLOAD_DIR,
)  # Assuming UPLOAD_DIR is correctly configured in OpenWebUI
import base64
import tempfile
import asyncio
import dotenv
import aiohttp
import time
from datetime import datetime

# Configure logging for the entire pipeline
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DIFY_PIPELINE")


class EventEmitter:
    """
    EventEmitter is a utility class for emitting events to OpenWebUI frontend.
    
    It provides methods for emitting progress, error, and success events to the OpenWebUI frontend.
    Events are sent as JSON objects with the following format:
    {
        "type": "status",
        "data": {
            "status": <status>,
            "description": <description>,
            "done": <done>,
            "hidden": <hidden>
        }
    }
    
    :param event_emitter: A callback function for emitting events to the OpenWebUI frontend.
    :param debug: If True, sets the logging level to DEBUG, otherwise sets it to INFO.
    """
    def __init__(
        self, event_emitter: Callable[[dict], Any] = None, debug: bool = False
    ):
        self.event_emitter = event_emitter
        self.debug = debug
        self.logger = logging.getLogger()
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        # Prevent adding multiple handlers if already configured by basicConfig
        if not self.logger.handlers:
            handler = logging.FileHandler("event_emitter.log")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def progress_update(self, description: str):
        """Sends an 'in_progress' status update to OpenWebUI."""
        await self.emit(description, status="in_progress", done=False, hidden=False)
        self.logger.info(f"Progress: {description}")

    async def error_update(self, description: str):
        """Sends an 'error' status update to OpenWebUI."""
        await self.emit(description, status="error", done=True, hidden=False)
        self.logger.error(f"Error: {description}")

    async def success_update(self, description: str):
        """Sends a 'success' status update to OpenWebUI."""
        await self.emit(description, status="success", done=True, hidden=True)
        self.logger.info(f"Success: {description}")

    async def emit(
        self,
        description: str = "Unknown State",
        status: str = "Unknown",
        done: bool = False,
        hidden: bool = False,
    ):
        """Emits a status event to the OpenWebUI frontend."""
        if self.event_emitter:
            event = {
                "type": "status",
                "data": {
                    "status": status,
                    "description": description,
                    "done": done,
                    "hidden": hidden,
                },
            }
            await self.event_emitter(event)
            self.logger.debug(f"EventEmitter: {event}")

    def get_closure_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves closure variables from a function, specifically looking for a dictionary.
        Used to extract chat_id and message_id from the external event_emitter closure.
        A mock implementation:
        class MockEventEmitter:
            def __init__(self, request_info_data):
                self._request_info = request_info_data # The data to be captured

            def __call__(self, event_data):
                # In a real Open WebUI environment, this would send an event to the UI
                print(f"Emitting event: {event_data}")

            @property
            def __closure__(self):
                # This is where the magic happens for demonstration
                # In a real scenario, the __closure__ would be naturally created
                # if MockEventEmitter was a nested function or had a cell object
                # for _request_info. For demonstration, we're simulating it.
                class Cell:
                    def __init__(self, content):
                        self.cell_contents = content
                return (Cell(self._request_info),)

        """
        if hasattr(self.event_emitter, "__closure__") and self.event_emitter.__closure__:
            for cell in self.event_emitter.__closure__:
                if isinstance(request_info := cell.cell_contents, dict):
                    # self.logger.debug(f"Closure info found: {request_info}")
                    return request_info
        self.logger.debug("No dictionary found in function closure.")
        return None



class Event:
    """Base class for all event types."""
    def __init__(self, event_type: str):
        self.type = event_type
        self.event_emitter = None

    def set_event_emitter(self, event_emitter: Callable[[dict], Any]) -> 'Event':
        """Set the event emitter callback."""
        self.event_emitter = event_emitter
        return self

    async def emit(self, *args, **kwargs) -> None:
        """Base emit method to be overridden by derived classes."""
        raise NotImplementedError("emit method must be implemented by derived classes")


class StatusEvent(Event):
    """Event type for status updates."""
    def __init__(self):
        super().__init__("status")

    def curry(self, description: str = None, done: bool = False, hidden: bool = False) -> 'StatusEvent':
        """Curry the event with status parameters."""
        self.description = description
        self.done = done
        self.hidden = hidden
        return self

    async def emit(self) -> None:
        """Emit the status event."""
        if not self.event_emitter:
            raise ValueError("Event emitter not set")
        
        event_data = {
            "type": self.type,
            "data": {
                "description": self.description,
                "done": self.done,
                "hidden": self.hidden
            }
        }
        await self.event_emitter(event_data)


class MessageEvent(Event):
    """Event type for chat messages."""
    def __init__(self):
        super().__init__("message")

    def curry(self, content: str) -> 'MessageEvent':
        """Curry the event with message content."""
        self.content = content
        return self

    async def emit(self) -> None:
        """Emit the message event."""
        if not self.event_emitter:
            raise ValueError("Event emitter not set")
        
        event_data = {
            "type": self.type,
            "data": {"content": self.content}
        }
        await self.event_emitter(event_data)


class CitationEvent(Event):
    """Event type for citations."""
    def __init__(self):
        super().__init__("citation")

    def curry(self, document: str, source: dict, metadata: dict = None) -> 'CitationEvent':
        """Curry the event with citation parameters."""
        self.document = document
        self.source = source
        self.metadata = metadata or {}
        return self

    async def emit(self) -> None:
        """Emit the citation event."""
        if not self.event_emitter:
            raise ValueError("Event emitter not set")
        
        event_data = {
            "type": self.type,
            "data": {
                "document": self.document,
                "metadata": self.metadata,
                "source": self.source
            }
        }
        await self.event_emitter(event_data)


class Tools:
    """
    Tools class for OpenWebUI pipelines.
    This class is often expected by OpenWebUI even if no specific tools are defined.
    It can contain functions that act as external tools or functionalities
    that the pipeline might call.
    """

    class Valves(BaseModel):
        # Environment variable settings
        DIFY_BASE_URL: str = Field(
            default="http://localhost/v1",
            description="Optional: Base URL for the Dify API (default: http://localhost/v1).",
        )
        WEBUI_BASE_URL: str = Field(
            default="http://localhost/v1",
            description="Optional: Base URL for the OpenWebUI API (default: http://localhost:3000/).",
        )
        DIFY_USER: str = Field(
            default="",
            description="Optional: Username used in Dify workflow, defaults to user´s email.",
        )
        DIFY_KEY: str = Field(
            default="app-05EAqfax9bXXxUuT9EgMao6p", description="Your Dify API Key."
        )
        WEBUI_KEY: str = Field(default="sk-1234", description="Your OpenWebUI API Key.")
        DEBUG: bool = Field(default=True, description="Enable debug mode.")

    def __init__(self, debug: bool = False):
        self.citation = True
        self.type = "manifold"
        self.id = (
            "deep_research"  # This 'id' is used by OpenWebUI to identify the pipeline
        )
        self.name = "Deep Research"
        # Initialize valves with environment variables
        dotenv.load_dotenv(".env")
        settings = {
            "DIFY_KEY": os.getenv(
                "DIFY_KEY", "app-05EAqfax9bXXxUuT9EgMao6p"
            ),  # Empty default, force user to set
            "WEBUI_KEY": os.getenv("WEBUI_KEY", ""),  # Empty default, force user to set
            "DIFY_BASE_URL": os.getenv("DIFY_BASE_URL", "http://docker-nginx-1/v1"),
            "WEBUI_BASE_URL": os.getenv("WEBUI_BASE_URL", "http://localhost:3000/"),
            "DIFY_USER": os.getenv("DIFY_USER", "openwebui_user"),  # Default Dify user
            "DEBUG": os.getenv("DEBUG", debug),  # Default DEBUG Level
        }
        self.valves = self.Valves(**settings)
        self.debug = self.valves.DEBUG
        self.logger = logging.getLogger()
        self.logger.info("🔍 DEBUG Mode: " + "✅ Enabled" if self.debug else "❌ Disabled")
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler("tools.log")
            formatter = logging.Formatter(
                "%(asctime)s - Tools: - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.openwebui = OpenWebUIHelper(self.valves, debug=self.debug)
        self.dify = DifyHelper(self.valves, debug=self.debug)
        self.dify.load_state()  # Load Dify conversation/file state on initialization

    def pipes(self) -> List[dict]:
        """Returns the list of available DIFY models (currently hardcoded or fetched by DifyHelper)."""
        return self.dify.get_models()

    async def research_stream(
        self, query: str, __event_emitter__: Optional[Callable[[dict], Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Researches based on the input string using streaming mode.

        Args:
            query: The research query or question to send to Dify.
            __event_emitter__: Optional event emitter callback for status updates.

        Yields:
            str: Chunks of the response as they are received.

        Example:
            async for chunk in tools.research_stream("What is AI?"):
                print(chunk, end="")
        """
        event_emitter = EventEmitter(__event_emitter__, debug=self.debug)

        # Initial status update
        await event_emitter.emit("🚀 Starting research process...", "in_progress")

        # Validate required configuration
        if not self.valves.DIFY_KEY:
            error_msg = (
                "❌ Error: DIFY_KEY is not configured. Please set your Dify API key."
            )
            await event_emitter.emit(error_msg, "error")
            self.logger.error(error_msg)
            yield error_msg
            return

        if not query or not query.strip():
            error_msg = "❌ Error: Empty query provided. Please provide a valid research question."
            await event_emitter.emit(error_msg, "error")
            self.logger.error(error_msg)
            yield error_msg
            return

        try:
            # Prepare the request
            await event_emitter.emit(
                "🔍 Processing your research query...", "in_progress"
            )
            self.logger.debug(f"Starting research with query: {query[:100]}...")

            # Track state
            result_parts = []
            has_content = False
            start_time = time.time()

            # Make the API request
            try:
                async for chunk in self.dify.send_chat_message(
                    query=query, user=self.valves.DIFY_USER, response_mode="streaming", event_emitter=__event_emitter__
                ):
                    # Process different types of response chunks
                    if chunk.get("type") == "text":
                        content = chunk.get("content", "")
                        if content:
                            has_content = True
                            result_parts.append(content)
                            yield content

                    elif chunk.get("type") == "message_file":
                        # Handle file attachments if needed
                        file_info = (
                            f"📎 File attached: {chunk.get('file_type', 'file')}"
                        )
                        await event_emitter.emit(file_info, "info")
                        self.logger.info(file_info)

                    elif chunk.get("type") == "error":
                        error_msg = f"❌ Error: {chunk.get('message', 'Unknown error occurred')}"
                        await event_emitter.emit(error_msg, "error")
                        self.logger.error(error_msg)
                        yield error_msg
                        return

            except aiohttp.ClientError as e:
                error_msg = f"❌ Network error during research: {str(e)}"
                await event_emitter.emit(error_msg, "error")
                self.logger.error(error_msg, exc_info=True)
                yield error_msg
                return

            except Exception as e:
                error_msg = f"❌ Unexpected error during research: {str(e)}"
                await event_emitter.emit(error_msg, "error")
                self.logger.error(error_msg, exc_info=True)
                yield error_msg
                return

            # Process results
            if not has_content:
                warning_msg = "⚠️ No content was returned for your query. Please try rephrasing or check your API configuration."
                await event_emitter.emit(warning_msg, "warning")
                self.logger.warning(warning_msg)
                yield warning_msg
                return

            # Log successful completion
            duration = time.time() - start_time
            success_msg = f"✅ Research completed in {duration:.1f} seconds"
            await event_emitter.emit(success_msg, "success")
            self.logger.info(f"Research completed successfully in {duration:.1f}s")

        except Exception as e:
            error_msg = f"❌ Critical error in research_stream: {str(e)}"
            await event_emitter.emit(error_msg, "error")
            self.logger.error(error_msg, exc_info=True)
            yield error_msg

    async def research(
        self, query: str, __event_emitter__: Optional[Callable[[dict], Any]] = None
    ) -> str:
        """
        Performs research using Dify's blocking API.

        Args:
            query: The research query or question to send to Dify.
            __event_emitter__: Optional event emitter callback for status updates.
            **kwargs: Additional parameters to pass to the Dify API.

        Returns:
            str: The complete research response.

        Example:
            result = await tools.research("What is AI?")
            print(result)
        """
        event_emitter = EventEmitter(__event_emitter__, debug=self.debug)

        # Use research_stream but collect results
        result_parts = []
        try:
            async for chunk in self.research_stream(query, __event_emitter__):
                result_parts.append(chunk)
            return "".join(result_parts)

        except Exception as e:
            error_msg = f"❌ Error in research: {str(e)}"
            await event_emitter.emit(error_msg, "error")
            self.logger.error(error_msg, exc_info=True)
            return error_msg

    async def pipe(
            self,
            body: dict,
            __event_emitter__: Optional[Callable[[dict], Any]] = None,
            __user__: Optional[dict] = None,
            __task__: Optional[str] = None,
        ) -> AsyncGenerator[dict, None]:
            """
            Handles chat requests from OpenWebUI, orchestrates Dify interaction,
            and streams responses back to OpenWebUI.
            """
            event_emitter = EventEmitter(__event_emitter__, debug=self.debug)
            status_event = StatusEvent().set_event_emitter(__event_emitter__)
            await status_event.curry(description="Iniciando o DIFY Manifold Pipe...").emit()

            if not self.valves.DIFY_KEY:
                error_msg = "Erro: A variável de ambiente DIFY_KEY não está configurada. Por favor, defina sua chave de API Dify."
                self.logger.error(error_msg)
                await status_event.curry(description=error_msg).emit()
                yield {"type": "error", "content": error_msg}
                return

            # Extract model name from body (e.g., "dify.deepseek-r1" -> "deepseek-r1")
            model_name = (
                body["model"].split(".")[-1] if "." in body["model"] else body["model"]
            )
            self.logger.debug(f"Nome do modelo resolvido: {model_name}")

            # Handle special OpenWebUI tasks (title generation, tag generation)
            if __task__ is not None:
                if __task__ == "title_generation":
                    await status_event.curry(description="Geração de título pelo Dify (placeholder).").emit()
                    yield {"type": "text", "content": f"Título Dify: {model_name}"}
                    return
                elif __task__ == "tags_generation":
                    await status_event.curry(description="Geração de tags pelo Dify (placeholder).").emit()
                    yield {"type": "text", "content": f'{{"tags":["{model_name}"]}}'}
                    return

            # Determine the current user for Dify API calls
            current_user = self.valves.DIFY_USER
            if __user__ and "email" in __user__:
                current_user = __user__["email"]
            elif __user__ and "id" in __user__:  # Fallback to id if email not present
                current_user = __user__["id"]
            self.logger.debug(f"Usuário atual para Dify: {current_user}")

            # Extract chat_id and message_id from the OpenWebUI event context
            chat_id = None
            message_id = None

            # OpenWebUI `__event_emitter__` is typically a partial function that has chat_id/message_id in its closure
            closure_info = event_emitter.get_closure_info()
            if closure_info:
                chat_id = closure_info.get("chat_id")
                message_id = closure_info.get("message_id")

            # If not found in closure, try getting from body (less reliable for direct OWUI chat context)
            if not chat_id:
                chat_id = body.get("chat_id")
            if not message_id:
                message_id = body.get("message_id")

            if not chat_id or not message_id:
                error_msg = "Erro: Não foi possível obter o ID da conversa ou o ID da mensagem do OpenWebUI. Garanta que o contexto da conversa esteja disponível."
                await status_event.curry(description=error_msg).emit()
                yield {"type": "error", "content": error_msg}
                return

            self.logger.debug(f"Chat ID: {chat_id}, Message ID: {message_id}")

            # Process system messages and regular messages
            system_message, messages = pop_system_message(body["messages"])
            self.logger.debug(f"Mensagem do sistema: {system_message}")
            self.logger.debug(f"Mensagens processadas: {len(messages)}")

            # Dify conversation context management
            dify_conversation_id = None
            dify_parent_message_id = None

            is_new_conversation = len(messages) == 1

            # Initialize or retrieve conversation state
            if is_new_conversation or chat_id not in self.dify.chat_message_mapping:
                self.dify.dify_chat_model[chat_id] = model_name
                self.dify.chat_message_mapping[chat_id] = {
                    "dify_conversation_id": "",  # Will be filled by Dify's first response
                    "message_id_map": {},  # Map OWUI message_id to Dify message_id
                }
                self.dify.dify_file_list[chat_id] = (
                    {}
                )  # Clear file list for new conversation
                self.logger.info(
                    f"Nova conversa iniciada para chat_id: {chat_id}. Estado limpo."
                )
            else:
                # Validate model consistency for existing conversations
                if self.dify.dify_chat_model.get(chat_id)!= model_name:
                    error_msg = f"Erro: Não é possível mudar o modelo em uma conversa existente. Esta conversa foi iniciada com '{self.dify.dify_chat_model.get(chat_id, 'modelo desconhecido')}'."
                    self.logger.error(error_msg)
                    await status_event.curry(description=error_msg).emit()
                    yield {"type": "error", "content": error_msg}
                    return

                dify_conversation_id = self.dify.chat_message_mapping[chat_id].get(
                    "dify_conversation_id"
                )
                message_id_map = self.dify.chat_message_mapping[chat_id].get(
                    "message_id_map", {}
                )

                # Find the Dify message ID of the *previous AI response* to set as parent for continuity
                # The OpenWebUI `messages` list should contain the full history up to the current user query.
                # We look for the last assistant message in this list.
                last_assistant_message_owui_id = None
                for msg_idx in range(
                    len(messages) - 2, -1, -1
                ):  # Iterate backwards from message before current user query
                    if messages[msg_idx]["role"] == "assistant":
                        last_assistant_message_owui_id = messages[msg_idx]["id"]
                        break

                if (
                    last_assistant_message_owui_id
                    and last_assistant_message_owui_id in message_id_map
                ):
                    dify_parent_message_id = message_id_map[last_assistant_message_owui_id]
                    self.logger.debug(
                        f"Continuando conversa Dify com parent_message_id: {dify_parent_message_id}"
                    )
                else:
                    self.logger.debug(
                        "Nenhuma mensagem anterior do assistente mapeada para Dify. Iniciando novo branch ou primeira mensagem da conversa Dify."
                    )

            # Get the last message (current user query)
            user_query_message = messages[-1]
            query_text = ""
            dify_files_payload = []  # list to hold Dify's file payload structure

            # Process message content (text and image_url)
            if isinstance(user_query_message.get("content"), list):
                for item in user_query_message["content"]:
                    if item["type"] == "text":
                        query_text += item["text"]
                    elif item["type"] == "image_url":
                        try:
                            # Upload base64 encoded image or remote URL image
                            # Dify expects 'upload_file_id' for local_file and 'url' for remote_url
                            if item["image_url"]["url"].startswith("data:"):
                                upload_file_id = self.dify.upload_images(
                                    item["image_url"]["url"], current_user
                                )
                                dify_files_payload.append(
                                    {
                                        "type": "image",
                                        "transfer_method": "local_file",
                                        "upload_file_id": upload_file_id,
                                    }
                                )
                                self.logger.info(
                                    f"Imagem base64 carregada para Dify com ID: {upload_file_id}"
                                )
                            else:
                                # Assuming remote URL images can be sent directly if Dify supports it
                                dify_files_payload.append(
                                    {
                                        "type": "image",
                                        "transfer_method": "remote_url",
                                        "url": item["image_url"]["url"],
                                    }
                                )
                                self.logger.info(
                                    f"Imagem remota adicionada ao payload: {item['image_url']['url']}"
                                )

                        except Exception as e:
                            error_msg = f"Erro ao processar imagem para Dify: {e}"
                            self.logger.error(error_msg)
                            await status_event.curry(description=error_msg).emit()
                            yield {"type": "error", "content": error_msg}
                            return
            else:
                query_text = user_query_message.get("content", "")

            # Process file uploads from `body["upload_files"]`
            if "upload_files" in body and body["upload_files"]:
                if chat_id not in self.dify.dify_file_list:
                    self.dify.dify_file_list[chat_id] = {}

                for file_obj in body["upload_files"]:
                    if file_obj.get("type")!= "file" or not file_obj.get("id"):
                        continue

                    owui_file_id = file_obj["id"]

                    # Check if file was already uploaded in this conversation
                    if owui_file_id in self.dify.dify_file_list[chat_id]:
                        dify_files_payload.append(
                            self.dify.dify_file_list[chat_id][owui_file_id]["dify_payload"]
                        )
                        self.logger.debug(
                            f"Reutilizando arquivo Dify já carregado: {owui_file_id}"
                        )
                        continue

                    file_path = None
                    if (
                        "collection_name" in file_obj
                        and file_obj["file"]
                        and "filename" in file_obj["file"]
                    ):
                        file_path = os.path.join(UPLOAD_DIR, file_obj["file"]["filename"])
                    elif file_obj["file"] and "path" in file_obj["file"]:
                        file_path = file_obj["file"]["path"]

                    if not file_path or not os.path.exists(file_path):
                        error_msg = f"Caminho do arquivo não encontrado ou inválido para o ID do arquivo OpenWebUI: {owui_file_id}. Caminho: {file_path}"
                        self.logger.error(error_msg)
                        await status_event.curry(description=f"Erro: Arquivo carregado não encontrado no servidor: {file_obj.get('file',{}).get('filename', 'Arquivo desconhecido')}").emit()
                        continue  # Skip this file and continue with others

                    file_mime_type = file_obj["file"]["meta"]["content_type"]
                    file_name = file_obj["file"]["filename"]

                    upload_file_id = None
                    file_type_for_dify = ""

                    try:
                        if self.dify.is_doc_file(file_path):
                            upload_file_id = self.dify.upload_file(
                                current_user, file_path, file_mime_type
                            )
                            file_type_for_dify = "document"
                        elif self.dify.is_text_file(file_mime_type):
                            upload_file_id = self.dify.upload_text_file(
                                current_user, file_path
                            )
                            file_type_for_dify = "document"
                        elif self.dify.is_audio_file(file_path):
                            upload_file_id = self.dify.upload_file(
                                current_user, file_path, file_mime_type
                            )
                            file_type_for_dify = "audio"
                        elif self.dify.is_image_file(file_path):
                            upload_file_id = self.dify.upload_file(
                                current_user, file_path, file_mime_type
                            )
                            file_type_for_dify = "image"
                        else:
                            self.logger.warning(
                                f"Tipo de arquivo não suportado para upload no Dify: {file_mime_type} ({file_name}). Pulando."
                            )
                            await status_event.curry(description=f"Pulando arquivo não suportado: {file_name}").emit()
                            continue

                        if upload_file_id:
                            dify_file_payload_entry = {
                                "type": file_type_for_dify,
                                "transfer_method": "local_file",
                                "upload_file_id": upload_file_id,
                            }
                            dify_files_payload.append(dify_file_payload_entry)

                            # Store the mapping for future requests in this chat
                            self.dify.dify_file_list[chat_id][owui_file_id] = {
                                "local_file_path": file_path,
                                "dify_file_id": upload_file_id,
                                "file_name": file_name,
                                "dify_payload": dify_file_payload_entry,  # Store the full payload for re-use
                            }
                            self.logger.info(
                                f"Arquivo carregado e mapeado: {file_name} (OWUI ID: {owui_file_id}) para Dify ID: {upload_file_id}"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Falha ao carregar o arquivo {file_name} para o Dify: {e}",
                            exc_info=True,
                        )
                        await status_event.curry(description=f"Falha ao carregar o arquivo '{file_name}': {e}").emit()
                        continue

            await status_event.curry(description="Enviando mensagem para Dify...").emit()

            last_dify_message_id_received = None
            final_dify_conversation_id = dify_conversation_id  # Start with existing if any

            try:
                # Validate API key before proceeding
                if (
                    not hasattr(self.valves, "DIFY_KEY")
                    or not self.valves.DIFY_KEY
                    or not isinstance(self.valves.DIFY_KEY, str)
                    or not self.valves.DIFY_KEY.strip()
                ):
                    error_msg = "DIFY_KEY is not properly configured. Please check your environment variables."
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)

                async for chunk in self.dify.send_chat_message(
                    query=query_text,
                    user=current_user,
                    conversation_id=final_dify_conversation_id,
                    response_mode="streaming",
                    inputs={},  # Pass empty inputs if not explicitly used, Dify API payload
                    files=dify_files_payload,
                    event_emitter=event_emitter,
                    # Dify's `chat-messages` API uses `conversation_id` and `message_id` for continuation.
                    # `message_id` inside events will be used to track the last Dify message for mapping.
                    # `parent_message_id` would be passed in payload only if we were creating a new message
                    # explicitly linking to a parent, but Dify API manages this with `conversation_id`
                    # and internal state when streaming.
                ):
                    # Update conversation and message IDs as soon as they are available from Dify
                    if chunk.get("conversation_id") and not final_dify_conversation_id:
                        final_dify_conversation_id = chunk["conversation_id"]
                        self.dify.chat_message_mapping[chat_id][
                            "dify_conversation_id"
                        ] = final_dify_conversation_id
                        self.logger.debug(
                            f"Dify conversation ID set: {final_dify_conversation_id}"
                        )

                    if chunk.get("message_id"):
                        last_dify_message_id_received = chunk["message_id"]

                    # Process and yield events to OpenWebUI
                    event_type = chunk.get("event") # Changed from 'type' to 'event' based on Dify logs/docs [1, 2]
                    
                    if event_type in ["message", "agent_message"]: # Handle both message and agent_message as text output [2]
                        yield {
                            "type": "text",  # OpenWebUI expects 'text' for streaming content
                            "content": chunk.get("answer", ""), # Content for message is in 'answer' [3]
                        }
                    elif event_type == "text_chunk":  # Represents a partial text fragment [1]
                        yield {
                            "type": "text",  # OpenWebUI expects 'text' for streaming content
                            "content": chunk.get("data", {}).get("text", ""), # Content for text_chunk is in data.text [1]
                        }
                    elif event_type == "file": # This is the normalized file event (original code)
                        self.logger.debug(f"Recebido evento de arquivo do Dify: {chunk}")
                        yield chunk  # Yield the already normalized file event
                    elif event_type == "message_end":
                        # This signals the end of a message generation.
                        # We can now store the mapping of OpenWebUI's last message ID to Dify's last message ID.
                        if chat_id and message_id and last_dify_message_id_received:
                            if (
                                "message_id_map"
                                not in self.dify.chat_message_mapping[chat_id]
                            ):
                                self.dify.chat_message_mapping[chat_id][
                                    "message_id_map"
                                ] = {}
                            self.dify.chat_message_mapping[chat_id]["message_id_map"][
                                message_id
                            ] = last_dify_message_id_received
                            self.logger.debug(
                                f"Mapeamento de conversa Dify atualizado para chat_id {chat_id}: OWUI msg ID {message_id} -> Dify msg ID {last_dify_message_id_received}"
                            )
                        self.dify.save_state()  # Save state after successful message completion

                        # Optionally, yield message_end to OWUI if it requires it for metadata (e.g., usage)
                        yield {
                            "type": "message_end",  # Custom event type if OWUI handles it specifically
                            "content": {
                                "usage": chunk.get("usage", {}),
                                "metadata": chunk.get("metadata", {}),
                                "retriever_resources": chunk.get("retriever_resources",),
                            },
                        }
                    elif event_type == "workflow_started": # Workflow starts execution [1]
                        wf_name = chunk.get("data", {}).get("workflow_name", "Desconhecido")
                        await status_event.curry(description=f"Fluxo de Trabalho Dify Iniciado: {wf_name}").emit()
                        yield {"type": "workflow_start", "content": chunk.get("data")}

                    elif event_type == "node_started": # Node execution started [1]
                        node_name = chunk.get("data", {}).get("node_name", "Desconhecido")
                        await status_event.curry(description=f"Nó Dify Iniciado: {node_name}").emit()
                        yield {"type": "node_start", "content": chunk.get("data")}

                    elif event_type == "node_finished": # Node execution ends, success or failure [1]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("node_name", "Desconhecido")
                        status = node_data.get("status") # Status of execution [1]
                        error_msg = node_data.get("error") # Optional reason of error [1]
                        await status_event.curry(description=f"Nó Dify Finalizado: {node_name} (Status: {status})" + (f" Erro: {error_msg}" if error_msg else "")).emit()
                        yield {"type": "node_finish", "content": chunk.get("data")}

                    elif event_type == "workflow_finished": # Workflow execution ends, success or failure [1]
                        status = chunk.get("data", {}).get("status") # Status of execution [1]
                        error_msg = chunk.get("data", {}).get("error") # Optional reason of error [1]
                        await status_event.curry(description=f"Fluxo de Trabalho Dify Finalizado. Status: {status}" + (f" Erro: {error_msg}" if error_msg else "")).emit()
                        self.dify.save_state()  # Ensure state is saved at workflow end too
                        yield {"type": "workflow_finish", "content": chunk.get("data")}

                    elif event_type == "iteration_started": # Iteration node started [4, 5]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Iteration")
                        await status_event.curry(description=f"Iteração Iniciada: {node_name}").emit()
                        yield {"type": "iteration_start", "content": node_data}

                    elif event_type == "iteration_next": # Next iteration in an iteration node [4, 5]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Iteration")
                        index = node_data.get("index")
                        await status_event.curry(description=f"Próxima Iteração: {node_name} (Índice: {index})").emit()
                        yield {"type": "iteration_next", "content": node_data}

                    elif event_type == "iteration_completed": # Iteration node completed [4, 5]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Iteration")
                        status = node_data.get("status")
                        error_msg = node_data.get("error")
                        await status_event.curry(description=f"Iteração Concluída: {node_name} (Status: {status})" + (f" Erro: {error_msg}" if error_msg else "")).emit()
                        yield {"type": "iteration_finish", "content": node_data}

                    elif event_type == "parallel_branch_started": # Parallel branch started [1, 6]
                        branch_id = chunk.get("data", {}).get("parallel_branch_id", "Desconhecido")
                        await status_event.curry(description=f"Ramificação Paralela Iniciada: {branch_id}").emit()
                        yield {"type": "parallel_branch_start", "content": chunk.get("data")}

                    elif event_type == "parallel_branch_finished": # Parallel branch finished [1, 6]
                        branch_id = chunk.get("data", {}).get("parallel_branch_id", "Desconhecido")
                        status = chunk.get("data", {}).get("status")
                        error_msg = chunk.get("data", {}).get("error")
                        await status_event.curry(description=f"Ramificação Paralela Finalizada: {branch_id} (Status: {status})" + (f" Erro: {error_msg}" if error_msg else "")).emit()
                        yield {"type": "parallel_branch_finish", "content": chunk.get("data")}

                    elif event_type == "agent_thought": # Agent thought process [2]
                        await status_event.curry(description="Pensamento do Agente...").emit()
                        yield {"type": "agent_thought", "content": chunk.get("data", chunk)}

                    elif event_type == "agent_log": # Agent log messages [2]
                        await status_event.curry(description="Log do Agente...").emit()
                        yield {"type": "agent_log", "content": chunk.get("data", chunk)}

                    elif event_type == "loop_started": # Loop node started [2]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Loop")
                        await status_event.curry(description=f"Loop Iniciado: {node_name}").emit()
                        yield {"type": "loop_start", "content": node_data}

                    elif event_type == "loop_next": # Next iteration in a loop node [2]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Loop")
                        index = node_data.get("index")
                        await status_event.curry(description=f"Próximo Loop: {node_name} (Índice: {index})").emit()
                        yield {"type": "loop_next", "content": node_data}

                    elif event_type == "loop_completed": # Loop node completed [2]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Loop")
                        status = node_data.get("status")
                        error_msg = node_data.get("error")
                        await status_event.curry(description=f"Loop Concluído: {node_name} (Status: {status})" + (f" Erro: {error_msg}" if error_msg else "")).emit()
                        yield {"type": "loop_finish", "content": node_data}

                    elif event_type == "node_retry": # Node retry event [2]
                        node_data = chunk.get("data", {})
                        node_name = node_data.get("title", "Node")
                        await status_event.curry(description=f"Tentando Novamente Nó: {node_name}").emit()
                        yield {"type": "node_retry", "content": node_data}

                    elif event_type == "text_replace": # Text replacement event [2]
                        await status_event.curry(description="Substituição de Texto...").emit()
                        yield {"type": "text_replace", "content": chunk.get("data", chunk)}

                    elif event_type == "error": # Indicates an exception or error [3]
                        error_msg = chunk.get("message", "Erro desconhecido do Dify")
                        self.logger.error(f"Dify retornou erro: {error_msg}")
                        await status_event.curry(description=f"Erro Dify: {error_msg}").emit()
                        yield {
                            "type": "error",  # OpenWebUI standard error type
                            "content": error_msg,
                        }
                        return  # Terminate the generator on error
                    # For other event types like tts_message, tts_message_end, message_replace,
                    # handle_event already returns them in a suitable format, so we can yield them directly.
                    elif event_type in [
                        "tts_message",
                        "tts_message_end",
                        "message_replace",  
                    ]:
                        await status_event.curry(description="Substituição de Texto...").emit()
                        yield chunk
                    elif event_type == "file_replace":
                        await status_event.curry(description="Substituição de Arquivo...").emit()
                        yield {"type": "file_replace", "content": chunk.get("data", chunk)}
                    
                    else: # Catch any other unexpected event types not explicitly handled
                        self.logger.warning(f"Tipo de evento Dify desconhecido recebido: {event_type}. Dados: {chunk}")
                        # Yielding the raw chunk might be useful for debugging or future compatibility
                        yield {"type": f"dify_unhandled_{event_type}", "content": chunk}


            except aiohttp.ClientError as e:
                error_result = f"Erro de comunicação HTTP com Dify: {str(e)}"
                self.logger.exception(error_result)
                await status_event.curry(description=error_result).emit()
                yield {"type": "error", "content": error_result}
            except asyncio.TimeoutError:
                error_result = "A requisição para Dify excedeu o tempo limite (5 minutos)."
                self.logger.error(error_result)
                await status_event.curry(description=error_result).emit()
                yield {"type": "error", "content": error_result}
            except Exception as e:
                error_result = (
                    f"Um erro inesperado ocorreu durante a interação com o Dify: {str(e)}"
                )
                self.logger.exception(error_result)
                await status_event.curry(description=error_result).emit()
                yield {"type": "error", "content": error_result}



class OpenWebUIHelper:

    def __init__(self, valves: Tools.Valves, debug: bool = False):
        self.valves = valves
        self.logger = logging.getLogger()
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler("openwebui_helper.log")
            formatter = logging.Formatter(
                "%(asctime)s - OpenWebUIHelper - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def get_models(self) -> Optional[List[Dict[str, Any]]]:
        """
        Gets the list of models from the OpenWebUI API.
        NOTE: In a Dify-focused pipeline, this might be redundant or could be
        used to fetch available Dify app models from OpenWebUI's configuration.
        """
        try:
            response = requests.get(
                url=f"{self.valves.WEBUI_BASE_URL}/api/models",
                headers={
                    "Authorization": f"Bearer {self.valves.WEBUI_KEY}",
                },
                timeout=10,  # Add timeout for requests
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            result = response.json()
            self.logger.info("Modelos recuperados com sucesso do OpenWebUI.")
            return result.get("models")
        except requests.exceptions.RequestException as e:
            error_result = f"Erro ao recuperar modelos do OpenWebUI: {e}"
            self.logger.error(error_result)
            return None

    async def get_completion(
        self, query: Dict[str, Any]
    ) -> Optional[str]:  # Query likely a dict for Dify completions
        """
        Posts to the Dify API to get the completion of the query (blocking mode).
        This function is generally not used for streaming in this pipeline; `DifyHelper.send_chat_message` is preferred.
        """
        try:
            response = requests.post(
                url=f"{self.valves.DIFY_BASE_URL}/api/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.valves.DIFY_KEY}",
                    "Content-Type": "application/json",
                },
                json=query,  # query should be a dict payload for Dify
                timeout=60,  # Add timeout for blocking requests
            )
            response.raise_for_status()
            data = response.json()
            # Dify /chat/completions response structure might vary; assuming OpenAI-like for now
            return data["choices"][0]["message"]["content"]
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            error_result = f"Erro ao obter conclusão de Dify (modo bloqueio): {e}, Resposta: {response.text if 'response' in locals() else 'N/A'}"
            self.logger.error(error_result)
            return None


class DifyHelper:

    def __init__(self, valves: Tools.Valves, debug: bool = False):
        self.valves = valves
        self.debug = debug
        self.logger = logging.getLogger()
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler("dify_helper.log")
            formatter = logging.Formatter(
                "%(asctime)s - DifyHelper - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Storage format for mapping OpenWebUI chat/message IDs to Dify IDs:
        # {
        #   "chat_id_1": {
        #     "dify_conversation_id": "xxx",
        #     "message_id_map": {"owui_message_id_1": "dify_message_id_1", ...}
        #   }
        # }
        self.chat_message_mapping = {}

        # Storage format for keeping track of the Dify model used per chat:
        # {
        #   "chat_id_1": "gpt-3.5-turbo",
        #   "chat_id_2": "gpt-4"
        # }
        self.dify_chat_model = {}

        # Storage format for mapping OpenWebUI file IDs to Dify file IDs and their payloads:
        # {
        #   "chat_id_1": {
        #     "owui_file_id_1": {
        #       "local_file_path": "/path/to/file1.pdf",
        #       "dify_file_id": "dify_file_123",
        #       "file_name": "file1.pdf",
        #       "dify_payload": {"type": "document", "transfer_method": "local_file", "upload_file_id": "dify_file_123"}
        #     },
        #     ...
        #   }
        # }
        self.dify_file_list = {}

        self.data_cache_dir = "~/.dify/cache/"  # Directory to persist state

    def get_file_extension(self, file_name: str) -> str:
        """
        Gets the file extension from a filename.
        """
        return (
            os.path.splitext(file_name)[1].strip(".").lower()
        )  # Convert to lowercase for consistent comparison

    async def send_chat_message(
        self,
        query: str,
        user: Optional[str] = None,
        conversation_id: Optional[str] = None,
        response_mode: str = "streaming",
        inputs: Optional[dict] = None,
        files: Optional[List[dict]] = None,
        auto_generate_name: bool = True,
        event_emitter: EventEmitter = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a chat message to the Dify API and handles the streaming response (SSE).

        Args:
            query: The user's input/question content (required).
            user: User identifier, must be unique within the application (required).
            conversation_id: To continue a conversation based on previous chat records.
            response_mode: The mode of response return. Supported: 'streaming' or 'blocking'.
            inputs: Variable values for the app. Contains key/value pairs for template variables.
            files: List of file objects for multimodal understanding.
            auto_generate_name: Whether to auto-generate conversation title.
            event_emitter: Optional event emitter callback for status updates.

        Yields:
            Dictionary containing event data from the streaming response.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Input validation
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        if not user and not self.valves.DIFY_USER:
            raise ValueError("User identifier is required")

        if response_mode not in ("streaming", "blocking"):
            raise ValueError("response_mode must be either 'streaming' or 'blocking'")

        user = user or self.valves.DIFY_USER
        endpoint = f"{self.valves.DIFY_BASE_URL}/chat-messages"

        headers = {
            "Authorization": f"Bearer {self.valves.DIFY_KEY}",
            "Content-Type": "application/json",
            "Accept": (
                "text/event-stream"
                if response_mode == "streaming"
                else "application/json"
            ),
        }

        # Prepare payload according to Dify API spec
        payload = {
            "query": query,
            "user": user,
            "response_mode": response_mode,
            "inputs": inputs or {},
            "auto_generate_name": auto_generate_name,
        }

        if conversation_id:
            if not isinstance(conversation_id, str) or not conversation_id.strip():
                raise ValueError("conversation_id must be a non-empty string")
            payload["conversation_id"] = conversation_id

        if files:
            if not isinstance(files, list):
                raise ValueError("files must be a list of file objects")

            # Validate each file object structure
            valid_file_types = {
                "document": {
                    "TXT",
                    "MD",
                    "MARKDOWN",
                    "PDF",
                    "HTML",
                    "XLSX",
                    "XLS",
                    "DOCX",
                    "CSV",
                    "EML",
                    "MSG",
                    "PPTX",
                    "PPT",
                    "XML",
                    "EPUB",
                },
                "image": {"JPG", "JPEG", "PNG", "GIF", "WEBP", "SVG"},
                "audio": {"MP3", "M4A", "WAV", "WEBM", "AMR"},
                "video": {"MP4", "MOV", "MPEG", "MPGA"},
                "custom": set(),  # Any extension is allowed for custom type
            }

            for file_obj in files:
                if not isinstance(file_obj, dict):
                    raise ValueError(
                        "Each file must be a dictionary with required fields"
                    )

                file_type = file_obj.get("type")
                if file_type not in valid_file_types:
                    raise ValueError(
                        f"Invalid file type. Must be one of: {', '.join(valid_file_types.keys())}"
                    )

                transfer_method = file_obj.get("transfer_method")
                if transfer_method not in ("remote_url", "local_file"):
                    raise ValueError(
                        "transfer_method must be either 'remote_url' or 'local_file'"
                    )

                if transfer_method == "remote_url" and "url" not in file_obj:
                    raise ValueError(
                        "url is required when transfer_method is 'remote_url'"
                    )
                elif (
                    transfer_method == "local_file" and "upload_file_id" not in file_obj
                ):
                    raise ValueError(
                        "upload_file_id is required when transfer_method is 'local_file'"
                    )

            payload["files"] = files

        self.logger.debug(
            f"Sending payload to Dify: {json.dumps(payload, indent=2, default=str)}"
        )

        try:
            # Validate API key before proceeding
            if (
                not hasattr(self.valves, "DIFY_KEY")
                or not self.valves.DIFY_KEY
                or not isinstance(self.valves.DIFY_KEY, str)
                or not self.valves.DIFY_KEY.strip()
            ):
                error_msg = "DIFY_KEY is not properly configured. Please check your environment variables."
                self.logger.error(error_msg)
                raise ValueError(error_msg)


            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),  # 5 minutes timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(
                            f"Dify API request failed with status {response.status}: {error_text}"
                        )

                        try:
                            error_data = json.loads(error_text)
                            error_code = error_data.get("code", "")
                            error_msg = error_data.get("message", error_text)

                            # Map common error codes to specific exceptions
                            if response.status == 400:
                                if "invalid_param" in error_code:
                                    raise ValueError(f"Invalid parameters: {error_msg}")
                                elif "app_unavailable" in error_code:
                                    raise RuntimeError(
                                        "App configuration is not available"
                                    )
                                elif "provider_not_initialize" in error_code:
                                    raise RuntimeError(
                                        "No available model credential configuration"
                                    )
                            elif response.status == 404 and "conversation" in error_code:
                                raise ValueError("Conversation not found")
                            elif response.status == 429:
                                raise RuntimeError(
                                    "Rate limit exceeded. Please try again later."
                                )

                            raise Exception(
                                f"API Error ({response.status}): {error_msg}"
                            )

                        except json.JSONDecodeError:
                            raise Exception(
                                f"API Error ({response.status}): {error_text}"
                            )

                    # For blocking mode, return the single JSON response
                    if response_mode == "blocking":
                        try:
                            result = await response.json()
                            self.logger.debug("Dify blocking mode response: %s", result)
                            yield result
                            return
                        except json.JSONDecodeError as e:
                            raise ValueError(
                                f"Failed to parse response as JSON: {str(e)}"
                            )

                    # For streaming mode, process the SSE stream
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line:
                            continue

                        if line.startswith("data: "):
                            try:
                                payload = json.loads(
                                    line[6:]
                                )  # Remove 'data: ' prefix
                                event_type = payload.get("event")
                                event_data = payload.get("data", {})

                                # Extract chat_id and message_id from event emitter closure
                                closure_info = event_emitter.get_closure_info()
                                if closure_info:
                                    chat_id = closure_info.get("chat_id")
                                    message_id = closure_info.get("message_id")
                                else:
                                    chat_id = ""
                                    message_id = ""

                                # Process the Dify event and yield a normalized event
                                # {
                                #     "process_data": None,
                                #     "outputs": {
                                #         "depth": None,
                                #         "sys.query": "research about cat memes",
                                #         "sys.files": [],
                                #         "sys.conversation_id": "f965a860-717f-4be0-9fef-e49b57137716",
                                #         "sys.user_id": "test@example.com",
                                #         "sys.dialogue_count": 0,
                                #         "sys.app_id": "f10172d5-169d-4003-926c-9dfbfa5ab985",
                                #         "sys.workflow_id": "f2f20deb-4b6f-4edd-b08a-c20538aeb204",
                                #         "sys.workflow_run_id": "b007f4fd-33b6-4ed2-9fc8-1c31d03ec0a4"
                                #     },
                                #     "status": "succeeded",
                                #     "error": None,
                                #     "elapsed_time": 0.07908,
                                #     "execution_metadata": None,
                                #     "created_at": 1752611213,
                                #     "finished_at": 1752611213,
                                #     "files": [],
                                #     "parallel_id": None,
                                #     "parallel_start_node_id": None,
                                #     "parent_parallel_id": None,
                                #     "parent_parallel_start_node_id": None,
                                #     "iteration_id": None,
                                #     "loop_id": None
                                # }

                                processed_event = self.handle_event(
                                    event_data, event_type, event_emitter, chat_id, message_id
                                )
                                if processed_event:
                                    self.logger.debug(
                                        f"Processed Dify event: {processed_event}"
                                    )
                                    yield event_data

                            except json.JSONDecodeError as e:
                                self.logger.error(
                                    f"Failed to parse Dify event data: {line}. Error: {e}"
                                )
                                yield {
                                    "type": "error",
                                    "message": f"Failed to parse event data: {line[:100]}...",
                                }

        except asyncio.TimeoutError:
            self.logger.error("Dify request timed out after 5 minutes")
            yield {
                "type": "error",
                "message": "Request timed out after 5 minutes. Please try again.",
            }
        except aiohttp.ClientError as e:
            self.logger.error(
                f"HTTP client error while communicating with Dify: {str(e)}",
                exc_info=True,
                                )
            yield {"type": "error", "message": f"Network communication error: {str(e)}"}
        except Exception as e:
            self.logger.error(
                f"Unexpected error during Dify interaction: {str(e)}", exc_info=True
            )
            yield {
                "type": "error",
                "message": f"An unexpected error occurred: {str(e)}",
            }

    def handle_event(
        self, event_content: dict, event_type: str, event_emitter: EventEmitter, chat_id: str, message_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normalizes and filters event types from Dify API for OpenWebUI consumption.
        """
        self.logger.debug(f"Processing event type: {event_type}")
        
        # Update conversation and message IDs as soon as they are available from Dify
        if dify_conversation_id := event_content.get("conversation_id"):
            self.chat_message_mapping[dify_conversation_id]["conversation_id"] = dify_conversation_id
            self.logger.debug(f"Dify conversation ID mapped: {conversation_id} -> {dify_conversation_id}")

        if dify_message_id := event_content.get("message_id"):
            self.chat_message_mapping[dify_message_id]["message_id"] = dify_message_id
            self.logger.debug(f"Dify message ID mapped: {message_id} -> {dify_message_id}")


        event_type_map = {
            "message": self.handle_message,
            "agent_message": self.handle_agent_message,
            "text": self.handle_text,
            "file": self.handle_file,
            "message_end": self.handle_message_end,
            "workflow_started": self.handle_workflow_start,
            "node_started": self.handle_node_start,
            "node_finished": self.handle_node_finish,
            "workflow_finished": self.handle_workflow_finish,
            "loop_started": self.handle_loop_start,
            "loop_finished": self.handle_loop_finish,
            "node_retry": self.handle_node_retry,
            "text_replace": self.handle_text_replace,
            "error": self.handle_error,
        }

        handler = event_type_map.get(event_type)
        if not handler:
            self.logger.warning(f"Unknown event type: {event_type}")
            return None

        return handler(event_content, event_emitter, chat_id, message_id)
    
    def handle_text(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo texto parcial do Dify...")
        self.logger.debug(f"Recebendo texto parcial do Dify: {event_content}")
        return event_content

    def handle_message(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo resposta do Dify...")
        self.logger.debug(f"Recebendo resposta do Dify: {event_content}")
        return event_content

    def handle_agent_message(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo resposta do agente...")
        self.logger.debug(f"Recebendo resposta do agente: {event_content}")
        return event_content

    def handle_file(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo arquivo do Dify...")
        self.logger.debug(f"Recebendo arquivo do Dify: {event_content}")
        return event_content

    def handle_message_end(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo fim da mensagem do Dify...")
        self.logger.debug(f"Recebendo fim da mensagem do Dify: {event_content}")
        return event_content

    def handle_workflow_start(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo início do fluxo de trabalho do Dify...")
        self.logger.debug(f"Recebendo início do fluxo de trabalho do Dify: {event_content}")
        return event_content

    def handle_node_start(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo início do nó do Dify...")
        self.logger.debug(f"Recebendo início do nó do Dify: {event_content}")
        return event_content

    def handle_node_finish(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo fim do nó do Dify...")
        self.logger.debug(f"Recebendo fim do nó do Dify: {event_content}")
        return event_content

    def handle_workflow_finish(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo fim do fluxo de trabalho do Dify...")
        self.logger.debug(f"Recebendo fim do fluxo de trabalho do Dify: {event_content}")
        return event_content
    
    def handle_loop_start(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo início do loop do Dify...")
        self.logger.debug(f"Recebendo início do loop do Dify: {event_content}")
        return event_content

    def handle_loop_finish(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo fim do loop do Dify...")
        self.logger.debug(f"Recebendo fim do loop do Dify: {event_content}")
        return event_content

    def handle_node_retry(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo retry do nó do Dify...")
        self.logger.debug(f"Recebendo retry do nó do Dify: {event_content}")
        return event_content

    def handle_text_replace(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo replace do texto do Dify...")
        self.logger.debug(f"Recebendo replace do texto do Dify: {event_content}")
        return event_content

    def handle_error(self, event_content: dict, event_emitter: EventEmitter, chat_id: str, message_id: str):
        event_emitter.progress_update(f"Recebendo erro do Dify...")
        self.logger.debug(f"Recebendo erro do Dify: {event_content}")
        return event_content

    def save_state(self):
        """Persists Dify related state variables to file."""
        try:
            os.makedirs(self.data_cache_dir, exist_ok=True)
        except PermissionError as e:
            self.logger.error(
                f"Erro de permissão ao criar o diretório de cache '{self.data_cache_dir}': {e}. Verifique as permissões de gravação no local de execução do script ou execute-o de um diretório com permissões adequadas."
            )
            # Optionally, you might want to raise the error or return here if persistence is critical
            # For now, we'll log and continue, meaning state might not be saved.
            return  # Exit if directory creation fails due to permissions
        except Exception as e:
            self.logger.error(
                f"Falha ao criar o diretório de cache '{self.data_cache_dir}': {e}",
                exc_info=True,
            )
            return  # Exit if directory creation fails for other reasons

        try:
            with open(
                os.path.join(self.data_cache_dir, "chat_message_mapping.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.chat_message_mapping, f, ensure_ascii=False, indent=2)
            self.logger.info("Estado 'chat_message_mapping' salvo.")

            with open(
                os.path.join(self.data_cache_dir, "chat_model.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.dify_chat_model, f, ensure_ascii=False, indent=2)
            self.logger.info("Estado 'chat_model' salvo.")

            with open(
                os.path.join(self.data_cache_dir, "file_list.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.dify_file_list, f, ensure_ascii=False, indent=2)
            self.logger.info("Estado 'dify_file_list' salvo.")

        except Exception as e:
            self.logger.error(
                f"Falha ao salvar arquivos de estado do Dify: {e}", exc_info=True
            )

    def load_state(self):
        """Loads Dify related state variables from files."""
        try:
            chat_mapping_file = os.path.join(
                self.data_cache_dir, "chat_message_mapping.json"
            )
            if os.path.exists(chat_mapping_file):
                with open(chat_mapping_file, "r", encoding="utf-8") as f:
                    self.chat_message_mapping = json.load(f)
                self.logger.info("Estado 'chat_message_mapping' carregado.")
            else:
                self.chat_message_mapping = {}
                self.logger.info(
                    "'chat_message_mapping.json' não encontrado, inicializando vazio."
                )

            chat_model_file = os.path.join(self.data_cache_dir, "chat_model.json")
            if os.path.exists(chat_model_file):
                with open(chat_model_file, "r", encoding="utf-8") as f:
                    self.dify_chat_model = json.load(f)
                self.logger.info("Estado 'chat_model' carregado.")
            else:
                self.dify_chat_model = {}
                self.logger.info(
                    "'chat_model.json' não encontrado, inicializando vazio."
                )

            file_list_file = os.path.join(self.data_cache_dir, "file_list.json")
            if os.path.exists(file_list_file):
                with open(file_list_file, "r", encoding="utf-8") as f:
                    self.dify_file_list = json.load(f)
                self.logger.info("Estado 'dify_file_list' carregado.")
            else:
                self.dify_file_list = {}
                self.logger.info(
                    "'file_list.json' não encontrado, inicializando vazio."
                )

        except Exception as e:
            self.logger.error(
                f"Falha ao carregar arquivos de estado do Dify: {e}. Redefinindo estado.",
                exc_info=True,
            )
            self.chat_message_mapping = {}
            self.dify_chat_model = {}
            self.dify_file_list = {}

    def get_models(self) -> List[Dict[str, str]]:
        """
        Retrieves the list of DIFY models supported by this pipeline.
        This can be extended to dynamically fetch from Dify if an API for listing models is available.
        """
        # For simplicity, returning a hardcoded list matching the example.
        # In a real scenario, this would likely fetch available Dify Apps.
        return [
            {"id": "deepseek-r1", "name": "deepseek-r1"},
            # Add other Dify app IDs/names if your Dify instance supports multiple or you want to expose them.
        ]

    def upload_file(
        self, user_id: str, file_path: str, mime_type: str, max_size_mb: int = 10
    ) -> str:
        """
        Uploads a file to the Dify server and returns the file ID.

        Args:
            user_id: The ID of the user uploading the file
            file_path: Local path to the file being uploaded
            mime_type: The MIME type of the file
            max_size_mb: Maximum allowed file size in MB (default: 10MB)

        Returns:
            str: The file ID returned by the Dify server

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is empty or exceeds size limit
            requests.HTTPError: For API request failures with specific error messages
        """
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Cannot upload an empty file")

        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(
                f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            )

        url = f"{self.valves.DIFY_BASE_URL}/files/upload"
        headers = {
            "Authorization": f"Bearer {self.valves.DIFY_KEY}",
        }

        file_name = os.path.basename(file_path)

        try:
            with open(file_path, "rb") as f_data:
                files = {
                    "file": (file_name, f_data, mime_type),
                    "user": (None, user_id),
                }
                self.logger.info(
                    f"Uploading file to Dify: {file_name} ({mime_type}, {file_size} bytes) for user {user_id}"
                )

                response = requests.post(url, headers=headers, files=files, timeout=60)

                # Handle specific error responses
                if response.status_code == 400:
                    error_data = response.json()
                    error_code = error_data.get("code", "")
                    if "no_file_uploaded" in error_code:
                        raise ValueError("No file was provided in the request")
                    elif "too_many_files" in error_code:
                        raise ValueError("Only one file can be uploaded at a time")
                    elif "unsupported_file_type" in error_code:
                        raise ValueError(
                            "Unsupported file type. Please check the allowed file types."
                        )
                elif response.status_code == 413:
                    raise ValueError("File size exceeds the maximum allowed limit")
                elif response.status_code == 415:
                    raise ValueError("Unsupported file type")
                elif response.status_code == 503:
                    error_data = response.json()
                    error_code = error_data.get("code", "")
                    if "s3_connection_failed" in error_code:
                        raise ConnectionError("Unable to connect to storage service")
                    elif "s3_permission_denied" in error_code:
                        raise PermissionError(
                            "Insufficient permissions to upload files"
                        )
                    elif "s3_file_too_large" in error_code:
                        raise ValueError("File size exceeds storage service limit")

                response.raise_for_status()  # Handle any other HTTP errors

                file_data = response.json()
                file_id = file_data["id"]
                self.logger.info(
                    f"Successfully uploaded file to Dify. File ID: {file_id}"
                )
                return file_id

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to upload file: {str(e)}")
            raise

    def upload_text_file(self, user_id: str, file_path: str) -> str:
        """
        Uploads a text file to Dify. Dify's upload endpoint handles various text types.
        """
        # Determine MIME type based on extension, or default
        mime_type = "text/plain"
        ext = self.get_file_extension(file_path)
        if ext == "csv":
            mime_type = "text/csv"
        elif ext == "json":
            mime_type = "application/json"
        elif ext == "md":
            mime_type = "text/markdown"
        elif ext == "xml":
            mime_type = "application/xml"

        self.logger.debug(
            f"Uploading text file: {file_path} with MIME type: {mime_type}"
        )
        return self.upload_file(user_id, file_path, mime_type)

    def upload_images(self, image_url_or_base64: str, user_id: str) -> str:
        """
        Uploads an image to the Dify server. Supports base64 or remote URLs.
        If base64, it decodes and saves it temporarily before uploading.
        If a remote URL, it tries to download it first.
        Returns the Dify file ID.
        """
        if image_url_or_base64.startswith("data:"):
            # Base64 image
            header, encoded = image_url_or_base64.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            ext = mime_type.split("/")[-1]
            image_data = base64.b64decode(encoded)

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{ext}"
            ) as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            self.logger.info(f"Base64 image saved temporarily at: {temp_file_path}")

            try:
                file_id = self.upload_file(user_id, temp_file_path, mime_type)
                return file_id
            finally:
                os.unlink(temp_file_path)  # Clean up the temporary file
        else:
            # Assume it's a remote URL for direct Dify processing or requires download
            # For simplicity, if Dify's API for files/upload requires actual file content
            # we would download it first. If it accepts a remote URL directly in the `files` payload
            # with transfer_method: remote_url, then this function might not be strictly necessary
            # for that case, and the URL would be passed directly in the payload.
            # As per Dify docs, 'upload_file_id' for local_file and 'url' for remote_url,
            # so this `upload_images` is primarily for local files (incl. decoded base64).
            self.logger.warning(
                "Upload of image via remote URL is normally handled directly in the Dify payload, not via file upload."
            )
            raise ValueError(
                "The upload_images DifyHelper is intended for base64 images or local files; remote URLs are passed directly."
            )

    def is_doc_file(self, file_path: str) -> bool:
        """Checks if the file is a supported document type."""
        ext = self.get_file_extension(file_path)
        return ext in ["pdf", "docx", "pptx", "xlsx", "txt", "csv", "json", "md", "xml"]

    def is_text_file(self, mime_type: str) -> bool:
        """Checks if the file is a supported text type by MIME."""
        return mime_type.startswith("text/") or mime_type in [
            "application/json",
            "application/xml",
        ]

    def is_audio_file(self, file_path: str) -> bool:
        """Checks if the file is a supported audio type."""
        ext = self.get_file_extension(file_path)
        return ext in ["mp3", "wav", "flac", "aac", "ogg"]

    def is_image_file(self, file_path: str) -> bool:
        """Checks if the file is a supported image type."""
        ext = self.get_file_extension(file_path)
        return ext in ["jpg", "jpeg", "png", "gif", "webp"]


# --- Funções de Callback para Simulação Local de Eventos do OpenWebUI ---


async def real_owui_event_sink(event_dict):
    """Um callback que REALIZA a função real de recebimento de eventos do OpenWebUI."""
    print(f"\n--- Evento PRINCIPAL do OWUI Recebido ---")
    print(json.dumps(event_dict, indent=2))
    print("--------------------------------------")


async def mock_owui_event_callback(event_dict):
    """Um mock para a função __event_emitter__ que simula a recepção de eventos do OpenWebUI."""
    print(f"\n--- Evento MOCK do OWUI Recebido ---")
    print(json.dumps(event_dict, indent=2))
    print("-----------------------------------")


class MockEventEmitter:
    def __init__(self, request_info_data):
        self._request_info = request_info_data # The data to be captured

    async def __call__(self, event_data):
        # In a real Open WebUI environment, this would send an event to the UI
        print(f"Emitting event: {event_data}")
        return event_data

    @property
    def __closure__(self):
        # This is where the magic happens for demonstration
        # In a real scenario, the __closure__ would be naturally created
        # if MockEventEmitter was a nested function or had a cell object
        # for _request_info. For demonstration, we're simulating it.
        class Cell:
            def __init__(self, content):
                self.cell_contents = content
        return (Cell(self._request_info),)

# --- Bloco Principal de Execução para Testes Locais ---
if __name__ == "__main__":
    # Carregar variáveis de ambiente do .env
    dotenv.load_dotenv()

    # Configuração de argumentos CLI para depuração e desativação de eventos
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute o Dify Manifold Pipe localmente para teste."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Ativar modo de depuração."
    )
    parser.add_argument(
        "--disable-events",
        action="store_true",
        help="Usar um mock de evento para OpenWebUI (não envia para o emitter real).",
    )
    args = parser.parse_args()

    # Selecionar o callback de evento com base nos argumentos    
    if args.disable_events:
        event_emitter_to_use = mock_owui_event_callback
        print("\n--- MODO DE EVENTOS: MOCK (SAÍDA DE EVENTOS PARA CONSOLE) ---")
        print("    Eventos serão impressos no console por um callback mock.")
    else:
        event_emitter_to_use = MockEventEmitter({"chat_id": "test_chat_123", "message_id": "test_message_456"})
        print("\n--- MODO DE EVENTOS: REAL (SAÍDA DE EVENTOS PARA CONSOLE) ---")
        print(
            "    Eventos serão impressos no console, simulando a recepção pelo OpenWebUI."
        )
    print("----------------------------------------------------------------\n")

    # Instanciar a classe Tools com base no modo de depuração
    tools = Tools(debug=args.debug)

    # Exemplo de corpo da requisição (como seria enviado pelo OpenWebUI)
    # Adapte este dicionário para testar diferentes cenários.
    sample_body = {
        "model": "dify.deepseek-r1",  # Use o ID do seu aplicativo Dify
        "messages": [
            {"role": "user", "content": "research about cat memes"}
            # Adicione mais mensagens para simular o histórico da conversa
            # {"id": "msg_001", "role": "assistant", "content": "A capital da França é Paris."},
            # {"id": "msg_002", "role": "user", "content": "E qual a da Alemanha?"}
        ],
        "chat_id": "test_chat_123",  # ID de chat simulado
        "message_id": "test_message_456",  # ID de mensagem simulado
        "upload_files": [],  # Adicione objetos de arquivo aqui se for testar upload
    }

    # Exemplo de corpo da requisição com imagem base64 (substitua com uma imagem real se for testar)
    # image_data_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" # Um pixel PNG transparente
    # sample_body_with_image = {
    #     "model": "dify.deepseek-r1",
    #     "messages": [
    #         {"role": "user", "content": [
    #             {"type": "text", "text": "Descreva esta imagem:"},
    #             {"type": "image_url", "image_url": {"url": image_data_base64}}
    #         ]}
    #     ],
    #     "chat_id": "test_chat_image_789",
    #     "message_id": "test_message_image_1011"
    # }

    # Exemplo de corpo da requisição com arquivo (crie um arquivo dummy para testar)
    # with open("dummy_test_file.txt", "w") as f:
    #     f.write("Este é um arquivo de teste para upload.")
    # sample_body_with_file = {
    #     "model": "dify.deepseek-r1",
    #     "messages": [
    #         {"role": "user", "content": "Analise este arquivo."}
    #     ],
    #     "chat_id": "test_chat_file_abc",
    #     "message_id": "test_message_file_def",
    #     "upload_files": [
    #         {
    #             "id": "file_owui_123",
    #             "type": "file",
    #             "file": {
    #                 "id": "dummy_file_id",
    #                 "filename": "dummy_test_file.txt",
    #                 "path": "dummy_test_file.txt", # O pipeline vai tentar encontrar neste caminho
    #                 "meta": {"content_type": "text/plain", "size": os.path.getsize("dummy_test_file.txt")}
    #             }
    #         }
    #     ]
    # }

    async def run_test(event_emitter_to_use):
        print("\n--- Executando o Pipe com requisição de exemplo ---")
        full_response_content = ""
        try:
            # Iterar sobre a resposta assíncrona do pipe
            if tools.debug:
                print(
                    "\n--- Iniciando a iteração sobre a resposta assíncrona do pipe ---"
                )
            async for chunk in tools.pipe(
                sample_body,
                __event_emitter__= event_emitter_to_use,
                __user__={"email": "test@example.com"},
            ):
                if chunk["type"] == "text":
                    if tools.debug:
                        print(f"{chunk['content']}", end="")
                    full_response_content += chunk["content"]
                elif chunk["type"] == "error":
                    if tools.debug:
                        print(f"\nErro recebido: {chunk['content']}")
                    break
                elif chunk["type"] == "message_end":
                    if tools.debug:
                        print(f"\n--- Fim da mensagem ---")
                        print(f"Uso (Dify): {chunk['content'].get('usage')}")
                        print(f"Metadata (Dify): {chunk['content'].get('metadata')}")
                    break  # Terminar após o fim da mensagem principal
                else:
                    print(
                        f"\nEvento não textual recebido: {json.dumps(chunk, indent=2)}"
                    )
            print("\n--- Resposta completa do Pipe ---")
            print(full_response_content)

        except Exception as e:
            print(f"\nOcorreu uma exceção durante a execução do pipe: {e}")
            logging.exception("Exceção no bloco principal de execução.")

    # Executar o teste
    asyncio.run(run_test(event_emitter_to_use=event_emitter_to_use))

    # Limpar o arquivo dummy se foi criado
    # if os.path.exists("dummy_test_file.txt"):
    #     os.unlink("dummy_test_file.txt")