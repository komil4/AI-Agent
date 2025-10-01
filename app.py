#!/usr/bin/env python3
"""
MCP Chat - FastAPI приложение для работы с MCP серверами
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import asyncio
import logging
from datetime import datetime
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

# Импорт модулей
# MCP серверы теперь загружаются автоматически через server_discovery
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

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ
# ============================================================================

# Загрузка переменных окружения
load_dotenv()

# Инициализация компонентов
config_manager = ConfigManager()
ad_auth = ADAuthenticator()
session_manager = SessionManager()
admin_auth = AdminAuth()
llm_client = LLMClient()
code_analyzer = CodeAnalyzer()

# Кэширование статуса сервисов
_services_status_cache = None
_services_status_cache_time = 0
_services_status_cache_interval = 30  # секунд

# MCP серверы теперь инициализируются автоматически через server_discovery

# Создание FastAPI приложения
app = FastAPI(
    title="MCP Chat API",
    description="API для работы с MCP серверами через чат-интерфейс",
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

# Подключение middleware аутентификации
app.add_middleware(AuthMiddleware, session_manager=session_manager)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

# --- События приложения ---

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    try:
        logger.info("[STARTUP] Запуск MCP Chat...")
        
        # Инициализация базы данных
        database_url = config_manager.get_database_url()
        if database_url:
            init_database(database_url)
        else:
            logger.info("[INFO] База данных отключена в конфигурации")
        
        # Инициализация MCP клиента
        await mcp_client.initialize_servers()
        
        logger.info("[OK] MCP Chat запущен успешно")
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка запуска: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении работы приложения"""
    try:
        logger.info("[SHUTDOWN] Завершение работы MCP Chat...")
        
        # Закрытие MCP сессий
        await mcp_client.close_all_sessions()
        
        logger.info("[OK] MCP Chat завершен")
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка закрытия MCP сессий: {e}")

# --- Статические страницы ---

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

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Админ-панель"""
    with open("templates/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/favicon.ico")
async def favicon():
    """Иконка сайта"""
    return FileResponse("static/favicon.ico")

# --- Аутентификация ---

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Аутентификация пользователя через локальную БД или LDAP"""
    try:
        logger.info(f"🔍 Попытка входа пользователя: {login_data.username}")
        
        # Шаг 1: Проверяем локальную аутентификацию в таблице users
        logger.info("📋 Проверяем локальную аутентификацию в БД...")
        db_user = chat_service.authenticate_local_user(login_data.username, login_data.password)
        
        if db_user:
            # Локальная аутентификация успешна
            logger.info(f"[OK] Локальная аутентификация успешна: {db_user.username}")
            
            # Подготавливаем данные пользователя для сессии
            user_info = {
                "id": db_user.id,
                "username": db_user.username,
                "display_name": db_user.display_name or db_user.username,
                "email": db_user.email or "",
                "groups": db_user.groups or [],
                "is_admin": db_user.is_admin
            }
            
            # Создаем JWT токен и сессию
            access_token = ad_auth.create_access_token(user_info)
            session_id = session_manager.create_session(user_info, access_token)
            
            # Создаем ответ
            response = LoginResponse(
                success=True,
                message="Успешная локальная аутентификация",
                user_info=user_info
            )
            
            # Устанавливаем cookie
            from fastapi.responses import JSONResponse
            json_response = JSONResponse(content=response.dict(), status_code=200)
            json_response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=24*60*60
            )
            
            logger.info(f"🍪 Cookie установлен: session_id={session_id}")
            logger.info(f"📊 Сессия создана: {session_id}")
            
            return json_response
        
        # Шаг 2: Если локальная аутентификация не удалась, проверяем LDAP (если включен)
        logger.info("🔍 Локальная аутентификация не удалась, проверяем LDAP...")
        
        # Получаем конфигурацию LDAP
        ad_config = config_manager.get_service_config('active_directory')
        ldap_enabled = ad_config.get('enabled', False)
        
        if not ldap_enabled:
            logger.warning("[ERROR] LDAP отключен в конфигурации")
            return LoginResponse(
                success=False,
                message="Неверные учетные данные. LDAP отключен."
            )
        
        # Аутентификация через LDAP
        logger.info("🌐 Проверяем аутентификацию через LDAP...")
        ldap_user_info = ad_auth.authenticate_user(login_data.username, login_data.password)
        
        if not ldap_user_info:
            logger.warning(f"[ERROR] LDAP аутентификация не удалась для: {login_data.username}")
            return LoginResponse(
                success=False,
                message="Неверные учетные данные или пользователь не найден в Active Directory"
            )
        
        # Шаг 3: LDAP аутентификация успешна - создаем/обновляем пользователя в БД
        logger.info(f"[OK] LDAP аутентификация успешна: {ldap_user_info['username']}")
        
        # Добавляем флаг LDAP пользователя
        ldap_user_info['is_ldap_user'] = True
        
        # Создаем или обновляем пользователя в БД
        logger.info(f"💾 Создаем/обновляем LDAP пользователя в БД: {ldap_user_info['username']}")
        db_user = chat_service.get_or_create_user(ldap_user_info['username'], ldap_user_info)
        logger.info(f"[OK] LDAP пользователь создан/обновлен в БД: {db_user.id}")
        
        # Подготавливаем данные пользователя для сессии с ID из БД
        user_info = {
            "id": db_user.id,
            "username": db_user.username,
            "display_name": db_user.display_name or db_user.username,
            "email": db_user.email or "",
            "groups": db_user.groups or [],
            "is_admin": db_user.is_admin,
            "is_ldap_user": True
        }
        
        # Создаем JWT токен и сессию
        access_token = ad_auth.create_access_token(user_info)
        session_id = session_manager.create_session(user_info, access_token)
        
        # Создаем ответ
        response = LoginResponse(
            success=True,
            message="Успешная LDAP аутентификация",
            user_info=ldap_user_info
        )
        
        # Устанавливаем cookie
        from fastapi.responses import JSONResponse
        json_response = JSONResponse(content=response.dict(), status_code=200)
        json_response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=24*60*60
        )
        
        return json_response
    
    except Exception as e:
        logger.error(f"[ERROR] Ошибка аутентификации: {str(e)}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        return LoginResponse(
            success=False,
            message=f"Ошибка аутентификации: {str(e)}"
        )

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Получает информацию о текущем пользователе"""
    try:
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
        
        # Возвращаем информацию о пользователе
        user_info = session_data.get('user_info', {})
        return {
            "success": True,
            "username": user_info.get('username', 'Неизвестный пользователь'),
            "display_name": user_info.get('display_name', user_info.get('username', 'Неизвестный пользователь')),
            "user_info": user_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения информации о пользователе: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о пользователе: {str(e)}"
        )

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Выход пользователя"""
    try:
        session_id = request.cookies.get('session_id')
        if session_id:
            session_manager.delete_session(session_id)
        
        response = LogoutResponse(success=True, message="Успешный выход")
        from fastapi.responses import JSONResponse
        json_response = JSONResponse(content=response.dict(), status_code=200)
        json_response.delete_cookie(key="session_id")
        return json_response
    except Exception as e:
        return LogoutResponse(success=False, message=f"Ошибка выхода: {str(e)}")

# --- Чат ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage, request: Request):
    """Обработка сообщений чат-бота (только для аутентифицированных пользователей)"""
    try:
        logger.info("🔍 Начинаем обработку сообщения чата")
        
        # Используем универсальную функцию для получения пользователя
        user = await get_user_from_session(request)
        logger.info(f"[OK] Получен пользователь: {user.get('username')}")
        
        user_message = chat_message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
        
        # Получаем или создаем пользователя в базе данных
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        logger.info(f"[OK] Получен/создан пользователь БД: {db_user.id}")
        
        # Получаем или создаем активную сессию
        active_session = chat_service.get_active_session(db_user.id)
        if not active_session:
            active_session = chat_service.create_chat_session(db_user.id)
            logger.info(f"[OK] Создана новая сессия: {active_session.id}")
        else:
            logger.info(f"[OK] Используется существующая сессия: {active_session.id}")
        
        # Сохраняем сообщение пользователя
        logger.info("💾 Сохраняем сообщение пользователя...")
        user_message_data = chat_service.add_message(
            active_session.id, 
            db_user.id, 
            'user', 
            user_message,
            {'ip': request.client.host if request.client else None}
        )
        logger.info(f"[OK] Сообщение пользователя сохранено: {user_message_data['id']}")
        
        # Получаем историю сообщений сессии для контекста
        logger.info("📚 Получаем историю сообщений сессии...")
        session_history = chat_service.get_session_history(active_session.id, limit=10)
        logger.info(f"[OK] Получена история: {len(session_history)} сообщений")
        
        # Получаем дополнительный контекст пользователя
        logger.info("🧠 Получаем дополнительный контекст пользователя...")
        user_additional_context = chat_service.get_user_context(db_user.id)
        logger.info(f"[OK] Контекст пользователя получен: {len(user_additional_context or '')} символов")
        
        # Определяем, нужно ли использовать ReAct агента
        use_react = chat_message.use_react if hasattr(chat_message, 'use_react') else False
        
        # Добавляем информацию о пользователе и историю чата в контекст
        user_context = {
            'user': {
                'username': user.get('username'),
                'display_name': user.get('display_name'),
                'email': user.get('email'),
                'groups': user.get('groups', [])
            },
            'session_id': active_session.id,
            'chat_history': session_history,
            'user_additional_context': user_additional_context or "",
            'use_react': use_react,
            'use_intelligent_tools': True  # Включаем интеллектуальную обработку по умолчанию
        }
        
        # Определяем команду и вызываем соответствующий MCP сервер
        logger.info("🤖 Обрабатываем команду с контекстом чата...")
        response = await process_command(user_message, user_context)
        logger.info(f"[OK] Получен ответ: {response[:100]}...")
        
        # Сохраняем ответ ассистента
        logger.info("💾 Сохраняем ответ ассистента...")
        assistant_message_data = chat_service.add_message(
            active_session.id, 
            db_user.id, 
            'assistant', 
            response,
            {'session_id': active_session.id}
        )
        logger.info(f"[OK] Ответ ассистента сохранен: {assistant_message_data['id']}")
        
        return ChatResponse(
            response=response,
            status="success"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка в chat endpoint: {str(e)}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка обработки сообщения: {str(e)}"
        )

# --- История чата ---

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
                    "id": session_data["id"],
                    "name": session_data["session_name"],
                    "created_at": session_data["created_at"].isoformat(),
                    "updated_at": session_data["updated_at"].isoformat(),
                    "is_active": session_data["is_active"]
                }
                for session_data in sessions
            ]
        }
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения сессий: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения сессий: {str(e)}")

@app.get("/api/chat/sessions/{session_id}/history")
async def get_session_history(session_id: int, request: Request):
    """Получает историю конкретной сессии"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        
        # Проверяем, что сессия принадлежит пользователю
        sessions = chat_service.get_user_sessions(db_user.id)
        if not any(session_data["id"] == session_id for session_data in sessions):
            raise HTTPException(status_code=403, detail="Доступ к сессии запрещен")
        
        history = chat_service.get_session_history(session_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")

@app.post("/api/chat/sessions/{session_id}/close")
async def close_session(session_id: int, request: Request):
    """Закрывает сессию чата"""
    try:
        user = await get_user_from_session(request)
        db_user = chat_service.get_or_create_user(user.get('username'), user)
        
        # Проверяем, что сессия принадлежит пользователю
        sessions = chat_service.get_user_sessions(db_user.id)
        if not any(session_data["id"] == session_id for session_data in sessions):
            raise HTTPException(status_code=403, detail="Доступ к сессии запрещен")
        
        chat_service.close_session(session_id)
        return {"message": "Сессия закрыта"}
    except Exception as e:
        logger.error(f"[ERROR] Ошибка закрытия сессии: {e}")
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
        logger.error(f"[ERROR] Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")

# --- Управление контекстом пользователя ---

@app.get("/api/user/context")
async def get_user_context(request: Request):
    """Получает контекст текущего пользователя"""
    try:
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
        
        # Получаем ID пользователя
        user_info = session_data.get('user_info', {})
        user_id = user_info.get('id')
        
        logger.info(f"🔍 Отладка контекста пользователя: user_info={user_info}, user_id={user_id}")
        
        if not user_id:
            logger.error(f"[ERROR] ID пользователя не найден в сессии: {user_info}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID пользователя не найден в сессии"
            )
        
        # Получаем контекст пользователя
        context = chat_service.get_user_context(user_id)
        
        return {
            "success": True,
            "context": context or "",
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения контекста пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения контекста: {str(e)}"
        )

@app.post("/api/user/context")
async def save_user_context(request: Request, context_data: dict):
    """Сохраняет контекст пользователя"""
    try:
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
        
        # Получаем ID пользователя
        user_info = session_data.get('user_info', {})
        user_id = user_info.get('id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID пользователя не найден в сессии"
            )
        
        # Получаем контекст из запроса
        context = context_data.get('context', '')
        if not context:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Контекст не может быть пустым"
            )
        
        # Сохраняем контекст
        success = chat_service.save_user_context(user_id, context)
        
        if success:
            return {
                "success": True,
                "message": "Контекст успешно сохранен",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка сохранения контекста"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка сохранения контекста пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сохранения контекста: {str(e)}"
        )

@app.put("/api/user/context")
async def update_user_context(request: Request, context_data: dict):
    """Обновляет контекст пользователя (добавляет к существующему)"""
    try:
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
        
        # Получаем ID пользователя
        user_info = session_data.get('user_info', {})
        user_id = user_info.get('id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID пользователя не найден в сессии"
            )
        
        # Получаем новый контекст из запроса
        new_context = context_data.get('context', '')
        if not new_context:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Контекст не может быть пустым"
            )
        
        # Обновляем контекст
        success = chat_service.update_user_context(user_id, new_context)
        
        if success:
            return {
                "success": True,
                "message": "Контекст успешно обновлен",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка обновления контекста"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка обновления контекста пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления контекста: {str(e)}"
        )

@app.delete("/api/user/context")
async def clear_user_context(request: Request):
    """Очищает контекст пользователя"""
    try:
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
        
        # Получаем ID пользователя
        user_info = session_data.get('user_info', {})
        user_id = user_info.get('id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID пользователя не найден в сессии"
            )
        
        # Очищаем контекст
        success = chat_service.clear_user_context(user_id)
        
        if success:
            return {
                "success": True,
                "message": "Контекст успешно очищен",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка очистки контекста"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка очистки контекста пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки контекста: {str(e)}"
        )

# --- Администрирование ---

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

@app.get("/api/admin/info")
async def get_admin_info():
    """Получает информацию для админ-панели"""
    try:
        config = config_manager.get_config()
        
        admin_info = AdminInfo(
            services_status={
                "jira": {"enabled": config.get("jira", {}).get("enabled", False)},
                "atlassian": {"enabled": config.get("atlassian", {}).get("enabled", False)},
                "gitlab": {"enabled": config.get("gitlab", {}).get("enabled", False)},
                "onec": {"enabled": config.get("onec", {}).get("enabled", False)},
                "active_directory": {"enabled": config.get("active_directory", {}).get("enabled", False)},
                "llm": {"enabled": config.get("llm", {}).get("enabled", False)},
                "redis": {"enabled": config.get("redis", {}).get("enabled", False)}
            },
            llm_providers=config.get("llm", {}).get("providers", {}),
            last_updated=config.get("last_updated"),
            updated_by=config.get("updated_by")
        )
        
        return admin_info
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения информации админа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {str(e)}")

@app.get("/api/admin/config")
async def get_admin_config():
    """Получает конфигурацию для админ-панели"""
    try:
        config = config_manager.get_config()
        
        # Получаем динамические настройки MCP серверов
        mcp_servers_config = {}
        
        try:
            from mcp_servers import get_discovered_servers, create_server_instance
            
            discovered_servers = get_discovered_servers()
            logger.info(f"🔍 Обнаружено MCP серверов: {len(discovered_servers)}")
            
            for server_name, server_class in discovered_servers.items():
                try:
                    # Создаем экземпляр сервера
                    server_instance = create_server_instance(server_name)
                    
                    if server_instance:
                        # Получаем настройки админ-панели
                        admin_settings = server_instance.get_admin_settings()
                        
                        # Получаем текущую конфигурацию сервера
                        server_config = config.get(server_name, {})
                        
                        # Объединяем настройки
                        mcp_servers_config[server_name] = {
                            **admin_settings,
                            'config': server_config
                        }
                        
                        logger.info(f"[OK] Настройки сервера {server_name} загружены")
                    
                except Exception as e:
                    logger.warning(f"[WARN] Не удалось загрузить настройки сервера {server_name}: {e}")
                    # Добавляем базовые настройки
                    mcp_servers_config[server_name] = {
                        'name': server_name,
                        'display_name': f'{server_name.title()} MCP',
                        'description': f'MCP сервер для {server_name}',
                        'icon': 'fas fa-server',
                        'category': 'mcp_servers',
                        'fields': [],
                        'enabled': False,
                        'config': {}
                    }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения настроек MCP серверов: {e}")
        
        # Возвращаем полную конфигурацию
        return {
            "config": config,
            "mcp_servers": mcp_servers_config
        }
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения конфигурации админа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения конфигурации: {str(e)}")

@app.post("/api/admin/config/update", response_model=ConfigUpdateResponse)
async def update_config(config_request: ConfigUpdateRequest):
    """Обновляет конфигурацию системы"""
    try:
        success = config_manager.update_config(
            config_request.section,
            config_request.settings,
            "admin"
        )
        
        if success:
            # Переинициализируем систему с новой конфигурацией
            reinitialize_system()
            
            return ConfigUpdateResponse(
                success=True,
                message=f"Конфигурация секции '{config_request.section}' обновлена"
            )
        else:
            return ConfigUpdateResponse(
                success=False,
                message="Ошибка обновления конфигурации"
            )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка обновления конфигурации: {e}")
        return ConfigUpdateResponse(
            success=False,
            message=f"Ошибка обновления конфигурации: {str(e)}"
        )

@app.post("/api/admin/config/test", response_model=ConnectionTestResponse)
async def test_connection(test_request: ConnectionTestRequest):
    """Тестирует подключение к сервису"""
    try:
        result = config_manager.test_connection(test_request.service)
        return ConnectionTestResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка тестирования подключения: {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"Ошибка тестирования: {str(e)}"
        )

# --- Анализ кода ---

@app.post("/api/analyze-code", response_model=CodeAnalysisResponse)
async def analyze_code(analysis_request: CodeAnalysisRequest, request: Request):
    """Анализирует код с помощью LLM"""
    try:
        user = await get_user_from_session(request)
        
        analysis_result = await code_analyzer.analyze_code(
            analysis_request.code,
            analysis_request.language,
            analysis_request.analysis_type
        )
        
        return CodeAnalysisResponse(
            success=True,
            message="Анализ кода выполнен успешно",
            analysis=analysis_result
        )
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка анализа кода: {e}")
        return CodeAnalysisResponse(
            success=False,
            message=f"Ошибка анализа кода: {str(e)}"
        )

# --- Статус сервисов ---

@app.get("/api/services/status", response_model=HealthResponse)
async def get_services_status():
    """Получает статус всех сервисов с кэшированием"""
    global _services_status_cache, _services_status_cache_time
    
    try:
        current_time = datetime.utcnow().timestamp()
        
        # Проверяем, нужно ли обновить кэш
        if (_services_status_cache is None or 
            current_time - _services_status_cache_time > _services_status_cache_interval):
            
            logger.debug("[RELOAD] Обновляем кэш статуса сервисов")
            
            # Используем кэшированные серверы из mcp_client
            mcp_services = {}
            
            # Получаем кэшированные серверы
            cached_servers = mcp_client._get_builtin_servers()
            
            for server_name, server in cached_servers.items():
                try:
                    # Используем кэшированное состояние подключения
                    health_status = server.get_health_status()
                    mcp_services[server_name] = {"status": health_status.get('status', 'inactive')}
                except Exception:
                    mcp_services[server_name] = {"status": "inactive"}
            
            # Проверяем статус LLM
            llm_status = "active"
            try:
                if llm_client.provider:
                    llm_status = "active"
                else:
                    llm_status = "inactive"
            except Exception:
                llm_status = "inactive"
            
            services = {
                **mcp_services,
                "llm": {"status": llm_status},
                "database": {"status": "active"},
                "redis": {"status": "active" if session_manager.is_connected() else "inactive"}
            }
            
            # Кэшируем результат
            _services_status_cache = HealthResponse(
                status="healthy",
                services=services,
                timestamp=datetime.utcnow().isoformat()
            )
            _services_status_cache_time = current_time
            
            logger.debug("[OK] Кэш статуса сервисов обновлен")
        else:
            logger.debug("[RELOAD] Используем кэшированный статус сервисов")
        
        return _services_status_cache
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения статуса сервисов: {e}")
        return HealthResponse(
            status="unhealthy",
            services={},
            timestamp=datetime.utcnow().isoformat()
        )

def invalidate_services_status_cache():
    """Сбрасывает кэш статуса сервисов (полезно при изменении конфигурации)"""
    global _services_status_cache, _services_status_cache_time
    _services_status_cache = None
    _services_status_cache_time = 0
    logger.info("[RELOAD] Кэш статуса сервисов сброшен")

# --- LLM провайдеры ---

@app.get("/api/llm/providers", response_model=LLMConfigResponse)
async def get_llm_providers():
    """Получает список доступных LLM провайдеров"""
    try:
        config = config_manager.get_service_config('llm')
        providers = config.get('providers', {})
        
        return LLMConfigResponse(
            current_provider=config.get('provider', 'ollama'),
            providers=providers
        )
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения LLM провайдеров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения провайдеров: {str(e)}")

@app.post("/api/llm/providers/test", response_model=LLMProviderTestResponse)
async def test_llm_provider(test_request: LLMProviderTestRequest):
    """Тестирует LLM провайдер"""
    try:
        # Создаем временный провайдер для тестирования
        provider = LLMProvider.create_provider(
            test_request.provider_name,
            test_request.config
        )
        
        # Тестируем подключение
        test_message = "Привет! Это тестовое сообщение."
        response = await provider.generate_response(test_message)
        
        return LLMProviderTestResponse(
            success=True,
            message="Провайдер работает корректно",
            test_response=response[:200] + "..." if len(response) > 200 else response
        )
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка тестирования LLM провайдера: {e}")
        return LLMProviderTestResponse(
            success=False,
            message=f"Ошибка тестирования: {str(e)}",
            test_response=""
        )

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

def reinitialize_system():
    """Переинициализирует все компоненты системы"""
    global llm_client, mcp_client, config_manager
    
    try:
        print("[RELOAD] Переинициализация системы...")
        
        # Сбрасываем кэш статуса сервисов
        invalidate_services_status_cache()
        
        # Переинициализация конфигурации
        config_manager = ConfigManager()
        
        # Переинициализация LLM клиента
        llm_client = LLMClient()
        
        # Переинициализация MCP клиента
        mcp_client = MCPClient()
        
        # Переинициализация MCP серверов динамически
        from mcp_servers import get_discovered_servers, create_server_instance
        
        discovered_servers = get_discovered_servers()
        for server_name in discovered_servers.keys():
            try:
                server = create_server_instance(server_name)
                if server:
                    server.reconnect()
            except Exception as e:
                logger.warning(f"[WARN] Не удалось переподключить сервер {server_name}: {e}")
        
        # Переинициализация аутентификации
        ad_auth.reconnect()
        session_manager.reconnect()
        
        print("[OK] Система переинициализирована")
        
    except Exception as e:
        print(f"[ERROR] Ошибка переинициализации: {e}")

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

async def process_command(message: str, user_context: dict = None) -> str:
    """Обрабатывает команды пользователя с использованием MCP клиента"""
    try:
        # Используем MCP клиент для обработки сообщений
        response = await mcp_client.process_message_with_llm(message, user_context)
        return response
    except Exception as e:
        logger.error(f"[ERROR] Ошибка обработки команды: {e}")
        return f"Извините, произошла ошибка при обработке команды: {str(e)}"

# ============================================================================
# API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ СЕССИЯМИ ЧАТА
# ============================================================================

async def get_current_user_info(request: Request) -> dict:
    """Получает информацию о текущем пользователе из сессии"""
    session_id = request.cookies.get('session_id')
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия не найдена"
        )
    
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

@app.get("/api/chat/sessions")
async def get_chat_sessions(request: Request):
    """Получает список сессий чата пользователя"""
    try:
        user_info = await get_current_user_info(request)
        user_id = user_info['id']
        
        sessions = chat_service.get_user_sessions(user_id, limit=50)
        
        return {
            "success": True,
            "sessions": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения сессий чата: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения сессий чата: {str(e)}"
        )

@app.post("/api/chat/sessions")
async def create_chat_session(request: Request, session_data: dict):
    """Создает новую сессию чата"""
    try:
        user_info = await get_current_user_info(request)
        user_id = user_info['id']
        
        session_name = session_data.get('session_name', f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        chat_session = chat_service.create_chat_session(user_id, session_name)
        
        return {
            "success": True,
            "session_id": chat_session.id,
            "session_name": chat_session.session_name,
            "created_at": chat_session.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка создания сессии чата: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания сессии чата: {str(e)}"
        )

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, request: Request):
    """Получает сообщения сессии чата"""
    try:
        user_info = await get_current_user_info(request)
        user_id = user_info['id']
        
        # Проверяем, что сессия принадлежит пользователю
        session = chat_service.get_session_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия не найдена"
            )
        
        messages = chat_service.get_session_messages(session_id, limit=100)
        
        return {
            "success": True,
            "messages": messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка получения сообщений сессии: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения сообщений сессии: {str(e)}"
        )

@app.post("/api/chat/messages")
async def add_chat_message(request: Request, message_data: dict):
    """Добавляет сообщение в сессию чата"""
    try:
        user_info = await get_current_user_info(request)
        user_id = user_info['id']
        
        session_id = message_data.get('session_id')
        message_type = message_data.get('message_type', 'user')
        content = message_data.get('content', '')
        
        if not session_id or not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимы session_id и content"
            )
        
        # Проверяем, что сессия принадлежит пользователю
        session = chat_service.get_session_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия не найдена"
            )
        
        message_data = chat_service.add_message(
            session_id, 
            user_id, 
            message_type, 
            content,
            {'session_id': session_id}
        )
        
        return {
            "success": True,
            "message_id": message_data['id'],
            "message": message_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Ошибка добавления сообщения: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка добавления сообщения: {str(e)}"
        )

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
