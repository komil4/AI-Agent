import os
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class AdminAuth:
    def __init__(self):
        self.admin_file = "admin_config.json"
        self.default_admin = {
            "username": "admin",
            "password_hash": self._hash_password("admin"),
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
        self._ensure_admin_config()
    
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
    
    def authenticate_admin(self, username: str, password: str) -> bool:
        """Аутентификация админа"""
        config = self._load_admin_config()
        
        if config.get("username") != username:
            logger.warning(f"Неверное имя пользователя админа: {username}")
            return False
        
        password_hash = self._hash_password(password)
        if config.get("password_hash") != password_hash:
            logger.warning(f"Неверный пароль админа для пользователя: {username}")
            return False
        
        # Обновляем время последнего входа
        config["last_login"] = datetime.utcnow().isoformat()
        self._save_admin_config(config)
        
        return True
    
    def change_admin_password(self, old_password: str, new_password: str) -> bool:
        """Смена пароля админа"""
        config = self._load_admin_config()
        
        # Проверяем старый пароль
        old_password_hash = self._hash_password(old_password)
        if config.get("password_hash") != old_password_hash:
            logger.warning("Неверный старый пароль админа")
            return False
        
        # Устанавливаем новый пароль
        config["password_hash"] = self._hash_password(new_password)
        config["password_changed_at"] = datetime.utcnow().isoformat()
        self._save_admin_config(config)
        
        return True
    
    def get_admin_info(self) -> Dict[str, Any]:
        """Получает информацию об админе"""
        config = self._load_admin_config()
        return {
            "username": config.get("username"),
            "created_at": config.get("created_at"),
            "last_login": config.get("last_login"),
            "password_changed_at": config.get("password_changed_at")
        }
