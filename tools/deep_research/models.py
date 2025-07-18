from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime

class FileType(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"

class FileMetadata(BaseModel):
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DifyFile(BaseModel):
    id: str
    local_path: Optional[str] = None
    remote_id: Optional[str] = None
    type: FileType
    metadata: FileMetadata
    dify_payload: Optional[Dict[str, Any]] = None

class MessageContent(BaseModel):
    text: str
    files: List[DifyFile] = []

class Conversation(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    model: Optional[str] = None
    messages: List[Dict[str, str]] = []  # Maps message IDs between systems

class DifyAPIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: int