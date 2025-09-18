from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from .ad_auth import ADAuthenticator
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: list = None, session_manager=None):
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
        # Проверяем, нужно ли исключить путь из проверки авторизации
        if self._is_excluded_path(request.url.path):
            response = await call_next(request)
            return response
        
        # Получаем session_id из cookies
        session_id = request.cookies.get('session_id')
        
        if not session_id:
            logger.warning(f"Нет session_id для пути {request.url.path}")
            # Если нет сессии, перенаправляем на страницу логина
            if request.url.path.startswith('/api/'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Требуется аутентификация"
                )
            else:
                return RedirectResponse(url="/login", status_code=302)
        
        # Получаем session_manager
        session_manager = self.session_manager
        if not session_manager:
            # Fallback: пытаемся получить из глобального контекста
            import sys
            app_module = sys.modules.get('app')
            
            if app_module and hasattr(app_module, 'session_manager'):
                session_manager = app_module.session_manager
            else:
                logger.error("Не удалось найти session_manager")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка конфигурации сервера"
                )
        
        # Проверяем сессию
        session_data = session_manager.get_session(session_id)
        
        if not session_data:
            logger.warning(f"Сессия {session_id} недействительна для пути {request.url.path}")
            # Сессия недействительна
            if request.url.path.startswith('/api/'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Сессия истекла"
                )
            else:
                return RedirectResponse(url="/login", status_code=302)
        
        # Обновляем время последней активности
        session_manager.update_session_activity(session_id)
        
        # Продолжаем выполнение запроса
        response = await call_next(request)
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Проверяет, исключен ли путь из проверки авторизации
        """
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False

def get_current_user(request: Request) -> dict:
    """
    Получает текущего пользователя из request state
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не аутентифицирован"
        )
    return request.state.user

def require_groups(required_groups: list):
    """
    Декоратор для проверки принадлежности пользователя к определенным группам
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            ad_auth = ADAuthenticator()
            
            if not ad_auth.check_user_permissions(user, required_groups):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Недостаточно прав. Требуются группы: {', '.join(required_groups)}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
