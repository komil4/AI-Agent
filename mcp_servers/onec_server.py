import os
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List
from config.config_manager import ConfigManager

# Временная заглушка для IntentType
class IntentType:
    pass

class OneCMCPServer:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.url = None
        self.api_path = None
        self.username = None
        self.password = None
        self.auth = None
        self._load_config()
        self._connect()
    
    def _load_config(self):
        """Загружает конфигурацию 1С"""
        onec_config = self.config_manager.get_service_config('onec')
        self.url = onec_config.get('url', '')
        self.api_path = onec_config.get('api_path', '/api/tasks')
        self.username = onec_config.get('username', '')
        self.password = onec_config.get('password', '')
    
    def _connect(self):
        """Подключение к 1С"""
        try:
            onec_config = self.config_manager.get_service_config('onec')
            if not onec_config.get('enabled', False):
                print("⚠️ 1С отключен в конфигурации")
                return
                
            if self.url and self.username and self.password:
                # Создаем объект авторизации
                self.auth = HTTPBasicAuth(self.username, self.password)
                print("✅ Настройки 1С загружены")
            else:
                print("⚠️ 1С не настроен - отсутствуют данные в конфигурации")
        except Exception as e:
            print(f"❌ Ошибка загрузки настроек 1С: {e}")
    
    def reconnect(self):
        """Переподключается к 1С с новой конфигурацией"""
        self._load_config()
        self._connect()
    
    
    def _get_user_tasks(self, user: str) -> Dict[str, Any]:
        """Получает задачи пользователя"""
        try:
            if not self.auth:
                return {'error': '1С не подключен'}
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}{self.api_path}",
                auth=self.auth,
                params={'user': user},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'user': user,
                    'tasks': data.get('tasks', []),
                    'count': len(data.get('tasks', []))
                }
            else:
                return {
                    'error': f'Ошибка API 1С: {response.status_code}',
                    'details': response.text
                }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_task_info(self, task_id: str) -> Dict[str, Any]:
        """Получает информацию по задаче"""
        try:
            if not self.auth:
                return {'error': '1С не подключен'}
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}{self.api_path}/{task_id}",
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'task_id': task_id,
                    'task': data
                }
            else:
                return {
                    'error': f'Ошибка API 1С: {response.status_code}',
                    'details': response.text
                }
        except Exception as e:
            return {'error': str(e)}
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов 1С"""
        return [
            {
                "name": "get_user_tasks",
                "description": "Получает список задач пользователя в 1С",
                "parameters": {
                    "user": {"type": "string", "description": "Имя пользователя для получения задач"}
                }
            },
            {
                "name": "get_task_info",
                "description": "Получает детальную информацию по задаче в 1С",
                "parameters": {
                    "task_id": {"type": "string", "description": "Идентификатор задачи"}
                }
            }
        ]
    
    def check_health(self) -> Dict[str, Any]:
        """Проверка состояния подключения к 1С"""
        try:
            if self.auth:
                return {
                    'status': 'connected',
                    'url': self.url,
                    'username': self.username
                }
            else:
                return {'status': 'not_configured', 'url': None}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'url': self.url}
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент 1С"""
        return self.get_tool_result(tool_name, arguments)
    
    def get_tool_result(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет инструмент и возвращает результат"""
        try:
            if tool_name == "get_user_tasks":
                user = arguments.get("user", "")
                return self._get_user_tasks(user)
            
            elif tool_name == "get_task_info":
                task_id = arguments.get("task_id", "")
                return self._get_task_info(task_id)
            
            else:
                return {'error': f'Неизвестный инструмент: {tool_name}'}
                
        except Exception as e:
            return {'error': str(e)}