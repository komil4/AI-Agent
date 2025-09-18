import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config_file = "app_config.json"
        self.default_config = {
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
            "llm": {
                "provider": "ollama",  # openai, anthropic, google, ollama, local
                "providers": {
                    "openai": {
                        "api_key": "",
                        "model": "gpt-4o-mini",
                        "base_url": "https://api.openai.com/v1",
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "timeout": 30,
                        "enabled": False
                    },
                    "anthropic": {
                        "api_key": "",
                        "model": "claude-3-5-sonnet-20241022",
                        "base_url": "https://api.anthropic.com",
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "timeout": 30,
                        "enabled": False
                    },
                    "google": {
                        "api_key": "",
                        "model": "gemini-1.5-flash",
                        "base_url": "https://generativelanguage.googleapis.com",
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "timeout": 30,
                        "enabled": False
                    },
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "model": "llama3.1:8b",
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "timeout": 30,
                        "enabled": True
                    },
                    "local": {
                        "base_url": "http://localhost:8000",
                        "model": "local",
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "timeout": 30,
                        "enabled": False
                    }
                }
            },
            "redis": {
                "url": "redis://localhost:6379",
                "enabled": True
            },
            "jwt": {
                "secret": "",
                "algorithm": "HS256",
                "expire_hours": 24
            },
            "session": {
                "expire_hours": 24
            },
            "mcp_servers": {
                "jira": {
                    "enabled": False,
                    "url": "",
                    "username": "",
                    "api_token": ""
                },
                "gitlab": {
                    "enabled": False,
                    "url": "",
                    "token": ""
                },
                "confluence": {
                    "enabled": False,
                    "url": "",
                    "username": "",
                    "api_token": ""
                }
            },
            "last_updated": None,
            "updated_by": None
        }
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """Создает файл конфигурации если его нет"""
        logger.info(f"Проверяем файл конфигурации: {self.config_file}")
        logger.info(f"Файл существует: {os.path.exists(self.config_file)}")
        
        if not os.path.exists(self.config_file):
            logger.info("Создаем файл конфигурации...")
            self._save_config(self.default_config)
            logger.info("✅ Создан файл конфигурации приложения")
        else:
            logger.info("Файл конфигурации уже существует")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return self.default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Сохраняет конфигурацию"""
        try:
            logger.info(f"Сохраняем конфигурацию в файл: {self.config_file}")
            config["last_updated"] = datetime.utcnow().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("✅ Конфигурация сохранена")
            logger.info(f"Файл создан: {os.path.exists(self.config_file)}")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def get_config(self) -> Dict[str, Any]:
        """Получает текущую конфигурацию"""
        return self._load_config()
    
    def update_config(self, section: str, settings: Dict[str, Any], updated_by: str = "admin") -> bool:
        """Обновляет конфигурацию для определенной секции"""
        try:
            config = self._load_config()
            
            if section not in config:
                logger.error(f"Неизвестная секция конфигурации: {section}")
                return False
            
            # Обновляем секцию
            config[section].update(settings)
            config["updated_by"] = updated_by
            
            self._save_config(config)
            
            # Перезагружаем сервисы
            self.reload_services()
            
            logger.info(f"✅ Конфигурация секции '{section}' обновлена пользователем {updated_by}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            return False
    
    def get_section_config(self, section: str) -> Dict[str, Any]:
        """Получает конфигурацию определенной секции"""
        config = self._load_config()
        return config.get(section, {})
    
    def test_connection(self, service: str) -> Dict[str, Any]:
        """Тестирует подключение к сервису"""
        config = self._load_config()
        service_config = config.get(service, {})
        
        if not service_config.get("enabled", False):
            return {
                "success": False,
                "message": f"Сервис {service} отключен"
            }
        
        try:
            if service == "active_directory":
                return self._test_ad_connection(service_config)
            elif service == "jira":
                return self._test_jira_connection(service_config)
            elif service == "atlassian":
                return self._test_atlassian_connection(service_config)
            elif service == "gitlab":
                return self._test_gitlab_connection(service_config)
            elif service == "llm":
                return self._test_llm_connection(service_config)
            elif service == "redis":
                return self._test_redis_connection(service_config)
            else:
                return {
                    "success": False,
                    "message": f"Неизвестный сервис: {service}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка тестирования подключения: {str(e)}"
            }
    
    def _test_ad_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к Active Directory"""
        try:
            from auth.ad_auth import ADAuthenticator
            ad_auth = ADAuthenticator()
            # Простое тестирование - проверяем наличие настроек
            if not all([config.get("server"), config.get("domain"), config.get("base_dn")]):
                return {
                    "success": False,
                    "message": "Не все обязательные поля заполнены"
                }
            return {
                "success": True,
                "message": "Настройки Active Directory корректны"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка проверки AD: {str(e)}"
            }
    
    def _test_jira_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к Jira"""
        try:
            import requests
            url = config.get("url", "")
            username = config.get("username", "")
            token = config.get("api_token", "")
            
            if not all([url, username, token]):
                return {
                    "success": False,
                    "message": "Не все обязательные поля заполнены"
                }
            
            # Тестируем API
            auth = (username, token)
            response = requests.get(f"{url}/rest/api/3/myself", auth=auth, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Подключение к Jira успешно"
                }
            else:
                return {
                    "success": False,
                    "message": f"Ошибка API Jira: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к Jira: {str(e)}"
            }
    
    def _test_atlassian_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к Atlassian"""
        try:
            import requests
            url = config.get("url", "")
            username = config.get("username", "")
            token = config.get("api_token", "")
            
            if not all([url, username, token]):
                return {
                    "success": False,
                    "message": "Не все обязательные поля заполнены"
                }
            
            # Тестируем API Confluence
            auth = (username, token)
            response = requests.get(f"{url}/rest/api/content", auth=auth, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Подключение к Atlassian успешно"
                }
            else:
                return {
                    "success": False,
                    "message": f"Ошибка API Atlassian: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к Atlassian: {str(e)}"
            }
    
    def _test_gitlab_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к GitLab"""
        try:
            import requests
            url = config.get("url", "")
            token = config.get("token", "")
            
            if not all([url, token]):
                return {
                    "success": False,
                    "message": "Не все обязательные поля заполнены"
                }
            
            # Тестируем API
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{url}/api/v4/user", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Подключение к GitLab успешно"
                }
            else:
                return {
                    "success": False,
                    "message": f"Ошибка API GitLab: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к GitLab: {str(e)}"
            }
    
    def _test_llm_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к LLM серверу"""
        try:
            import requests
            base_url = config.get("base_url", "")
            
            if not base_url:
                return {
                    "success": False,
                    "message": "URL LLM сервера не указан"
                }
            
            # Тестируем API
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Подключение к LLM серверу успешно"
                }
            else:
                return {
                    "success": False,
                    "message": f"Ошибка LLM сервера: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к LLM: {str(e)}"
            }
    
    def _test_redis_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирует подключение к Redis"""
        try:
            import redis
            redis_url = config.get("url", "")
            
            if not redis_url:
                return {
                    "success": False,
                    "message": "URL Redis не указан"
                }
            
            # Тестируем подключение
            r = redis.from_url(redis_url, decode_responses=True)
            r.ping()
            
            return {
                "success": True,
                "message": "Подключение к Redis успешно"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка подключения к Redis: {str(e)}"
            }
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Получает конфигурацию конкретного сервиса"""
        config = self._load_config()
        return config.get(service, {})
    
    def reload_services(self):
        """Перезагружает сервисы после изменения конфигурации"""
        try:
            # Получаем глобальные переменные из app.py
            import sys
            app_module = sys.modules.get('app')
            if app_module:
                # Переподключаем MCP серверы
                if hasattr(app_module, 'jira_server') and hasattr(app_module.jira_server, 'reconnect'):
                    app_module.jira_server.reconnect()
                if hasattr(app_module, 'atlassian_server') and hasattr(app_module.atlassian_server, 'reconnect'):
                    app_module.atlassian_server.reconnect()
                if hasattr(app_module, 'gitlab_server') and hasattr(app_module.gitlab_server, 'reconnect'):
                    app_module.gitlab_server.reconnect()
                if hasattr(app_module, 'llm_client') and hasattr(app_module.llm_client, 'reconnect'):
                    app_module.llm_client.reconnect()
                if hasattr(app_module, 'ad_auth') and hasattr(app_module.ad_auth, 'reconnect'):
                    app_module.ad_auth.reconnect()
                if hasattr(app_module, 'session_manager') and hasattr(app_module.session_manager, 'reconnect'):
                    app_module.session_manager.reconnect()
                
                logger.info("✅ Сервисы перезагружены")
            else:
                logger.warning("⚠️ Не удалось найти модуль app.py")
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки сервисов: {e}")
