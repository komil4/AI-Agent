import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from mcp_servers.jira_server import JiraMCPServer
from mcp_servers.atlassian_server import AtlassianMCPServer
from mcp_servers.gitlab_server import GitLabMCPServer
from mcp_servers.onec_server import OneCMCPServer
from llm_client import LLMClient
from database import init_database
from chat_service import chat_service
from models import (
    ChatMessage, ChatResponse, ErrorResponse, HealthResponse, ServiceStatus,
    LoginRequest, LoginResponse, UserInfo, LogoutResponse,
    AdminLoginRequest, AdminLoginResponse, AdminPasswordChangeRequest, 
    AdminPasswordChangeResponse, ConfigUpdateRequest, ConfigUpdateResponse,
    ConnectionTestRequest, ConnectionTestResponse, AdminInfo,
    CodeAnalysisRequest, CodeAnalysisResponse,
    LLMConfigRequest, LLMConfigResponse, LLMProviderTestRequest, LLMProviderTestResponse
)
from auth.ad_auth import ADAuthenticator
from auth.session_manager import SessionManager
from auth.middleware import AuthMiddleware
from auth.admin_auth import AdminAuth
from config.config_manager import ConfigManager
from analyzers.code_analyzer import CodeAnalyzer
from mcp_client import mcp_client, MCPClient
from config.llm_config import LLMProvider

def reinitialize_system():
    """Переинициализирует все компоненты системы"""
    global llm_client, mcp_client, config_manager
    
    try:
        print("🔄 Переинициализация системы...")
        
        # Перезагружаем конфигурацию
        config_manager = ConfigManager()
        
        # Перезагружаем LLM клиент с провайдером по умолчанию
        llm_client = LLMClient()
        
        # Перезагружаем MCP клиент
        mcp_client = MCPClient()
        
        # Логируем информацию о текущем провайдере
        current_provider = llm_client.get_current_provider()
        print(f"✅ Система переинициализирована, текущий LLM провайдер: {current_provider}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка переинициализации: {e}")
        return False

def validate_provider_config(provider_name: str, config: dict) -> dict:
    """Валидирует конфигурацию провайдера LLM"""
    validated = {}
    
    # Общие поля для всех провайдеров
    validated['enabled'] = bool(config.get('enabled', False))
    validated['temperature'] = max(0.0, min(2.0, float(config.get('temperature', 0.7))))
    validated['max_tokens'] = max(1, min(100000, int(config.get('max_tokens', 4000))))
    validated['timeout'] = max(1, min(300, int(config.get('timeout', 30))))
    
    # Специфичные поля для каждого провайдера
    if provider_name == 'openai':
        validated['api_key'] = str(config.get('api_key', ''))
        validated['model'] = str(config.get('model', 'gpt-4o-mini'))
        validated['base_url'] = str(config.get('base_url', 'https://api.openai.com/v1'))
    elif provider_name == 'anthropic':
        validated['api_key'] = str(config.get('api_key', ''))
        validated['model'] = str(config.get('model', 'claude-3-5-sonnet-20241022'))
        validated['base_url'] = str(config.get('base_url', 'https://api.anthropic.com'))
    elif provider_name == 'google':
        validated['api_key'] = str(config.get('api_key', ''))
        validated['model'] = str(config.get('model', 'gemini-1.5-flash'))
        validated['base_url'] = str(config.get('base_url', 'https://generativelanguage.googleapis.com'))
    elif provider_name == 'ollama':
        validated['base_url'] = str(config.get('base_url', 'http://localhost:11434'))
        validated['model'] = str(config.get('model', 'llama3.1:8b'))
    elif provider_name == 'local':
        validated['base_url'] = str(config.get('base_url', 'http://localhost:8000'))
        validated['model'] = str(config.get('model', 'local'))
    
    return validated

# Загружаем переменные окружения
load_dotenv()

# Создаем FastAPI приложение
app = FastAPI(
    title="AI Ассистент с MCP Серверами",
    description="Веб-приложение с чат-ботом LLM и MCP серверами для Jira, Atlassian и GitLab",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация сервисов
def init_services():
    """Инициализирует все сервисы"""
    global jira_server, atlassian_server, gitlab_server, onec_server, llm_client, ad_auth, session_manager, admin_auth, config_manager, code_analyzer
    
    # MCP серверы
    jira_server = JiraMCPServer()
    atlassian_server = AtlassianMCPServer()
    gitlab_server = GitLabMCPServer()
    onec_server = OneCMCPServer()
    
    # LLM клиент
    llm_client = LLMClient()
    
    # Аутентификация
    ad_auth = ADAuthenticator()
    session_manager = SessionManager()
    admin_auth = AdminAuth()
    config_manager = ConfigManager()
    code_analyzer = CodeAnalyzer()

# Инициализируем сервисы
init_services()

# Добавляем middleware для аутентификации после инициализации сервисов
app.add_middleware(AuthMiddleware, session_manager=session_manager)

# Инициализируем MCP клиент при запуске
@app.on_event("startup")
async def startup_event():
    """Инициализация MCP клиента при запуске приложения"""
    try:
        # Инициализируем базу данных
        database_url = config_manager.get_database_url()
        init_database(database_url)
        logger.info("✅ База данных инициализирована")
        
        # Инициализируем MCP клиент
        await mcp_client.initialize_servers()
        logger.info("✅ Упрощенный MCP клиент инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие MCP сессий при остановке приложения"""
    try:
        await mcp_client.close_all_sessions()
        logger.info("✅ MCP сессии закрыты")
    except Exception as e:
        logger.error(f"❌ Ошибка закрытия MCP сессий: {e}")

# Универсальная функция для получения пользователя из сессии
async def get_user_from_session(request: Request) -> dict:
    """Получает информацию о пользователе из сессии (универсальный механизм)"""
    # Получаем session_id из cookies
    session_id = request.cookies.get('session_id')
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    
    # Проверяем сессию
    session_data = session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия истекла"
        )
    
    user_info = session_data.get('user_info')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Информация о пользователе не найдена"
        )
    
    return user_info

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Страница входа"""
    with open("templates/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Аутентификация пользователя через Active Directory или admin"""
    try:
        # Сначала проверяем, не admin ли это
        if login_data.username.lower() == "admin":
            # Проверяем пароль admin
            if admin_auth.authenticate_admin(login_data.username, login_data.password):
                # Создаем пользователя admin
                user_info = {
                    "username": "admin",
                    "display_name": "Administrator",
                    "email": "admin@localhost",
                    "groups": ["admin"],
                    "is_admin": True
                }
                
                # Создаем JWT токен
                access_token = ad_auth.create_access_token(user_info)
                
                # Создаем сессию
                session_id = session_manager.create_session(user_info, access_token)
                
                # Создаем ответ с cookie
                response = LoginResponse(
                    success=True,
                    message="Успешная аутентификация admin",
                    user_info=user_info
                )
                
                # Устанавливаем cookie с session_id
                from fastapi.responses import JSONResponse
                json_response = JSONResponse(
                    content=response.dict(),
                    status_code=200
                )
                json_response.set_cookie(
                    key="session_id",
                    value=session_id,
                    httponly=True,
                    secure=False,  # Установите True для HTTPS
                    samesite="lax",
                    max_age=24*60*60  # 24 часа
                )
                
                return json_response
        
        # Аутентификация через AD
        user_info = ad_auth.authenticate_user(login_data.username, login_data.password)
        
        if not user_info:
            return LoginResponse(
                success=False,
                message="Неверные учетные данные или пользователь не найден в Active Directory"
            )
        
        # Создаем JWT токен
        access_token = ad_auth.create_access_token(user_info)
        
        # Создаем сессию
        session_id = session_manager.create_session(user_info, access_token)
        
        # Создаем ответ с cookie
        response = LoginResponse(
            success=True,
            message="Успешная аутентификация",
            user_info=user_info
        )
        
        # Устанавливаем cookie с session_id
        from fastapi.responses import JSONResponse
        json_response = JSONResponse(
            content=response.dict(),
            status_code=200
        )
        json_response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  # Установите True для HTTPS
            samesite="lax",
            max_age=24*60*60  # 24 часа
        )
        
        return json_response
    
    except Exception as e:
        return LoginResponse(
            success=False,
            message=f"Ошибка аутентификации: {str(e)}"
        )

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Выход пользователя"""
    try:
        session_id = request.cookies.get('session_id')
        if session_id:
            session_manager.delete_session(session_id)
        
        # Создаем ответ с удалением cookie
        from fastapi.responses import JSONResponse
        response = LogoutResponse(
            success=True,
            message="Успешный выход из системы"
        )
        
        json_response = JSONResponse(
            content=response.dict(),
            status_code=200
        )
        # Удаляем cookie
        json_response.delete_cookie(key="session_id")
        
        return json_response
    except Exception as e:
        return LogoutResponse(
            success=False,
            message=f"Ошибка выхода: {str(e)}"
        )

@app.get("/api/auth/me")
async def get_current_user_info(request: Request):
    """Получение информации о текущем пользователе"""
    try:
        # Используем универсальную функцию для получения пользователя
        user_info = await get_user_from_session(request)
        
        return UserInfo(
            username=user_info['username'],
            display_name=user_info['display_name'],
            email=user_info.get('email'),
            groups=user_info.get('groups', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о пользователе: {str(e)}"
        )

# Admin Panel Endpoints
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Админ-панель"""
    with open("templates/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/admin/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLoginRequest):
    """Аутентификация админа"""
    try:
        success = admin_auth.authenticate_admin(login_data.username, login_data.password)
        
        if success:
            return AdminLoginResponse(
                success=True,
                message="Успешный вход в админ-панель"
            )
        else:
            return AdminLoginResponse(
                success=False,
                message="Неверные учетные данные админа"
            )
    except Exception as e:
        return AdminLoginResponse(
            success=False,
            message=f"Ошибка аутентификации: {str(e)}"
        )

@app.post("/api/admin/change-password", response_model=AdminPasswordChangeResponse)
async def admin_change_password(password_data: AdminPasswordChangeRequest):
    """Смена пароля админа"""
    try:
        success = admin_auth.change_admin_password(
            password_data.old_password, 
            password_data.new_password
        )
        
        if success:
            return AdminPasswordChangeResponse(
                success=True,
                message="Пароль успешно изменен"
            )
        else:
            return AdminPasswordChangeResponse(
                success=False,
                message="Неверный старый пароль"
            )
    except Exception as e:
        return AdminPasswordChangeResponse(
            success=False,
            message=f"Ошибка смены пароля: {str(e)}"
        )

@app.get("/api/admin/info", response_model=AdminInfo)
async def get_admin_info():
    """Получение информации об админе"""
    return AdminInfo(**admin_auth.get_admin_info())

@app.get("/api/admin/config")
async def get_config():
    """Получение текущей конфигурации"""
    return config_manager.get_config()

@app.post("/api/admin/config/update", response_model=ConfigUpdateResponse)
async def update_config(config_data: ConfigUpdateRequest):
    """Обновление конфигурации"""
    try:
        success = config_manager.update_config(
            config_data.section,
            config_data.settings,
            "admin"
        )
        
        if success:
            # Переинициализируем систему после обновления конфигурации
            reinit_success = reinitialize_system()
            
            if reinit_success:
                return ConfigUpdateResponse(
                    success=True,
                    message=f"Конфигурация секции '{config_data.section}' обновлена и система переинициализирована"
                )
            else:
                return ConfigUpdateResponse(
                    success=True,
                    message=f"Конфигурация секции '{config_data.section}' обновлена, но произошла ошибка при переинициализации системы"
                )
        else:
            return ConfigUpdateResponse(
                success=False,
                message="Ошибка обновления конфигурации"
            )
    except Exception as e:
        return ConfigUpdateResponse(
            success=False,
            message=f"Ошибка обновления: {str(e)}"
        )

@app.post("/api/admin/test-connection", response_model=ConnectionTestResponse)
async def test_connection(test_data: ConnectionTestRequest):
    """Тестирование подключения к сервису"""
    try:
        result = config_manager.test_connection(test_data.service)
        return ConnectionTestResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=f"Ошибка тестирования: {str(e)}"
        )

# Code Analysis Endpoints
@app.post("/api/analyze-code", response_model=CodeAnalysisResponse)
async def analyze_code(analysis_request: CodeAnalysisRequest, request: Request):
    """Анализ кода по задаче Jira"""
    try:
        # Используем универсальную функцию для получения пользователя
        user = await get_user_from_session(request)
        
        task_key = analysis_request.task_key.strip()
        
        if not task_key:
            return CodeAnalysisResponse(
                success=False,
                message="Номер задачи не может быть пустым"
            )
        
        # Выполняем анализ
        report = code_analyzer.analyze_task_code(task_key)
        
        if not report:
            return CodeAnalysisResponse(
                success=False,
                message=f"Не удалось проанализировать задачу {task_key}. Проверьте подключения к сервисам."
            )
        
        # Генерируем отчет
        report_text = code_analyzer.generate_report_text(report)
        
        return CodeAnalysisResponse(
            success=True,
            message="Анализ кода выполнен успешно",
            report=report_text
        )
        
    except Exception as e:
        return CodeAnalysisResponse(
            success=False,
            message=f"Ошибка анализа кода: {str(e)}"
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage, request: Request):
    """Обработка сообщений чат-бота (только для аутентифицированных пользователей)"""
    try:
        # Используем универсальную функцию для получения пользователя
        user = await get_user_from_session(request)
        user_message = chat_message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
        
        # Получаем или создаем пользователя в базе данных
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        
        # Получаем или создаем активную сессию
        active_session = chat_service.get_active_session(db_user.id)
        if not active_session:
            active_session = chat_service.create_chat_session(db_user.id)
        
        # Сохраняем сообщение пользователя
        user_message_obj = chat_service.add_message(
            active_session.id, 
            db_user.id, 
            'user', 
            user_message,
            {'ip': request.client.host if request.client else None}
        )
        
        # Добавляем информацию о пользователе в контекст
        user_context = {
            'user': {
                'username': user.get('username'),
                'display_name': user.get('display_name'),
                'email': user.get('email'),
                'groups': user.get('groups', [])
            },
            'session_id': active_session.id
        }
        
        # Определяем команду и вызываем соответствующий MCP сервер
        response = await process_command(user_message, user_context)
        
        # Сохраняем ответ ассистента
        assistant_message_obj = chat_service.add_message(
            active_session.id, 
            db_user.id, 
            'assistant', 
            response,
            {'session_id': active_session.id}
        )
        
        return ChatResponse(
            response=response,
            status="success"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка обработки сообщения: {str(e)}"
        )

async def process_command(message: str, user_context: dict = None) -> str:
    """Обрабатывает команды пользователя с использованием MCP клиента"""
    try:
        # Используем MCP клиент для обработки сообщений
        return await mcp_client.process_message_with_llm(message, user_context)
    except Exception as e:
        logger.error(f"❌ Ошибка обработки команды: {e}")
        

@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Проверка состояния сервисов"""
    llm_status = await llm_client.check_health()
    jira_status = jira_server.check_health()
    atlassian_status = atlassian_server.check_health()
    gitlab_status = gitlab_server.check_health()
    onec_status = onec_server.check_health()
    
    # Проверяем LDAP только если он включен
    ldap_status = {"status": "disabled", "message": "LDAP отключен в конфигурации"}
    ad_config = config_manager.get_service_config('active_directory')
    if ad_config.get('enabled', False):
        try:
            from mcp_servers.ldap_server import LDAPMCPServer
            ldap_server = LDAPMCPServer()
            ldap_status = ldap_server.check_health()
        except Exception as e:
            ldap_status = {"status": "error", "message": str(e)}
    
    return HealthResponse(
        llm=ServiceStatus(**llm_status),
        jira=ServiceStatus(**jira_status),
        atlassian=ServiceStatus(**atlassian_status),
        gitlab=ServiceStatus(**gitlab_status),
        onec=ServiceStatus(**onec_status),
        ldap=ServiceStatus(**ldap_status)
    )

@app.get("/api/services/status")
async def get_services_status():
    """Получает статус сервисов с информацией о том, какие включены"""
    # Получаем конфигурацию сервисов
    jira_config = config_manager.get_service_config('jira')
    atlassian_config = config_manager.get_service_config('atlassian')
    gitlab_config = config_manager.get_service_config('gitlab')
    onec_config = config_manager.get_service_config('onec')
    llm_config = config_manager.get_service_config('llm')
    
    # Получаем статусы
    llm_status = await llm_client.check_health()
    jira_status = jira_server.check_health()
    atlassian_status = atlassian_server.check_health()
    gitlab_status = gitlab_server.check_health()
    onec_status = onec_server.check_health()
    
    # Для LLM проверяем, включен ли текущий провайдер
    current_provider = llm_config.get('provider', 'ollama')
    provider_config = llm_config.get('providers', {}).get(current_provider, {})
    llm_enabled = provider_config.get('enabled', False)
    
    return {
        "llm": {
            "enabled": llm_enabled,
            "status": llm_status.get('status', 'unknown')
        },
        "jira": {
            "enabled": jira_config.get('enabled', False),
            "status": jira_status.get('status', 'unknown')
        },
        "atlassian": {
            "enabled": atlassian_config.get('enabled', False),
            "status": atlassian_status.get('status', 'unknown')
        },
        "gitlab": {
            "enabled": gitlab_config.get('enabled', False),
            "status": gitlab_status.get('status', 'unknown')
        },
        "onec": {
            "enabled": onec_config.get('enabled', False),
            "status": onec_status.get('status', 'unknown')
        }
    }

# LLM Provider Management Endpoints

@app.get("/api/llm/providers")
async def get_llm_providers():
    """Получает список доступных LLM провайдеров"""
    try:
        available_providers = llm_client.get_available_providers()
        current_provider = llm_client.get_current_provider()
        
        return {
            "available_providers": [provider.value for provider in available_providers],
            "current_provider": current_provider.value,
            "provider_info": llm_client.get_provider_info()
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдеров: {e}")
        return {"error": str(e)}

@app.post("/api/llm/switch-provider")
async def switch_llm_provider(provider_data: dict):
    """Переключает LLM провайдер"""
    try:
        provider_name = provider_data.get('provider')
        if not provider_name:
            return {"error": "Провайдер не указан"}
        
        # Конвертируем строку в enum
        try:
            provider = LLMProvider(provider_name)
        except ValueError:
            return {"error": f"Неподдерживаемый провайдер: {provider_name}"}
        
        # Переключаем провайдер
        llm_client.switch_provider(provider)
        
        return {
            "message": f"Провайдер переключен на {provider_name}",
            "current_provider": provider.value,
            "provider_info": llm_client.get_provider_info()
        }
    except Exception as e:
        logger.error(f"❌ Ошибка переключения провайдера: {e}")
        return {"error": str(e)}

@app.get("/api/llm/health")
async def get_llm_health():
    """Проверяет состояние LLM провайдера"""
    try:
        health = await llm_client.check_health()
        return health
    except Exception as e:
        logger.error(f"❌ Ошибка проверки LLM: {e}")
        return {"error": str(e)}

@app.post("/api/llm/test")
async def test_llm_provider(test_data: dict):
    """Тестирует LLM провайдер с тестовым сообщением"""
    try:
        message = test_data.get('message', 'Привет! Как дела?')
        response = await llm_client.generate_response(message)
        
        return {
            "message": message,
            "response": response,
            "provider": llm_client.get_current_provider().value
        }
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования LLM: {e}")
        return {"error": str(e)}

# LDAP Management Endpoints

@app.get("/api/ldap/status")
async def get_ldap_status():
    """Получает статус LDAP сервера"""
    try:
        ad_config = config_manager.get_service_config('active_directory')
        
        if not ad_config.get('enabled', False):
            return {
                "enabled": False,
                "status": "disabled",
                "message": "LDAP отключен в конфигурации"
            }
        
        from mcp_servers.ldap_server import LDAPMCPServer
        ldap_server = LDAPMCPServer()
        health = ldap_server.check_health()
        
        return {
            "enabled": True,
            "status": health.get('status', 'unknown'),
            "message": health.get('message', ''),
            "connection": ldap_server.connection is not None
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса LDAP: {e}")
        return {"error": str(e)}

@app.post("/api/ldap/toggle")
async def toggle_ldap(toggle_data: dict):
    """Включает/отключает LDAP сервер"""
    try:
        enabled = toggle_data.get('enabled', False)
        
        # Обновляем конфигурацию
        ad_config = config_manager.get_service_config('active_directory')
        ad_config['enabled'] = enabled
        config_manager.update_config('active_directory', ad_config)
        
        # Перезагружаем MCP клиент для применения изменений
        await mcp_client.initialize_servers()
        
        return {
            "message": f"LDAP {'включен' if enabled else 'отключен'}",
            "enabled": enabled
        }
    except Exception as e:
        logger.error(f"❌ Ошибка переключения LDAP: {e}")
        return {"error": str(e)}

# LLM Configuration Management Endpoints

@app.get("/api/admin/llm/config", response_model=LLMConfigResponse)
async def get_llm_config():
    """Получает конфигурацию LLM для админ-панели"""
    try:
        llm_config = config_manager.get_service_config('llm')
        
        return LLMConfigResponse(
            success=True,
            message="Конфигурация LLM получена",
            config=llm_config
        )
    except Exception as e:
        logger.error(f"❌ Ошибка получения конфигурации LLM: {e}")
        return LLMConfigResponse(
            success=False,
            message=f"Ошибка получения конфигурации: {str(e)}"
        )

@app.post("/api/admin/llm/config", response_model=LLMConfigResponse)
async def update_llm_config(request: dict):
    """Обновляет конфигурацию LLM"""
    try:
        # Получаем текущую конфигурацию
        llm_config = config_manager.get_service_config('llm')
        
        # Обновляем провайдера по умолчанию
        llm_config['provider'] = request.get('provider', 'ollama')
        
        # Обновляем конфигурации провайдеров
        if 'providers' in request:
            for provider_name, provider_config in request['providers'].items():
                # Валидация конфигурации провайдера
                validated_config = validate_provider_config(provider_name, provider_config)
                
                if provider_name in llm_config.get('providers', {}):
                    llm_config['providers'][provider_name].update(validated_config)
                else:
                    llm_config['providers'][provider_name] = validated_config
        
        # Сохраняем конфигурацию
        config_manager.update_config('llm', llm_config)
        
        # Переинициализируем систему после обновления LLM конфигурации
        reinit_success = reinitialize_system()
        
        if reinit_success:
            return LLMConfigResponse(
                success=True,
                message="Конфигурация LLM обновлена и система переинициализирована",
                config=llm_config
            )
        else:
            return LLMConfigResponse(
                success=True,
                message="Конфигурация LLM обновлена, но произошла ошибка при переинициализации системы",
                config=llm_config
            )
    except Exception as e:
        logger.error(f"❌ Ошибка обновления конфигурации LLM: {e}")
        return LLMConfigResponse(
            success=False,
            message=f"Ошибка обновления конфигурации: {str(e)}"
        )

@app.post("/api/admin/system/reinitialize", response_model=ConfigUpdateResponse)
async def reinitialize_system_endpoint():
    """Переинициализирует систему вручную"""
    try:
        success = reinitialize_system()
        
        if success:
            return ConfigUpdateResponse(
                success=True,
                message="Система успешно переинициализирована"
            )
        else:
            return ConfigUpdateResponse(
                success=False,
                message="Ошибка переинициализации системы"
            )
    except Exception as e:
        return ConfigUpdateResponse(
            success=False,
            message=f"Ошибка переинициализации: {str(e)}"
        )

@app.post("/api/admin/llm/test", response_model=LLMProviderTestResponse)
async def test_llm_provider(request: LLMProviderTestRequest):
    """Тестирует LLM провайдер"""
    try:
        from config.llm_config import LLMProvider
        
        # Конвертируем строку в enum
        try:
            provider_enum = LLMProvider(request.provider)
        except ValueError:
            return LLMProviderTestResponse(
                success=False,
                message=f"Неподдерживаемый провайдер: {request.provider}"
            )
        
        # Создаем временный клиент для тестирования
        test_client = LLMClient(provider_enum)
        
        # Проверяем здоровье провайдера
        health = await test_client.check_health()
        if health['status'] != 'healthy':
            return LLMProviderTestResponse(
                success=False,
                message=f"Провайдер недоступен: {health.get('error', 'Неизвестная ошибка')}",
                provider=request.provider
            )
        
        # Тестируем генерацию ответа
        response = await test_client.generate_response(request.message)
        
        return LLMProviderTestResponse(
            success=True,
            message="Тест провайдера выполнен успешно",
            response=response,
            provider=request.provider
        )
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования провайдера: {e}")
        return LLMProviderTestResponse(
            success=False,
            message=f"Ошибка тестирования: {str(e)}",
            provider=request.provider,
            error=str(e)
        )

@app.get("/api/admin/llm/providers")
async def get_available_llm_providers():
    """Получает список доступных LLM провайдеров"""
    try:
        available_providers = llm_client.get_available_providers()
        current_provider = llm_client.get_current_provider()
        
        return {
            "success": True,
            "available_providers": [provider.value for provider in available_providers],
            "current_provider": current_provider.value,
            "provider_info": llm_client.get_provider_info()
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдеров: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/docs")
async def api_docs():
    """Документация API"""
    return {"message": "Документация API доступна по адресу /docs"}

# Обработчик для статических файлов
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

# API для работы с историей чата
@app.get("/api/chat/sessions")
async def get_chat_sessions(request: Request):
    """Получает список сессий чата пользователя"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        sessions = chat_service.get_user_sessions(db_user.id)
        
        return {
            "sessions": [
                {
                    "id": session.id,
                    "name": session.session_name,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "is_active": session.is_active
                }
                for session in sessions
            ]
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения сессий: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения сессий: {str(e)}")

@app.get("/api/chat/sessions/{session_id}/history")
async def get_session_history(session_id: int, request: Request):
    """Получает историю конкретной сессии"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        
        # Проверяем, что сессия принадлежит пользователю
        session = chat_service.get_user_sessions(db_user.id)
        if not any(s.id == session_id for s in session):
            raise HTTPException(status_code=403, detail="Доступ к сессии запрещен")
        
        history = chat_service.get_session_history(session_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")

@app.post("/api/chat/sessions/{session_id}/close")
async def close_session(session_id: int, request: Request):
    """Закрывает сессию чата"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        
        # Проверяем, что сессия принадлежит пользователю
        session = chat_service.get_user_sessions(db_user.id)
        if not any(s.id == session_id for s in session):
            raise HTTPException(status_code=403, detail="Доступ к сессии запрещен")
        
        chat_service.close_session(session_id)
        return {"message": "Сессия закрыта"}
    except Exception as e:
        logger.error(f"❌ Ошибка закрытия сессии: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка закрытия сессии: {str(e)}")

@app.get("/api/chat/stats")
async def get_user_stats(request: Request):
    """Получает статистику пользователя"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        stats = chat_service.get_user_stats(db_user.id)
        return stats
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=5000, 
        reload=True,
        log_level="info"
    )
