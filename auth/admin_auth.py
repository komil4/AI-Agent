#!/usr/bin/env python3
"""
Аутентификация администратора
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class AdminAuth:
    """Аутентификатор администратора"""
    
    def __init__(self):
        """Инициализация аутентификатора администратора"""
        self.admin_file = "admin_config.json"
        self.default_admin = {
            "username": "admin",
            "password_hash": self._hash_password("admin"),
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
        self._ensure_admin_config()
    
    def authenticate_admin(self, username: str, password: str) -> bool:
        """Аутентификация админа"""
        config = self._load_admin_config()
        
        if config.get("username") == username:
            password_hash = self._hash_password(password)
            if config.get("password_hash") == password_hash:
                # Обновляем время последнего входа
                config["last_login"] = datetime.utcnow().isoformat()
                self._save_admin_config(config)
                logger.info(f"✅ Админ аутентифицирован: {username}")
                return True
        
        logger.warning(f"❌ Неверные учетные данные админа: {username}")
        return False
    
    def change_admin_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Изменение пароля админа"""
        config = self._load_admin_config()
        
        if config.get("username") == username:
            old_password_hash = self._hash_password(old_password)
            if config.get("password_hash") == old_password_hash:
                # Обновляем пароль
                config["password_hash"] = self._hash_password(new_password)
                config["last_password_change"] = datetime.utcnow().isoformat()
                self._save_admin_config(config)
                logger.info(f"✅ Пароль админа изменен: {username}")
                return True
        
        logger.warning(f"❌ Неверный старый пароль для админа: {username}")
        return False
    
    def get_admin_info(self) -> Dict[str, Any]:
        """Получает информацию об админе"""
        config = self._load_admin_config()
        return {
            "username": config.get("username"),
            "created_at": config.get("created_at"),
            "last_login": config.get("last_login"),
            "last_password_change": config.get("last_password_change")
        }
    
    def create_admin(self, username: str, password: str) -> bool:
        """Создает нового админа"""
        config = self._load_admin_config()
        
        if config.get("username") == username:
            logger.warning(f"❌ Админ уже существует: {username}")
            return False
        
        new_admin = {
            "username": username,
            "password_hash": self._hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
        
        self._save_admin_config(new_admin)
        logger.info(f"✅ Создан новый админ: {username}")
        return True

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

    def _ensure_admin_config(self):
        """Создает файл конфигурации админа если его нет"""
        if not os.path.exists(self.admin_file):
            self._save_admin_config(self.default_admin)
    
    def _hash_password(self, password: str) -> str:
        """Хеширует пароль"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_admin_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию админа"""
        try:
            with open(self.admin_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации админа: {e}")
            return self.default_admin
    
    def _save_admin_config(self, config: Dict[str, Any]):
        """Сохраняет конфигурацию админа"""
        try:
            with open(self.admin_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации админа: {e}")

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр аутентификатора администратора
admin_auth = AdminAuth()
