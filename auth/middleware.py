#!/usr/bin/env python3
"""
Middleware для аутентификации
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from .ad_auth import ADAuthenticator
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки аутентификации"""
    
    def __init__(self, app, excluded_paths: list = None, session_manager=None):
        """Инициализация middleware"""
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            '/',
            '/login',
            '/logout',
            '/admin',
            '/static',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/api/auth/login',
            '/api/auth/logout',
            '/api/auth/me',  # Добавляем /api/auth/me для проверки статуса
            '/api/admin/login',
            '/api/admin/info',
            '/api/admin/config',
            '/api/admin/config/update',
            '/api/admin/test-connection',
            '/api/admin/change-password',
            '/favicon.ico'
        ]
        self.ad_auth = ADAuthenticator()
        self.session_manager = session_manager  # Сохраняем переданный session_manager
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Обработка запроса через middleware"""
        # Проверяем, нужно ли исключить путь из проверки авторизации
        if self._is_excluded_path(request.url.path):
            response = await call_next(request)
            return response
        
        # Получаем session_id из cookies
        session_id = request.cookies.get('session_id')
        logger.debug(f"🍪 Session ID из cookies: {session_id}")
        logger.debug(f"📋 Все cookies: {request.cookies}")
        
        if not session_id:
            logger.warning(f"❌ Нет session_id для пути {request.url.path}")
            # Если нет сессии, перенаправляем на страницу логина
            if request.url.path.startswith('/api/'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Требуется аутентификация"
                )
            else:
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Проверяем сессию
        session_data = self.session_manager.get_session(session_id)
        if not session_data:
            logger.warning(f"Недействительная сессия {session_id} для пути {request.url.path}")
            # Если сессия недействительна, перенаправляем на страницу логина
            if request.url.path.startswith('/api/'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Сессия истекла"
                )
            else:
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Проверяем JWT токен
        access_token = session_data.get('access_token')
        if access_token:
            user_info = self.ad_auth.verify_access_token(access_token)
            if not user_info:
                logger.warning(f"Недействительный JWT токен для сессии {session_id}")
                # Если токен недействителен, перенаправляем на страницу логина
                if request.url.path.startswith('/api/'):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Токен доступа недействителен"
                    )
                else:
                    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Добавляем информацию о пользователе в request state
        request.state.user_info = session_data.get('user_info', {})
        request.state.session_id = session_id
        
        # Продолжаем обработку запроса
        response = await call_next(request)
        return response

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

    def _is_excluded_path(self, path: str) -> bool:
        """Проверяет, исключен ли путь из проверки авторизации"""
        # Проверяем точное совпадение
        if path in self.excluded_paths:
            return True
        
        # Проверяем пути, начинающиеся с исключенными префиксами
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        
        return False
    
    def _is_admin_path(self, path: str) -> bool:
        """Проверяет, является ли путь админским"""
        return path.startswith('/admin') or path.startswith('/api/admin')
    
    def _is_api_path(self, path: str) -> bool:
        """Проверяет, является ли путь API"""
        return path.startswith('/api/')
    
    def _is_static_path(self, path: str) -> bool:
        """Проверяет, является ли путь статическим"""
        return path.startswith('/static') or path.endswith('.ico') or path.endswith('.css') or path.endswith('.js')
    
    def _is_documentation_path(self, path: str) -> bool:
        """Проверяет, является ли путь документацией"""
        return path in ['/docs', '/redoc', '/openapi.json']
    
    def _is_auth_path(self, path: str) -> bool:
        """Проверяет, является ли путь аутентификационным"""
        return path.startswith('/api/auth/') or path in ['/login', '/logout']
    
    def _should_redirect_to_login(self, path: str) -> bool:
        """Определяет, нужно ли перенаправлять на страницу логина"""
        return not (self._is_static_path(path) or 
                   self._is_documentation_path(path) or 
                   self._is_auth_path(path) or 
                   path == '/')
    
    def _should_return_401(self, path: str) -> bool:
        """Определяет, нужно ли возвращать 401 для API"""
        return self._is_api_path(path) and not self._is_auth_path(path)

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр middleware (создается при инициализации приложения)
auth_middleware = None
