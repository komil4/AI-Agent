#!/usr/bin/env python3
"""
MCP сервер для работы с GitLab с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import gitlab
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_mcp_server import BaseMCPServer, create_tool_schema, validate_tool_parameters, format_tool_response

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class GitLabMCPServer(BaseMCPServer):
    """MCP сервер для работы с GitLab - управление репозиториями, проектами, merge requests и коммитами"""
    
    def __init__(self):
        """Инициализация GitLab MCP сервера"""
        # Инициализируем переменные ДО вызова super().__init__()
        self.gitlab_url = None
        self.access_token = None
        self.gitlab = None
        
        # Теперь вызываем родительский конструктор
        super().__init__("gitlab")
        
        # Настройки для админ-панели
        self.display_name = "GitLab MCP"
        self.icon = "fab fa-gitlab"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL GitLab', 'type': 'text', 'placeholder': 'https://gitlab.com' },
            { 'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'placeholder': 'ваш access token' },
            { 'key': 'project_id', 'label': 'ID проекта', 'type': 'text', 'placeholder': '12345' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="list_projects",
                description="Получает список проектов GitLab с возможностью поиска и фильтрации",
                parameters={
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "Поисковый запрос для фильтрации проектов"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Количество результатов на странице (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "visibility": {
                            "type": "string",
                            "description": "Видимость проектов",
                            "enum": ["private", "internal", "public"]
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Поле для сортировки",
                            "enum": ["id", "name", "path", "created_at", "updated_at", "last_activity_at"]
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_project_details",
                description="Получает детальную информацию о конкретном проекте GitLab",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта (например, 'group/project')"
                        },
                        "include_statistics": {
                            "type": "boolean",
                            "description": "Включать статистику проекта (коммиты, размер репозитория)"
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            create_tool_schema(
                name="get_project_commits",
                description="Получает список коммитов проекта с возможностью фильтрации",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Ветка для получения коммитов (по умолчанию main/master)"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Количество коммитов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "author_email": {
                            "type": "string",
                            "description": "Email автора для фильтрации коммитов"
                        },
                        "since": {
                            "type": "string",
                            "description": "Дата начала периода (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "Дата окончания периода (ISO 8601)"
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            create_tool_schema(
                name="create_merge_request",
                description="Создает новый merge request в GitLab",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "title": {
                            "type": "string",
                            "description": "Заголовок merge request"
                        },
                        "description": {
                            "type": "string",
                            "description": "Описание merge request"
                        },
                        "source_branch": {
                            "type": "string",
                            "description": "Исходная ветка"
                        },
                        "target_branch": {
                            "type": "string",
                            "description": "Целевая ветка (по умолчанию main/master)"
                        },
                        "assignee_id": {
                            "type": "integer",
                            "description": "ID пользователя для назначения"
                        },
                        "reviewer_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "ID пользователей для ревью"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Метки для merge request"
                        }
                    },
                    "required": ["project_id", "title", "source_branch"]
                }
            ),
            create_tool_schema(
                name="list_merge_requests",
                description="Получает список merge requests проекта",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "state": {
                            "type": "string",
                            "description": "Состояние merge request",
                            "enum": ["opened", "closed", "merged", "all"]
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "author_id": {
                            "type": "integer",
                            "description": "ID автора для фильтрации"
                        },
                        "assignee_id": {
                            "type": "integer",
                            "description": "ID исполнителя для фильтрации"
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            create_tool_schema(
                name="get_merge_request_details",
                description="Получает детальную информацию о merge request",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "merge_request_iid": {
                            "type": "integer",
                            "description": "IID merge request"
                        },
                        "include_commits": {
                            "type": "boolean",
                            "description": "Включать список коммитов"
                        },
                        "include_changes": {
                            "type": "boolean",
                            "description": "Включать изменения файлов"
                        }
                    },
                    "required": ["project_id", "merge_request_iid"]
                }
            ),
            create_tool_schema(
                name="update_merge_request",
                description="Обновляет существующий merge request",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "merge_request_iid": {
                            "type": "integer",
                            "description": "IID merge request"
                        },
                        "title": {
                            "type": "string",
                            "description": "Новый заголовок"
                        },
                        "description": {
                            "type": "string",
                            "description": "Новое описание"
                        },
                        "assignee_id": {
                            "type": "integer",
                            "description": "ID нового исполнителя"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Новые метки"
                        },
                        "state_event": {
                            "type": "string",
                            "description": "Изменение состояния",
                            "enum": ["close", "reopen"]
                        }
                    },
                    "required": ["project_id", "merge_request_iid"]
                }
            ),
            create_tool_schema(
                name="list_branches",
                description="Получает список веток проекта",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Количество результатов (по умолчанию 20)",
                            "minimum": 1,
                            "maximum": 100
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            create_tool_schema(
                name="create_branch",
                description="Создает новую ветку в проекте",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Название новой ветки"
                        },
                        "ref": {
                            "type": "string",
                            "description": "Базовая ветка или коммит (по умолчанию main/master)"
                        }
                    },
                    "required": ["project_id", "branch_name"]
                }
            ),
            create_tool_schema(
                name="get_file_content",
                description="Получает содержимое файла из репозитория",
                parameters={
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID или путь проекта"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Путь к файлу в репозитории"
                        },
                        "ref": {
                            "type": "string",
                            "description": "Ветка или коммит (по умолчанию main/master)"
                        }
                    },
                    "required": ["project_id", "file_path"]
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "gitlab: Управление проектами, ветками, merge requests в GitLab. Инструменты: list_projects, get_project_details, get_project_commits, create_merge_request, list_merge_requests, list_branches, create_branch, get_file_content"
    
    def _load_config(self):
        """Загружает конфигурацию GitLab"""
        gitlab_config = self.config_manager.get_service_config('gitlab')
        self.gitlab_url = gitlab_config.get('url', '')
        self.access_token = gitlab_config.get('token', '')
    
    def _connect(self):
        """Подключение к GitLab"""
        try:
            gitlab_config = self.config_manager.get_service_config('gitlab')
            if not gitlab_config.get('enabled', False):
                logger.info("ℹ️ GitLab отключен в конфигурации")
                return
            
            if not all([self.gitlab_url, self.access_token]):
                logger.warning("⚠️ Неполная конфигурация GitLab")
                return
            
            # Подключение к GitLab
            self.gitlab = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token)
            self.gitlab.auth()
            
            logger.info(f"✅ Подключение к GitLab успешно: {self.gitlab_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к GitLab: {e}")
            self.gitlab = None
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к GitLab"""
        if not self.gitlab:
            return False
        
        try:
            self.gitlab.auth()
            return True
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ GITLAB
    # ============================================================================
    
    def list_projects(self, search: str = None, per_page: int = 20, visibility: str = None,
                     order_by: str = "last_activity_at") -> Dict[str, Any]:
        """Получает список проектов GitLab"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Параметры поиска
            params = {
                'per_page': per_page,
                'order_by': order_by
            }
            
            if search:
                params['search'] = search
            if visibility:
                params['visibility'] = visibility
            
            # Получаем проекты
            projects = self.gitlab.projects.list(**params)
            
            # Форматируем результаты
            project_list = []
            for project in projects:
                project_data = {
                    "id": project.id,
                    "name": project.name,
                    "path": project.path,
                    "full_path": project.path_with_namespace,
                    "description": project.description,
                    "visibility": project.visibility,
                    "created_at": project.created_at,
                    "last_activity_at": project.last_activity_at,
                    "web_url": project.web_url
                }
                project_list.append(project_data)
            
            logger.info(f"✅ Получен список проектов: {len(project_list)}")
            return format_tool_response(True, f"Получен список проектов", project_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка проектов: {e}")
            return format_tool_response(False, f"Ошибка получения списка проектов: {str(e)}")
    
    def get_project_details(self, project_id: str, include_statistics: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о проекте"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Базовые данные
            project_data = {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "full_path": project.path_with_namespace,
                "description": project.description,
                "visibility": project.visibility,
                "created_at": project.created_at,
                "last_activity_at": project.last_activity_at,
                "web_url": project.web_url,
                "ssh_url": project.ssh_url_to_repo,
                "http_url": project.http_url_to_repo
            }
            
            # Статистика
            if include_statistics:
                try:
                    stats = project.statistics.get()
                    project_data["statistics"] = {
                        "commit_count": stats.commit_count,
                        "repository_size": stats.repository_size,
                        "lfs_objects_size": stats.lfs_objects_size,
                        "build_artifacts_size": stats.build_artifacts_size
                    }
                except Exception:
                    project_data["statistics"] = "Недоступно"
            
            logger.info(f"✅ Получены детали проекта: {project_id}")
            return format_tool_response(True, "Детали проекта получены", project_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей проекта: {e}")
            return format_tool_response(False, f"Ошибка получения деталей проекта: {str(e)}")
    
    def get_project_commits(self, project_id: str, branch: str = None, per_page: int = 20,
                           author_email: str = None, since: str = None, until: str = None) -> Dict[str, Any]:
        """Получает список коммитов проекта"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Параметры для получения коммитов
            params = {'per_page': per_page}
            
            if branch:
                params['ref_name'] = branch
            if author_email:
                params['author_email'] = author_email
            if since:
                params['since'] = since
            if until:
                params['until'] = until
            
            # Получаем коммиты
            commits = project.commits.list(**params)
            
            # Форматируем результаты
            commit_list = []
            for commit in commits:
                commit_data = {
                    "id": commit.id,
                    "short_id": commit.short_id,
                    "title": commit.title,
                    "message": commit.message,
                    "author_name": commit.author_name,
                    "author_email": commit.author_email,
                    "committer_name": commit.committer_name,
                    "committer_email": commit.committer_email,
                    "created_at": commit.created_at,
                    "web_url": commit.web_url
                }
                commit_list.append(commit_data)
            
            logger.info(f"✅ Получены коммиты проекта: {len(commit_list)}")
            return format_tool_response(True, f"Получены коммиты проекта", commit_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения коммитов: {e}")
            return format_tool_response(False, f"Ошибка получения коммитов: {str(e)}")
    
    def create_merge_request(self, project_id: str, title: str, source_branch: str,
                            description: str = None, target_branch: str = None,
                            assignee_id: int = None, reviewer_ids: List[int] = None,
                            labels: List[str] = None) -> Dict[str, Any]:
        """Создает новый merge request"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Параметры для создания MR
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch or 'main',
                'title': title
            }
            
            if description:
                mr_data['description'] = description
            if assignee_id:
                mr_data['assignee_id'] = assignee_id
            if reviewer_ids:
                mr_data['reviewer_ids'] = reviewer_ids
            if labels:
                mr_data['labels'] = labels
            
            # Создаем merge request
            mr = project.mergerequests.create(mr_data)
            
            logger.info(f"✅ Создан merge request: {mr.iid}")
            return format_tool_response(
                True,
                f"Merge request #{mr.iid} создан успешно",
                {
                    "iid": mr.iid,
                    "title": mr.title,
                    "state": mr.state,
                    "source_branch": mr.source_branch,
                    "target_branch": mr.target_branch,
                    "web_url": mr.web_url
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания merge request: {e}")
            return format_tool_response(False, f"Ошибка создания merge request: {str(e)}")
    
    def list_merge_requests(self, project_id: str, state: str = "opened", per_page: int = 20,
                           author_id: int = None, assignee_id: int = None) -> Dict[str, Any]:
        """Получает список merge requests проекта"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Параметры для поиска MR
            params = {
                'state': state,
                'per_page': per_page
            }
            
            if author_id:
                params['author_id'] = author_id
            if assignee_id:
                params['assignee_id'] = assignee_id
            
            # Получаем merge requests
            mrs = project.mergerequests.list(**params)
            
            # Форматируем результаты
            mr_list = []
            for mr in mrs:
                mr_data = {
                    "iid": mr.iid,
                    "title": mr.title,
                    "description": mr.description,
                    "state": mr.state,
                    "source_branch": mr.source_branch,
                    "target_branch": mr.target_branch,
                    "author": mr.author['name'] if mr.author else None,
                    "assignee": mr.assignee['name'] if mr.assignee else None,
                    "created_at": mr.created_at,
                    "updated_at": mr.updated_at,
                    "web_url": mr.web_url
                }
                mr_list.append(mr_data)
            
            logger.info(f"✅ Получены merge requests: {len(mr_list)}")
            return format_tool_response(True, f"Получены merge requests", mr_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения merge requests: {e}")
            return format_tool_response(False, f"Ошибка получения merge requests: {str(e)}")
    
    def get_merge_request_details(self, project_id: str, merge_request_iid: int,
                                 include_commits: bool = False, include_changes: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о merge request"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Получаем merge request
            mr = project.mergerequests.get(merge_request_iid)
            
            # Базовые данные
            mr_data = {
                "iid": mr.iid,
                "title": mr.title,
                "description": mr.description,
                "state": mr.state,
                "source_branch": mr.source_branch,
                "target_branch": mr.target_branch,
                "author": mr.author['name'] if mr.author else None,
                "assignee": mr.assignee['name'] if mr.assignee else None,
                "created_at": mr.created_at,
                "updated_at": mr.updated_at,
                "web_url": mr.web_url,
                "labels": mr.labels
            }
            
            # Коммиты
            if include_commits:
                try:
                    commits = mr.commits()
                    mr_data["commits"] = [
                        {
                            "id": commit['id'],
                            "title": commit['title'],
                            "author_name": commit['author_name'],
                            "created_at": commit['created_at']
                        }
                        for commit in commits
                    ]
                except Exception:
                    mr_data["commits"] = "Недоступно"
            
            # Изменения
            if include_changes:
                try:
                    changes = mr.changes()
                    mr_data["changes"] = [
                        {
                            "old_path": change['old_path'],
                            "new_path": change['new_path'],
                            "diff": change['diff']
                        }
                        for change in changes['changes']
                    ]
                except Exception:
                    mr_data["changes"] = "Недоступно"
            
            logger.info(f"✅ Получены детали merge request: {merge_request_iid}")
            return format_tool_response(True, "Детали merge request получены", mr_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей merge request: {e}")
            return format_tool_response(False, f"Ошибка получения деталей merge request: {str(e)}")
    
    def update_merge_request(self, project_id: str, merge_request_iid: int, title: str = None,
                            description: str = None, assignee_id: int = None,
                            labels: List[str] = None, state_event: str = None) -> Dict[str, Any]:
        """Обновляет существующий merge request"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Получаем merge request
            mr = project.mergerequests.get(merge_request_iid)
            
            # Подготавливаем данные для обновления
            update_data = {}
            
            if title:
                update_data['title'] = title
            if description:
                update_data['description'] = description
            if assignee_id:
                update_data['assignee_id'] = assignee_id
            if labels:
                update_data['labels'] = labels
            if state_event:
                update_data['state_event'] = state_event
            
            # Обновляем merge request
            if update_data:
                mr.save()
            
            logger.info(f"✅ Merge request {merge_request_iid} обновлен")
            return format_tool_response(True, f"Merge request #{merge_request_iid} обновлен успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления merge request: {e}")
            return format_tool_response(False, f"Ошибка обновления merge request: {str(e)}")
    
    def list_branches(self, project_id: str, per_page: int = 20) -> Dict[str, Any]:
        """Получает список веток проекта"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Получаем ветки
            branches = project.branches.list(per_page=per_page)
            
            # Форматируем результаты
            branch_list = []
            for branch in branches:
                branch_data = {
                    "name": branch.name,
                    "default": branch.default,
                    "protected": branch.protected,
                    "developers_can_push": branch.developers_can_push,
                    "developers_can_merge": branch.developers_can_merge,
                    "commit": {
                        "id": branch.commit['id'],
                        "short_id": branch.commit['short_id'],
                        "title": branch.commit['title'],
                        "author_name": branch.commit['author_name'],
                        "created_at": branch.commit['created_at']
                    }
                }
                branch_list.append(branch_data)
            
            logger.info(f"✅ Получены ветки проекта: {len(branch_list)}")
            return format_tool_response(True, f"Получены ветки проекта", branch_list)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения веток: {e}")
            return format_tool_response(False, f"Ошибка получения веток: {str(e)}")
    
    def create_branch(self, project_id: str, branch_name: str, ref: str = None) -> Dict[str, Any]:
        """Создает новую ветку в проекте"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Создаем ветку
            branch_data = {
                'branch': branch_name,
                'ref': ref or 'main'
            }
            
            branch = project.branches.create(branch_data)
            
            logger.info(f"✅ Создана ветка: {branch_name}")
            return format_tool_response(
                True,
                f"Ветка '{branch_name}' создана успешно",
                {
                    "name": branch.name,
                    "default": branch.default,
                    "protected": branch.protected,
                    "commit": branch.commit
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания ветки: {e}")
            return format_tool_response(False, f"Ошибка создания ветки: {str(e)}")
    
    def get_file_content(self, project_id: str, file_path: str, ref: str = None) -> Dict[str, Any]:
        """Получает содержимое файла из репозитория"""
        try:
            if not self.gitlab:
                return format_tool_response(False, "GitLab не подключен")
            
            # Получаем проект
            project = self.gitlab.projects.get(project_id)
            
            # Получаем файл
            file_content = project.files.get(file_path, ref=ref or 'main')
            
            logger.info(f"✅ Получено содержимое файла: {file_path}")
            return format_tool_response(
                True,
                f"Содержимое файла '{file_path}' получено",
                {
                    "file_path": file_path,
                    "content": file_content.decode(),
                    "encoding": file_content.encoding,
                    "size": file_content.size,
                    "ref": ref or 'main'
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения файла: {e}")
            return format_tool_response(False, f"Ошибка получения файла: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья GitLab сервера"""
        try:
            if not self.is_enabled():
                return {
                    'status': 'disabled',
                    'provider': 'gitlab',
                    'message': 'GitLab отключен в конфигурации'
                }
            
            # Проверяем подключение к GitLab
            if hasattr(self, 'gitlab') and self.gitlab:
                # Пытаемся получить информацию о текущем пользователе
                current_user = self.gitlab.user
                return {
                    'status': 'healthy',
                    'provider': 'gitlab',
                    'message': f'Подключение к GitLab успешно. Пользователь: {current_user.username}',
                    'server_url': self.gitlab_url
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'gitlab',
                    'message': 'GitLab клиент не инициализирован'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья GitLab: {e}")
            return {
                'status': 'unhealthy',
                'provider': 'gitlab',
                'error': str(e)
            }
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список инструментов GitLab сервера"""
        return self.tools

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр GitLab сервера
gitlab_server = GitLabMCPServer()
