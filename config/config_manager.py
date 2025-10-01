#!/usr/bin/env python3
"""
Менеджер конфигурации приложения
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self):
        """Инициализация менеджера конфигурации"""
        self.config_file = "app_config.json"
        self.default_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "mcp_chat",
                "username": "mcp_user",
                "password": "mcp_password",
                "enabled": True
            },
            "active_directory": {
                "server": "",
                "domain": "",
                "base_dn": "",
                "service_user": "",
                "service_password": "",
                "enabled": False
            },
            "jira": {
                "url": "",
                "username": "",
                "api_token": "",
                "enabled": False
            },
            "atlassian": {
                "url": "",
                "username": "",
                "api_token": "",
                "enabled": False
            },
            "gitlab": {
                "url": "",
                "token": "",
                "enabled": False
            },
            "onec": {
                "url": "",
                "api_path": "/api/tasks",
                "username": "",
                "password": "",
                "enabled": False
            },
            "llm": {
                "provider": "ollama",
                "enabled": True,
                "providers": {
                    "ollama": {
                        "url": "http://localhost:11434",
                        "model": "llama2",
                        "enabled": True
                    },
                    "openai": {
                        "api_key": "",
                        "model": "gpt-3.5-turbo",
                        "enabled": False
                    },
                    "anthropic": {
                        "api_key": "",
                        "model": "claude-3-sonnet-20240229",
                        "enabled": False
                    },
                    "google": {
                        "api_key": "",
                        "model": "gemini-pro",
                        "enabled": False
                    }
                }
            },
            "redis": {
                "url": "redis://localhost:6379",
                "enabled": True
            },
            "session": {
                "expire_hours": 24,
                "enabled": True
            }
        }
        self._ensure_config_file()
    
    def get_config(self) -> Dict[str, Any]:
        """Получает полную конфигурацию"""
        return self._load_config()
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Получает конфигурацию конкретного сервиса"""
        config = self._load_config()
        return config.get(service, {})
    
    def update_config(self, section: str, settings: Dict[str, Any], updated_by: str = "user") -> bool:
        """Обновляет конфигурацию секции"""
        try:
            config = self._load_config()
            
            if section not in config:
                config[section] = {}
            
            # Обновляем настройки
            config[section].update(settings)
            
            # Добавляем метаданные
            config["last_updated"] = datetime.utcnow().isoformat()
            config["updated_by"] = updated_by
            
            # Сохраняем конфигурацию
            self._save_config(config)
            
            logger.info(f"[OK] Конфигурация секции '{section}' обновлена пользователем: {updated_by}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка обновления конфигурации: {e}")
            return False
    
    def reset_config(self) -> bool:
        """Сбрасывает конфигурацию к значениям по умолчанию"""
        try:
            self._save_config(self.default_config)
            logger.info("[OK] Конфигурация сброшена к значениям по умолчанию")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Ошибка сброса конфигурации: {e}")
            return False
    
    def get_database_url(self) -> str:
        """Получает URL подключения к базе данных"""
        db_config = self.get_service_config('database')
        
        # Проверяем, включена ли база данных
        if not db_config.get('enabled', False):
            return None
        
        # Проверяем переменные окружения
        host = os.getenv('DB_HOST', db_config.get('host', 'localhost'))
        port = os.getenv('DB_PORT', db_config.get('port', 5432))
        database = os.getenv('DB_NAME', db_config.get('database', 'mcp_chat'))
        username = os.getenv('DB_USER', db_config.get('username', 'mcp_user'))
        password = os.getenv('DB_PASSWORD', db_config.get('password', 'mcp_password'))
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def test_connection(self, service: str) -> Dict[str, Any]:
        """Тестирует подключение к сервису"""
        try:
            if service == "database":
                return self._test_database_connection()
            elif service == "redis":
                return self._test_redis_connection()
            elif service == "jira":
                return self._test_jira_connection()
            elif service == "atlassian":
                return self._test_atlassian_connection()
            elif service == "gitlab":
                return self._test_gitlab_connection()
            elif service == "onec":
                return self._test_onec_connection()
            elif service == "active_directory":
                return self._test_ldap_connection()
            elif service == "llm":
                return self._test_llm_connection()
            else:
                return {"success": False, "message": f"Неизвестный сервис: {service}"}
                
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования: {str(e)}"}
    
    def validate_config(self) -> Dict[str, Any]:
        """Валидирует конфигурацию"""
        config = self._load_config()
        errors = []
        warnings = []
        
        # Проверяем обязательные поля
        required_services = ['database', 'llm', 'redis']
        for service in required_services:
            if service not in config:
                errors.append(f"Отсутствует секция '{service}'")
            elif not config[service].get('enabled', False):
                warnings.append(f"Сервис '{service}' отключен")
        
        # Проверяем настройки базы данных
        if 'database' in config:
            db_config = config['database']
            if not db_config.get('host'):
                errors.append("Не указан хост базы данных")
            if not db_config.get('database'):
                errors.append("Не указано имя базы данных")
        
        # Проверяем настройки LLM
        if 'llm' in config:
            llm_config = config['llm']
            if not llm_config.get('provider'):
                errors.append("Не указан провайдер LLM")
            elif llm_config.get('provider') not in llm_config.get('providers', {}):
                errors.append(f"Провайдер '{llm_config['provider']}' не настроен")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

    def _ensure_config_file(self):
        """Создает файл конфигурации если его нет"""
        if not os.path.exists(self.config_file):
            self._save_config(self.default_config)
            logger.info(f"[OK] Создан файл конфигурации: {self.config_file}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Объединяем с конфигурацией по умолчанию для новых полей
                return self._merge_configs(self.default_config, config)
        except Exception as e:
            logger.error(f"[ERROR] Ошибка загрузки конфигурации: {e}")
            return self.default_config.copy()
    
    def _save_config(self, config: Dict[str, Any]):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[ERROR] Ошибка сохранения конфигурации: {e}")
            raise
    
    def _merge_configs(self, default: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Объединяет конфигурации"""
        result = default.copy()
        
        for key, value in current.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _test_database_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к базе данных"""
        try:
            from database import DatabaseManager
            db_url = self.get_database_url()
            db_manager = DatabaseManager(db_url)
            success = db_manager.test_connection()
            return {
                "success": success,
                "message": "Подключение к базе данных успешно" if success else "Ошибка подключения к базе данных"
            }
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования БД: {str(e)}"}
    
    def _test_redis_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к Redis"""
        try:
            import redis
            redis_config = self.get_service_config('redis')
            redis_url = redis_config.get('url', 'redis://localhost:6379')
            client = redis.from_url(redis_url)
            client.ping()
            return {"success": True, "message": "Подключение к Redis успешно"}
        except Exception as e:
            return {"success": False, "message": f"Ошибка подключения к Redis: {str(e)}"}
    
    def _test_jira_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к Jira"""
        try:
            from mcp_servers import create_server_instance
            jira_server = create_server_instance('jira')
            if jira_server:
                success = jira_server.test_connection()
                return {
                    "success": success,
                    "message": "Подключение к Jira успешно" if success else "Ошибка подключения к Jira"
                }
            else:
                return {"success": False, "message": "Jira сервер не найден"}
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования Jira: {str(e)}"}
    
    def _test_atlassian_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к Atlassian"""
        try:
            from mcp_servers import create_server_instance
            atlassian_server = create_server_instance('atlassian')
            if atlassian_server:
                success = atlassian_server.test_connection()
                return {
                    "success": success,
                    "message": "Подключение к Atlassian успешно" if success else "Ошибка подключения к Atlassian"
                }
            else:
                return {"success": False, "message": "Atlassian сервер не найден"}
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования Atlassian: {str(e)}"}
    
    def _test_gitlab_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к GitLab"""
        try:
            from mcp_servers import create_server_instance
            gitlab_server = create_server_instance('gitlab')
            if gitlab_server:
                success = gitlab_server.test_connection()
                return {
                    "success": success,
                    "message": "Подключение к GitLab успешно" if success else "Ошибка подключения к GitLab"
                }
            else:
                return {"success": False, "message": "GitLab сервер не найден"}
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования GitLab: {str(e)}"}
    
    def _test_onec_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к 1C"""
        try:
            from mcp_servers import create_server_instance
            onec_server = create_server_instance('onec')
            if onec_server:
                success = onec_server.test_connection()
                return {
                    "success": success,
                    "message": "Подключение к 1C успешно" if success else "Ошибка подключения к 1C"
                }
            else:
                return {"success": False, "message": "1C сервер не найден"}
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования 1C: {str(e)}"}
    
    def _test_ldap_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к LDAP"""
        try:
            from auth.ad_auth import ADAuthenticator
            ad_auth = ADAuthenticator()
            success = ad_auth.is_connected()
            return {
                "success": success,
                "message": "Подключение к LDAP успешно" if success else "Ошибка подключения к LDAP"
            }
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования LDAP: {str(e)}"}
    
    def _test_llm_connection(self) -> Dict[str, Any]:
        """Тестирует подключение к LLM"""
        try:
            from llm_client import LLMClient
            llm_client = LLMClient()
            success = llm_client.is_connected()
            return {
                "success": success,
                "message": "Подключение к LLM успешно" if success else "Ошибка подключения к LLM"
            }
        except Exception as e:
            return {"success": False, "message": f"Ошибка тестирования LLM: {str(e)}"}

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager()
