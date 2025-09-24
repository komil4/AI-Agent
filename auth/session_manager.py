#!/usr/bin/env python3
"""
Менеджер сессий пользователей
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis
import json
import logging
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class SessionManager:
    """Менеджер сессий пользователей"""
    
    def __init__(self):
        """Инициализация менеджера сессий"""
        self.config_manager = ConfigManager()
        self.redis_url = 'redis://localhost:6379'
        self.session_expire_hours = 24
        self.redis_client = None
        self._sessions = {}  # Инициализируем in-memory хранилище
        self._load_config()
        self._connect_redis()
    
    def create_session(self, user_info: Dict[str, Any], access_token: str) -> str:
        """Создает новую сессию пользователя"""
        session_id = self._generate_session_id()
        session_data = {
            'user_info': user_info,
            'access_token': access_token,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        
        # Сохраняем в Redis или in-memory
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}",
                    self.session_expire_hours * 3600,
                    json.dumps(session_data)
                )
                logger.info(f"✅ Сессия создана в Redis: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка сохранения в Redis, используем in-memory: {e}")
                self._sessions[session_id] = session_data
        else:
            self._sessions[session_id] = session_data
            logger.info(f"✅ Сессия создана в памяти: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные сессии"""
        if self.redis_client:
            try:
                session_data = self.redis_client.get(f"session:{session_id}")
                if session_data:
                    session_dict = json.loads(session_data)
                    # Обновляем время последней активности
                    session_dict['last_activity'] = datetime.utcnow().isoformat()
                    self.redis_client.setex(
                        f"session:{session_id}",
                        self.session_expire_hours * 3600,
                        json.dumps(session_dict)
                    )
                    return session_dict
                return None
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения из Redis: {e}")
                return self._sessions.get(session_id)
        else:
            return self._sessions.get(session_id)
    
    def update_session(self, session_id: str, user_info: Dict[str, Any] = None, access_token: str = None):
        """Обновляет данные сессии"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        if user_info:
            session_data['user_info'] = user_info
        if access_token:
            session_data['access_token'] = access_token
        
        session_data['last_activity'] = datetime.utcnow().isoformat()
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}",
                    self.session_expire_hours * 3600,
                    json.dumps(session_data)
                )
                return True
            except Exception as e:
                logger.warning(f"⚠️ Ошибка обновления в Redis: {e}")
                self._sessions[session_id] = session_data
                return True
        else:
            self._sessions[session_id] = session_data
            return True
    
    def delete_session(self, session_id: str):
        """Удаляет сессию"""
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_id}")
                logger.info(f"✅ Сессия удалена из Redis: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления из Redis: {e}")
                self._sessions.pop(session_id, None)
        else:
            self._sessions.pop(session_id, None)
            logger.info(f"✅ Сессия удалена из памяти: {session_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Получает все активные сессии"""
        if self.redis_client:
            try:
                sessions = {}
                for key in self.redis_client.scan_iter(match="session:*"):
                    session_id = key.replace("session:", "")
                    session_data = self.get_session(session_id)
                    if session_data:
                        sessions[session_id] = session_data
                return sessions
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения сессий из Redis: {e}")
                return self._sessions.copy()
        else:
            return self._sessions.copy()
    
    def cleanup_expired_sessions(self):
        """Очищает истекшие сессии"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        if self.redis_client:
            try:
                for key in self.redis_client.scan_iter(match="session:*"):
                    session_data = self.redis_client.get(key)
                    if session_data:
                        session_dict = json.loads(session_data)
                        last_activity = datetime.fromisoformat(session_dict['last_activity'])
                        if (current_time - last_activity).total_seconds() > self.session_expire_hours * 3600:
                            expired_sessions.append(key)
                
                for key in expired_sessions:
                    self.redis_client.delete(key)
                
                logger.info(f"✅ Очищено {len(expired_sessions)} истекших сессий из Redis")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка очистки сессий в Redis: {e}")
        else:
            for session_id, session_data in self._sessions.items():
                last_activity = datetime.fromisoformat(session_data['last_activity'])
                if (current_time - last_activity).total_seconds() > self.session_expire_hours * 3600:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
            
            logger.info(f"✅ Очищено {len(expired_sessions)} истекших сессий из памяти")
    
    def reconnect(self):
        """Переподключается с новой конфигурацией"""
        self._load_config()
        self._connect_redis()
    
    def is_connected(self) -> bool:
        """Проверяет подключение к Redis"""
        if self.redis_client:
            try:
                self.redis_client.ping()
                return True
            except Exception:
                return False
        return True  # in-memory всегда доступен

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

    def _load_config(self):
        """Загружает конфигурацию Redis и сессий"""
        redis_config = self.config_manager.get_service_config('redis')
        self.redis_url = redis_config.get('url', 'redis://localhost:6379')
        
        session_config = self.config_manager.get_service_config('session')
        self.session_expire_hours = session_config.get('expire_hours', 24)
    
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
    
    def _generate_session_id(self) -> str:
        """Генерирует уникальный ID сессии"""
        import uuid
        return str(uuid.uuid4())

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр менеджера сессий
session_manager = SessionManager()
