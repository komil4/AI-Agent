from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List

class ChatMessage(BaseModel):
    message: str
    use_react: bool = False  # Флаг для использования ReAct агента

class ChatResponse(BaseModel):
    response: str
    status: str

class ErrorResponse(BaseModel):
    error: str
    status: str

class ServiceStatus(BaseModel):
    status: str
    url: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    available_models: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, ServiceStatus]
    timestamp: str

# Auth models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user_info: Optional[Dict[str, Any]] = None

class UserInfo(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    groups: List[str] = []

class LogoutResponse(BaseModel):
    success: bool
    message: str

# Admin models
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str

class AdminPasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class AdminPasswordChangeResponse(BaseModel):
    success: bool
    message: str

class ConfigUpdateRequest(BaseModel):
    section: str
    settings: Dict[str, Any]

class ConfigUpdateResponse(BaseModel):
    success: bool
    message: str

class ConnectionTestRequest(BaseModel):
    service: str

class ConnectionTestResponse(BaseModel):
    success: bool
    message: str

class AdminInfo(BaseModel):
    username: str
    created_at: str
    last_login: Optional[str] = None
    password_changed_at: Optional[str] = None

# Code Analysis models
class CodeAnalysisRequest(BaseModel):
    task_key: str

class CodeAnalysisResponse(BaseModel):
    success: bool
    message: str
    report: Optional[str] = None

# LLM Configuration Models
class LLMProviderConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    model: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30

class LLMConfigRequest(BaseModel):
    provider: str
    providers: Dict[str, LLMProviderConfig]

class LLMConfigResponse(BaseModel):
    success: bool
    message: str
    config: Optional[Dict[str, Any]] = None

class LLMProviderTestRequest(BaseModel):
    provider: str
    message: Optional[str] = "Привет! Это тестовое сообщение."

class LLMProviderTestResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None
