import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis
import json
import logging
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.redis_url = 'redis://localhost:6379'
        self.session_expire_hours = 24
        self.redis_client = None
        self._sessions = {}  # Инициализируем in-memory хранилище
        self._load_config()
        self._connect_redis()
    
    def _load_config(self):
        """Загружает конфигурацию Redis и сессий"""
        redis_config = self.config_manager.get_service_config('redis')
        self.redis_url = redis_config.get('url', 'redis://localhost:6379')
        
        session_config = self.config_manager.get_service_config('session')
        self.session_expire_hours = session_config.get('expire_hours', 24)
    
    def reconnect(self):
        """Переподключается с новой конфигурацией"""
        self._load_config()
        self._connect_redis()
    
    def _connect_redis(self):
        """Подключение к Redis для хранения сессий"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Проверяем подключение
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"⚠️ Redis недоступен, используем in-memory хранилище: {e}")
            self.redis_client = None
            # _sessions уже инициализирован в конструкторе
    
    def create_session(self, user_info: Dict[str, Any], access_token: str) -> str:
        """
        Создает новую сессию пользователя
        """
        session_id = self._generate_session_id()
        session_data = {
            'user_info': user_info,
            'access_token': access_token,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        
        if self.redis_client:
            # Сохраняем в Redis
            self.redis_client.setex(
                f"session:{session_id}",
                timedelta(hours=self.session_expire_hours),
                json.dumps(session_data)
            )
        else:
            # Сохраняем в памяти
            self._sessions[session_id] = session_data
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные сессии
        """
        try:
            if self.redis_client:
                session_data = self.redis_client.get(f"session:{session_id}")
                if session_data:
                    return json.loads(session_data)
            else:
                return self._sessions.get(session_id)
        except Exception as e:
            logger.error(f"Ошибка получения сессии: {e}")

        return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Обновляет время последней активности сессии
        """
        try:
            session_data = self.get_session(session_id)
            if session_data:
                session_data['last_activity'] = datetime.utcnow().isoformat()
                
                if self.redis_client:
                    self.redis_client.setex(
                        f"session:{session_id}",
                        timedelta(hours=self.session_expire_hours),
                        json.dumps(session_data)
                    )
                else:
                    self._sessions[session_id] = session_data
                
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления сессии: {e}")
        
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию
        """
        try:
            if self.redis_client:
                self.redis_client.delete(f"session:{session_id}")
            else:
                self._sessions.pop(session_id, None)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления сессии: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """
        Очищает истекшие сессии
        """
        try:
            if self.redis_client:
                # Redis автоматически удаляет истекшие ключи
                pass
            else:
                # Очищаем in-memory хранилище
                current_time = datetime.utcnow()
                expired_sessions = []
                
                for session_id, session_data in self._sessions.items():
                    last_activity = datetime.fromisoformat(session_data['last_activity'])
                    if current_time - last_activity > timedelta(hours=self.session_expire_hours):
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self._sessions[session_id]
                
        except Exception as e:
            logger.error(f"Ошибка очистки сессий: {e}")
    
    def _generate_session_id(self) -> str:
        """
        Генерирует уникальный ID сессии
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_user_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе из сессии
        """
        session_data = self.get_session(session_id)
        if session_data:
            return session_data.get('user_info')
        return None
