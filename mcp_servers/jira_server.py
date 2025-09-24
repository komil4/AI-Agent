#!/usr/bin/env python3
"""
MCP сервер для работы с Jira с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import logging
import requests
from jira import JIRA
from typing import Dict, Any, List, Optional
from datetime import datetime
from analyzers.code_analyzer import CodeAnalyzer
from .base_fastmcp_server import BaseFastMCPServer, create_tool_schema, validate_tool_parameters, format_tool_response

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class JiraFastMCPServer(BaseFastMCPServer):
    """MCP сервер для работы с Jira - управление задачами, проектами и отслеживанием проблем"""
    
    def __init__(self):
        """Инициализация Jira MCP сервера"""
        super().__init__("jira")
        self.jira_url = None
        self.username = None
        self.api_token = None
        self.jira = None
        self.code_analyzer = CodeAnalyzer()
        
        # Настройки для админ-панели
        self.display_name = "Jira MCP"
        self.icon = "fas fa-tasks"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL Jira', 'type': 'text', 'placeholder': 'https://your-domain.atlassian.net' },
            { 'key': 'username', 'label': 'Имя пользователя', 'type': 'text', 'placeholder': 'your-email@domain.com' },
            { 'key': 'api_token', 'label': 'API Token', 'type': 'password', 'placeholder': 'ваш API токен' },
            { 'key': 'project_key', 'label': 'Ключ проекта', 'type': 'text', 'placeholder': 'PROJ' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="create_issue",
                description="Создает новую задачу в Jira с указанными параметрами",
                parameters={
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Краткое описание задачи (обязательно)"
                        },
                        "description": {
                            "type": "string", 
                            "description": "Подробное описание задачи"
                        },
                        "project_key": {
                            "type": "string",
                            "description": "Ключ проекта (например, TEST)"
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Тип задачи (Task, Bug, Story, Epic)",
                            "enum": ["Task", "Bug", "Story", "Epic"]
                        },
                        "priority": {
                            "type": "string",
                            "description": "Приоритет задачи",
                            "enum": ["Highest", "High", "Medium", "Low", "Lowest"]
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Исполнитель задачи (username)"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Метки задачи"
                        }
                    },
                    "required": ["summary", "project_key"]
                }
            ),
            create_tool_schema(
                name="search_issues",
                description="Ищет задачи в Jira по JQL запросу с возможностью фильтрации",
                parameters={
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL запрос для поиска задач"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Поля для возврата (summary, status, assignee, etc.)"
                        }
                    },
                    "required": ["jql"]
                }
            ),
            create_tool_schema(
                name="get_issue_details",
                description="Получает детальную информацию о конкретной задаче",
                parameters={
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Ключ задачи (например, TEST-123)"
                        },
                        "include_comments": {
                            "type": "boolean",
                            "description": "Включать комментарии в результат"
                        },
                        "include_attachments": {
                            "type": "boolean", 
                            "description": "Включать информацию о вложениях"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),
            create_tool_schema(
                name="update_issue",
                description="Обновляет существующую задачу в Jira",
                parameters={
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Ключ задачи для обновления"
                        },
                        "summary": {
                            "type": "string",
                            "description": "Новое краткое описание"
                        },
                        "description": {
                            "type": "string",
                            "description": "Новое подробное описание"
                        },
                        "status": {
                            "type": "string",
                            "description": "Новый статус задачи"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Новый исполнитель"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Новый приоритет"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Новые метки"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),
            create_tool_schema(
                name="add_comment",
                description="Добавляет комментарий к задаче",
                parameters={
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Ключ задачи"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Текст комментария"
                        },
                        "visibility": {
                            "type": "string",
                            "description": "Видимость комментария",
                            "enum": ["public", "private"]
                        }
                    },
                    "required": ["issue_key", "comment"]
                }
            ),
            create_tool_schema(
                name="list_projects",
                description="Получает список доступных проектов в Jira",
                parameters={
                    "properties": {
                        "include_archived": {
                            "type": "boolean",
                            "description": "Включать архивированные проекты"
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_project_details",
                description="Получает детальную информацию о проекте",
                parameters={
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Ключ проекта"
                        }
                    },
                    "required": ["project_key"]
                }
            ),
            create_tool_schema(
                name="transition_issue",
                description="Переводит задачу в новый статус (workflow transition)",
                parameters={
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Ключ задачи"
                        },
                        "transition_name": {
                            "type": "string",
                            "description": "Название перехода (например, 'In Progress', 'Done')"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Комментарий к переходу"
                        }
                    },
                    "required": ["issue_key", "transition_name"]
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "Jira MCP сервер - управление задачами, проектами и отслеживанием проблем в Atlassian Jira"
    
    def _load_config(self):
        """Загружает конфигурацию Jira"""
        jira_config = self.config_manager.get_service_config('jira')
        self.jira_url = jira_config.get('url', '')
        self.username = jira_config.get('username', '')
        self.api_token = jira_config.get('api_token', '')
    
    def _connect(self):
        """Подключение к Jira"""
        try:
            jira_config = self.config_manager.get_service_config('jira')
            if not jira_config.get('enabled', False):
                logger.info("ℹ️ Jira отключен в конфигурации")
                return
            
            if not all([self.jira_url, self.username, self.api_token]):
                logger.warning("⚠️ Неполная конфигурация Jira")
                return
            
            # Подключение к Jira
            self.jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.username, self.api_token)
            )
            
            # Проверяем подключение
            self.jira.current_user()
            logger.info(f"✅ Подключение к Jira успешно: {self.jira_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Jira: {e}")
            self.jira = None
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к Jira"""
        if not self.jira:
            return False
        
        try:
            self.jira.current_user()
            return True
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ JIRA
    # ============================================================================
    
    def create_issue(self, summary: str, project_key: str, description: str = None, 
                    issue_type: str = "Task", priority: str = None, assignee: str = None,
                    labels: List[str] = None) -> Dict[str, Any]:
        """Создает новую задачу в Jira"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Подготавливаем данные для создания задачи
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'issuetype': {'name': issue_type}
            }
            
            if description:
                issue_dict['description'] = description
            
            if priority:
                issue_dict['priority'] = {'name': priority}
            
            if assignee:
                issue_dict['assignee'] = {'name': assignee}
            
            if labels:
                issue_dict['labels'] = labels
            
            # Создаем задачу
            new_issue = self.jira.create_issue(fields=issue_dict)
            
            logger.info(f"✅ Создана задача: {new_issue.key}")
            return format_tool_response(
                True, 
                f"Задача {new_issue.key} создана успешно",
                {
                    "issue_key": new_issue.key,
                    "summary": new_issue.fields.summary,
                    "status": new_issue.fields.status.name,
                    "url": f"{self.jira_url}/browse/{new_issue.key}"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания задачи: {e}")
            return format_tool_response(False, f"Ошибка создания задачи: {str(e)}")
    
    def search_issues(self, jql: str, max_results: int = 50, fields: List[str] = None) -> Dict[str, Any]:
        """Ищет задачи в Jira по JQL запросу"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Определяем поля для возврата
            if not fields:
                fields = ['summary', 'status', 'assignee', 'priority', 'created', 'updated']
            
            # Выполняем поиск
            issues = self.jira.search_issues(jql, maxResults=max_results, fields=fields)
            
            # Форматируем результаты
            results = []
            for issue in issues:
                issue_data = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name if issue.fields.status else None,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                    "url": f"{self.jira_url}/browse/{issue.key}"
                }
                results.append(issue_data)
            
            logger.info(f"✅ Найдено {len(results)} задач по запросу")
            return format_tool_response(
                True,
                f"Найдено {len(results)} задач",
                {
                    "total": len(results),
                    "issues": results,
                    "jql": jql
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска задач: {e}")
            return format_tool_response(False, f"Ошибка поиска задач: {str(e)}")
    
    def get_issue_details(self, issue_key: str, include_comments: bool = False, 
                         include_attachments: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о задаче"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Получаем задачу
            issue = self.jira.issue(issue_key)
            
            # Базовые данные
            issue_data = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "labels": issue.fields.labels,
                "url": f"{self.jira_url}/browse/{issue.key}"
            }
            
            # Комментарии
            if include_comments:
                comments = []
                for comment in issue.fields.comment.comments:
                    comments.append({
                        "author": comment.author.displayName,
                        "body": comment.body,
                        "created": comment.created
                    })
                issue_data["comments"] = comments
            
            # Вложения
            if include_attachments:
                attachments = []
                for attachment in issue.fields.attachment:
                    attachments.append({
                        "filename": attachment.filename,
                        "size": attachment.size,
                        "created": attachment.created,
                        "url": attachment.content
                    })
                issue_data["attachments"] = attachments
            
            logger.info(f"✅ Получены детали задачи: {issue_key}")
            return format_tool_response(True, "Детали задачи получены", issue_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей задачи: {e}")
            return format_tool_response(False, f"Ошибка получения деталей задачи: {str(e)}")
    
    def update_issue(self, issue_key: str, summary: str = None, description: str = None,
                    status: str = None, assignee: str = None, priority: str = None,
                    labels: List[str] = None) -> Dict[str, Any]:
        """Обновляет существующую задачу"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Получаем задачу
            issue = self.jira.issue(issue_key)
            
            # Подготавливаем поля для обновления
            update_fields = {}
            
            if summary:
                update_fields['summary'] = summary
            if description:
                update_fields['description'] = description
            if assignee:
                update_fields['assignee'] = {'name': assignee}
            if priority:
                update_fields['priority'] = {'name': priority}
            if labels:
                update_fields['labels'] = labels
            
            # Обновляем задачу
            if update_fields:
                issue.update(fields=update_fields)
            
            # Обновляем статус отдельно, если указан
            if status:
                transitions = self.jira.transitions(issue)
                for transition in transitions:
                    if transition['name'].lower() == status.lower():
                        self.jira.transition_issue(issue, transition['id'])
                        break
            
            logger.info(f"✅ Задача {issue_key} обновлена")
            return format_tool_response(True, f"Задача {issue_key} обновлена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления задачи: {e}")
            return format_tool_response(False, f"Ошибка обновления задачи: {str(e)}")
    
    def add_comment(self, issue_key: str, comment: str, visibility: str = "public") -> Dict[str, Any]:
        """Добавляет комментарий к задаче"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Добавляем комментарий
            self.jira.add_comment(issue_key, comment, visibility=visibility)
            
            logger.info(f"✅ Комментарий добавлен к задаче: {issue_key}")
            return format_tool_response(True, f"Комментарий добавлен к задаче {issue_key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления комментария: {e}")
            return format_tool_response(False, f"Ошибка добавления комментария: {str(e)}")
    
    def list_projects(self, include_archived: bool = False) -> Dict[str, Any]:
        """Получает список проектов"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Получаем проекты
            projects = self.jira.projects()
            
            # Фильтруем архивированные проекты
            if not include_archived:
                projects = [p for p in projects if not getattr(p, 'archived', False)]
            
            # Форматируем результаты
            project_list = []
            for project in projects:
                project_data = {
                    "key": project.key,
                    "name": project.name,
                    "description": getattr(project, 'description', ''),
                    "lead": getattr(project, 'lead', {}).get('displayName', ''),
                    "url": f"{self.jira_url}/browse/{project.key}"
                }
                project_list.append(project_data)
            
            logger.info(f"✅ Получен список проектов: {len(project_list)}")
            return format_tool_response(True, f"Получен список проектов", project_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка проектов: {e}")
            return format_tool_response(False, f"Ошибка получения списка проектов: {str(e)}")
    
    def get_project_details(self, project_key: str) -> Dict[str, Any]:
        """Получает детальную информацию о проекте"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Получаем проект
            project = self.jira.project(project_key)
            
            # Формируем данные проекта
            project_data = {
                "key": project.key,
                "name": project.name,
                "description": getattr(project, 'description', ''),
                "lead": getattr(project, 'lead', {}).get('displayName', ''),
                "projectType": getattr(project, 'projectTypeKey', ''),
                "url": f"{self.jira_url}/browse/{project.key}"
            }
            
            logger.info(f"✅ Получены детали проекта: {project_key}")
            return format_tool_response(True, "Детали проекта получены", project_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей проекта: {e}")
            return format_tool_response(False, f"Ошибка получения деталей проекта: {str(e)}")
    
    def transition_issue(self, issue_key: str, transition_name: str, comment: str = None) -> Dict[str, Any]:
        """Переводит задачу в новый статус"""
        try:
            if not self.jira:
                return format_tool_response(False, "Jira не подключен")
            
            # Получаем задачу
            issue = self.jira.issue(issue_key)
            
            # Получаем доступные переходы
            transitions = self.jira.transitions(issue)
            
            # Ищем нужный переход
            transition_id = None
            for transition in transitions:
                if transition['name'].lower() == transition_name.lower():
                    transition_id = transition['id']
                    break
            
            if not transition_id:
                available_transitions = [t['name'] for t in transitions]
                return format_tool_response(
                    False, 
                    f"Переход '{transition_name}' недоступен. Доступные: {', '.join(available_transitions)}"
                )
            
            # Выполняем переход
            self.jira.transition_issue(issue, transition_id, comment=comment)
            
            logger.info(f"✅ Задача {issue_key} переведена в статус: {transition_name}")
            return format_tool_response(True, f"Задача {issue_key} переведена в статус: {transition_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перехода задачи: {e}")
            return format_tool_response(False, f"Ошибка перехода задачи: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья Jira сервера"""
        try:
            if not self.is_enabled():
                return {
                    'status': 'disabled',
                    'provider': 'jira',
                    'message': 'Jira отключен в конфигурации'
                }
            
            # Проверяем подключение к Jira
            if hasattr(self, 'jira') and self.jira:
                # Пытаемся получить информацию о текущем пользователе
                current_user = self.jira.current_user()
                return {
                    'status': 'healthy',
                    'provider': 'jira',
                    'message': f'Подключение к Jira успешно. Пользователь: {current_user}',
                    'server_url': self.jira_url
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'jira',
                    'message': 'Jira клиент не инициализирован'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья Jira: {e}")
            return {
                'status': 'unhealthy',
                'provider': 'jira',
                'error': str(e)
            }

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр Jira сервера
jira_server = JiraFastMCPServer()
