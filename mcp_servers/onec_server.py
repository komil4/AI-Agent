#!/usr/bin/env python3
"""
MCP сервер для работы с 1С с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import json
import requests
import logging
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_mcp_server import BaseMCPServer, create_tool_schema, validate_tool_parameters, format_tool_response

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class OneCMCPServer(BaseMCPServer):
    """MCP сервер для работы с 1С - получение информации о задачах пользователей и деталях задач через HTTP API"""
    
    def __init__(self):
        """Инициализация 1C MCP сервера"""
        # Инициализируем переменные ДО вызова super().__init__()
        self.url = None
        self.api_path = None
        self.username = None
        self.password = None
        self.auth = None
        
        # Теперь вызываем родительский конструктор
        super().__init__("onec")
        
        # Настройки для админ-панели
        self.display_name = "1C MCP"
        self.icon = "fas fa-calculator"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL сервера 1C', 'type': 'text', 'placeholder': 'http://1c-server:8080' },
            { 'key': 'api_path', 'label': 'Путь к API', 'type': 'text', 'placeholder': '/api/v1' },
            { 'key': 'username', 'label': 'Имя пользователя', 'type': 'text', 'placeholder': 'admin' },
            { 'key': 'password', 'label': 'Пароль', 'type': 'password', 'placeholder': 'пароль' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="get_user_tasks",
                description="Получает список задач пользователя в 1С с возможностью фильтрации по статусу и приоритету",
                parameters={
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "Имя пользователя для получения задач"
                        },
                        "status": {
                            "type": "string",
                            "description": "Статус задач для фильтрации",
                            "enum": ["new", "in_progress", "completed", "cancelled", "all"]
                        },
                        "priority": {
                            "type": "string",
                            "description": "Приоритет задач для фильтрации",
                            "enum": ["low", "normal", "high", "critical", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество задач (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 500
                        },
                        "include_completed": {
                            "type": "boolean",
                            "description": "Включать завершенные задачи"
                        }
                    },
                    "required": ["user"]
                }
            ),
            create_tool_schema(
                name="get_task_info",
                description="Получает детальную информацию по конкретной задаче в 1С",
                parameters={
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Идентификатор задачи"
                        },
                        "include_history": {
                            "type": "boolean",
                            "description": "Включать историю изменений задачи"
                        },
                        "include_comments": {
                            "type": "boolean",
                            "description": "Включать комментарии к задаче"
                        },
                        "include_attachments": {
                            "type": "boolean",
                            "description": "Включать информацию о вложениях"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            create_tool_schema(
                name="create_task",
                description="Создает новую задачу в 1С",
                parameters={
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Название задачи"
                        },
                        "description": {
                            "type": "string",
                            "description": "Описание задачи"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Исполнитель задачи"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Приоритет задачи",
                            "enum": ["low", "normal", "high", "critical"]
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Срок выполнения (ISO 8601)"
                        },
                        "project": {
                            "type": "string",
                            "description": "Проект задачи"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Теги задачи"
                        }
                    },
                    "required": ["title", "description", "assignee"]
                }
            ),
            create_tool_schema(
                name="update_task",
                description="Обновляет существующую задачу в 1С",
                parameters={
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Идентификатор задачи"
                        },
                        "title": {
                            "type": "string",
                            "description": "Новое название задачи"
                        },
                        "description": {
                            "type": "string",
                            "description": "Новое описание задачи"
                        },
                        "status": {
                            "type": "string",
                            "description": "Новый статус задачи",
                            "enum": ["new", "in_progress", "completed", "cancelled"]
                        },
                        "priority": {
                            "type": "string",
                            "description": "Новый приоритет задачи",
                            "enum": ["low", "normal", "high", "critical"]
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Новый исполнитель"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Новый срок выполнения (ISO 8601)"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            create_tool_schema(
                name="add_task_comment",
                description="Добавляет комментарий к задаче в 1С",
                parameters={
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Идентификатор задачи"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Текст комментария"
                        },
                        "is_private": {
                            "type": "boolean",
                            "description": "Приватный комментарий (только для исполнителя)"
                        }
                    },
                    "required": ["task_id", "comment"]
                }
            ),
            create_tool_schema(
                name="list_projects",
                description="Получает список проектов в 1С",
                parameters={
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество проектов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 200
                        },
                        "status": {
                            "type": "string",
                            "description": "Статус проектов для фильтрации",
                            "enum": ["active", "inactive", "completed", "all"]
                        },
                        "include_stats": {
                            "type": "boolean",
                            "description": "Включать статистику по проектам"
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_project_info",
                description="Получает детальную информацию о проекте в 1С",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Идентификатор проекта"
                        },
                        "include_tasks": {
                            "type": "boolean",
                            "description": "Включать список задач проекта"
                        },
                        "include_members": {
                            "type": "boolean",
                            "description": "Включать список участников проекта"
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            create_tool_schema(
                name="list_users",
                description="Получает список пользователей в 1С",
                parameters={
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество пользователей (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 200
                        },
                        "role": {
                            "type": "string",
                            "description": "Роль пользователей для фильтрации",
                            "enum": ["admin", "manager", "user", "all"]
                        },
                        "status": {
                            "type": "string",
                            "description": "Статус пользователей",
                            "enum": ["active", "inactive", "all"]
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_user_info",
                description="Получает информацию о пользователе в 1С",
                parameters={
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Имя пользователя"
                        },
                        "include_tasks": {
                            "type": "boolean",
                            "description": "Включать статистику по задачам пользователя"
                        },
                        "include_projects": {
                            "type": "boolean",
                            "description": "Включать список проектов пользователя"
                        }
                    },
                    "required": ["username"]
                }
            ),
            create_tool_schema(
                name="search_tasks",
                description="Ищет задачи в 1С по различным критериям",
                parameters={
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос (название, описание, теги)"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Исполнитель для фильтрации"
                        },
                        "project": {
                            "type": "string",
                            "description": "Проект для фильтрации"
                        },
                        "status": {
                            "type": "string",
                            "description": "Статус для фильтрации",
                            "enum": ["new", "in_progress", "completed", "cancelled", "all"]
                        },
                        "priority": {
                            "type": "string",
                            "description": "Приоритет для фильтрации",
                            "enum": ["low", "normal", "high", "critical", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "onec: Управление задачами и проектами в 1С через HTTP API. Инструменты: get_user_tasks, get_task_info, create_task, update_task, add_task_comment, list_projects, get_project_info, list_users, get_user_info, search_tasks"
    
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
                logger.info("ℹ️ 1С отключен в конфигурации")
                return
            
            if not all([self.url, self.username, self.password]):
                logger.warning("⚠️ Неполная конфигурация 1С")
                return
            
            # Создаем объект авторизации
            self.auth = HTTPBasicAuth(self.username, self.password)
            
            # Проверяем подключение
            self._test_connection()
            
            logger.info(f"✅ Подключение к 1С успешно: {self.url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к 1С: {e}")
            self.auth = None
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к 1С"""
        if not self.auth:
            return False
        
        try:
            # Пробуем выполнить простой запрос
            response = requests.get(
                f"{self.url}{self.api_path}/health",
                auth=self.auth,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ 1С
    # ============================================================================
    
    def get_user_tasks(self, user: str, status: str = "all", priority: str = "all",
                      limit: int = 50, include_completed: bool = False) -> Dict[str, Any]:
        """Получает список задач пользователя"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {
                'user': user,
                'limit': limit
            }
            
            if status != "all":
                params['status'] = status
            if priority != "all":
                params['priority'] = priority
            if include_completed:
                params['include_completed'] = 'true'
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}{self.api_path}",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', [])
                
                logger.info(f"✅ Получено задач пользователя {user}: {len(tasks)}")
                return format_tool_response(
                    True,
                    f"Получено задач пользователя {user}: {len(tasks)}",
                    {
                        "user": user,
                        "total": len(tasks),
                        "tasks": tasks,
                        "filters": {
                            "status": status,
                            "priority": priority,
                            "include_completed": include_completed
                        }
                    }
                )
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения задач пользователя: {e}")
            return format_tool_response(False, f"Ошибка получения задач пользователя: {str(e)}")
    
    def get_task_info(self, task_id: str, include_history: bool = False,
                     include_comments: bool = False, include_attachments: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию по задаче"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {}
            if include_history:
                params['include_history'] = 'true'
            if include_comments:
                params['include_comments'] = 'true'
            if include_attachments:
                params['include_attachments'] = 'true'
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}{self.api_path}/tasks/{task_id}",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                task_data = response.json()
                
                logger.info(f"✅ Получена информация о задаче: {task_id}")
                return format_tool_response(True, "Информация о задаче получена", task_data)
            elif response.status_code == 404:
                return format_tool_response(False, f"Задача {task_id} не найдена")
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о задаче: {e}")
            return format_tool_response(False, f"Ошибка получения информации о задаче: {str(e)}")
    
    def create_task(self, title: str, description: str, assignee: str,
                   priority: str = "normal", due_date: str = None,
                   project: str = None, tags: List[str] = None) -> Dict[str, Any]:
        """Создает новую задачу"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Данные для создания задачи
            task_data = {
                'title': title,
                'description': description,
                'assignee': assignee,
                'priority': priority
            }
            
            if due_date:
                task_data['due_date'] = due_date
            if project:
                task_data['project'] = project
            if tags:
                task_data['tags'] = tags
            
            # Выполняем HTTP запрос к API 1С
            response = requests.post(
                f"{self.url}{self.api_path}/task",
                auth=self.auth,
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 201:
                new_task = response.json()
                
                logger.info(f"✅ Создана задача: {new_task.get('id')}")
                return format_tool_response(
                    True,
                    f"Задача '{title}' создана успешно",
                    {
                        "task_id": new_task.get('id'),
                        "title": new_task.get('title'),
                        "status": new_task.get('status'),
                        "assignee": new_task.get('assignee'),
                        "url": f"{self.url}/tasks/{new_task.get('id')}"
                    }
                )
            else:
                return format_tool_response(False, f"Ошибка создания задачи: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания задачи: {e}")
            return format_tool_response(False, f"Ошибка создания задачи: {str(e)}")
    
    def update_task(self, task_id: str, title: str = None, description: str = None,
                   status: str = None, priority: str = None, assignee: str = None,
                   due_date: str = None) -> Dict[str, Any]:
        """Обновляет существующую задачу"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Данные для обновления задачи
            update_data = {}
            
            if title:
                update_data['title'] = title
            if description:
                update_data['description'] = description
            if status:
                update_data['status'] = status
            if priority:
                update_data['priority'] = priority
            if assignee:
                update_data['assignee'] = assignee
            if due_date:
                update_data['due_date'] = due_date
            
            # Выполняем HTTP запрос к API 1С
            response = requests.put(
                f"{self.url}{self.api_path}/{task_id}",
                auth=self.auth,
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                updated_task = response.json()
                
                logger.info(f"✅ Задача {task_id} обновлена")
                return format_tool_response(
                    True,
                    f"Задача {task_id} обновлена успешно",
                    {
                        "task_id": task_id,
                        "title": updated_task.get('title'),
                        "status": updated_task.get('status'),
                        "updated_fields": list(update_data.keys())
                    }
                )
            elif response.status_code == 404:
                return format_tool_response(False, f"Задача {task_id} не найдена")
            else:
                return format_tool_response(False, f"Ошибка обновления задачи: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления задачи: {e}")
            return format_tool_response(False, f"Ошибка обновления задачи: {str(e)}")
    
    def add_task_comment(self, task_id: str, comment: str, is_private: bool = False) -> Dict[str, Any]:
        """Добавляет комментарий к задаче"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Данные для комментария
            comment_data = {
                'comment': comment,
                'is_private': is_private
            }
            
            # Выполняем HTTP запрос к API 1С
            response = requests.post(
                f"{self.url}{self.api_path}/{task_id}/comments",
                auth=self.auth,
                json=comment_data,
                timeout=30
            )
            
            if response.status_code == 201:
                new_comment = response.json()
                
                logger.info(f"✅ Комментарий добавлен к задаче: {task_id}")
                return format_tool_response(
                    True,
                    f"Комментарий добавлен к задаче {task_id}",
                    {
                        "comment_id": new_comment.get('id'),
                        "task_id": task_id,
                        "comment": comment,
                        "is_private": is_private
                    }
                )
            elif response.status_code == 404:
                return format_tool_response(False, f"Задача {task_id} не найдена")
            else:
                return format_tool_response(False, f"Ошибка добавления комментария: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления комментария: {e}")
            return format_tool_response(False, f"Ошибка добавления комментария: {str(e)}")
    
    def list_projects(self, limit: int = 50, status: str = "all", include_stats: bool = False) -> Dict[str, Any]:
        """Получает список проектов"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {'limit': limit}
            if status != "all":
                params['status'] = status
            if include_stats:
                params['include_stats'] = 'true'
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}/api/projects",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get('projects', [])
                
                logger.info(f"✅ Получено проектов: {len(projects)}")
                return format_tool_response(True, f"Получено проектов: {len(projects)}", projects)
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка проектов: {e}")
            return format_tool_response(False, f"Ошибка получения списка проектов: {str(e)}")
    
    def get_project_info(self, project_id: str, include_tasks: bool = False,
                        include_members: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о проекте"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {}
            if include_tasks:
                params['include_tasks'] = 'true'
            if include_members:
                params['include_members'] = 'true'
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}/api/projects/{project_id}",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                project_data = response.json()
                
                logger.info(f"✅ Получена информация о проекте: {project_id}")
                return format_tool_response(True, "Информация о проекте получена", project_data)
            elif response.status_code == 404:
                return format_tool_response(False, f"Проект {project_id} не найден")
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о проекте: {e}")
            return format_tool_response(False, f"Ошибка получения информации о проекте: {str(e)}")
    
    def list_users(self, limit: int = 50, role: str = "all", status: str = "all") -> Dict[str, Any]:
        """Получает список пользователей"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {'limit': limit}
            if role != "all":
                params['role'] = role
            if status != "all":
                params['status'] = status
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}/api/users",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('users', [])
                
                logger.info(f"✅ Получено пользователей: {len(users)}")
                return format_tool_response(True, f"Получено пользователей: {len(users)}", users)
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка пользователей: {e}")
            return format_tool_response(False, f"Ошибка получения списка пользователей: {str(e)}")
    
    def get_user_info(self, username: str, include_tasks: bool = False,
                     include_projects: bool = False) -> Dict[str, Any]:
        """Получает информацию о пользователе"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {}
            if include_tasks:
                params['include_tasks'] = 'true'
            if include_projects:
                params['include_projects'] = 'true'
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}/api/users/{username}",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                logger.info(f"✅ Получена информация о пользователе: {username}")
                return format_tool_response(True, "Информация о пользователе получена", user_data)
            elif response.status_code == 404:
                return format_tool_response(False, f"Пользователь {username} не найден")
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о пользователе: {e}")
            return format_tool_response(False, f"Ошибка получения информации о пользователе: {str(e)}")
    
    def search_tasks(self, query: str, assignee: str = None, project: str = None,
                    status: str = "all", priority: str = "all", limit: int = 50) -> Dict[str, Any]:
        """Ищет задачи по различным критериям"""
        try:
            if not self.auth:
                return format_tool_response(False, "1С не подключен")
            
            # Параметры запроса
            params = {
                'query': query,
                'limit': limit
            }
            
            if assignee:
                params['assignee'] = assignee
            if project:
                params['project'] = project
            if status != "all":
                params['status'] = status
            if priority != "all":
                params['priority'] = priority
            
            # Выполняем HTTP запрос к API 1С
            response = requests.get(
                f"{self.url}/api/tasks/search",
                auth=self.auth,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', [])
                
                logger.info(f"✅ Найдено задач: {len(tasks)}")
                return format_tool_response(
                    True,
                    f"Найдено задач: {len(tasks)}",
                    {
                        "total": len(tasks),
                        "tasks": tasks,
                        "query": query,
                        "filters": {
                            "assignee": assignee,
                            "project": project,
                            "status": status,
                            "priority": priority
                        }
                    }
                )
            else:
                return format_tool_response(False, f"Ошибка API 1С: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска задач: {e}")
            return format_tool_response(False, f"Ошибка поиска задач: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья 1C сервера"""
        try:
            if not self.is_enabled():
                return {
                    'status': 'disabled',
                    'provider': 'onec',
                    'message': '1C отключен в конфигурации'
                }
            
            # Проверяем подключение к 1C
            if hasattr(self, 'auth') and self.auth:
                # Пытаемся выполнить простой запрос для проверки подключения
                response = requests.get(
                    f"{self.url}{self.api_path}/health",
                    auth=self.auth,
                    timeout=5
                )
                
                if response.status_code == 200:
                    return {
                        'status': 'healthy',
                        'provider': 'onec',
                        'message': f'Подключение к 1C успешно. Сервер: {self.url}',
                        'server_url': self.url
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'provider': 'onec',
                        'message': f'1C сервер недоступен. Статус: {response.status_code}'
                    }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'onec',
                    'message': '1C клиент не инициализирован'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья 1C: {e}")
            return {
                'status': 'unhealthy',
                'provider': 'onec',
                'error': str(e)
            }
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список инструментов 1C сервера"""
        return self.tools

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр 1C сервера
onec_server = OneCMCPServer()
