#!/usr/bin/env python3
"""
Пример использования MCP серверов с стандартом Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import asyncio
import logging
from typing import Dict, Any

# Импорт MCP серверов
from mcp_servers.jira_server_fastmcp import JiraFastMCPServer
from mcp_servers.gitlab_server_fastmcp import GitLabFastMCPServer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class MCPExample:
    """Пример использования MCP серверов с стандартом Anthropic"""
    
    def __init__(self):
        """Инициализация примера"""
        self.jira_server = JiraFastMCPServer()
        self.gitlab_server = GitLabFastMCPServer()
    
    async def demonstrate_jira_tools(self):
        """Демонстрация инструментов Jira"""
        logger.info("🔧 Демонстрация инструментов Jira")
        
        # Проверяем подключение
        if not self.jira_server.is_enabled():
            logger.warning("⚠️ Jira сервер отключен")
            return
        
        # 1. Получение списка проектов
        logger.info("📋 Получение списка проектов...")
        projects_result = self.jira_server.list_projects()
        if projects_result["success"]:
            logger.info(f"✅ Найдено проектов: {len(projects_result['data'])}")
            for project in projects_result["data"][:3]:  # Показываем первые 3
                logger.info(f"   - {project['key']}: {project['name']}")
        
        # 2. Создание задачи (пример)
        logger.info("📝 Создание задачи...")
        create_result = self.jira_server.create_issue(
            summary="Тестовая задача из MCP",
            project_key="TEST",  # Замените на реальный ключ проекта
            description="Эта задача создана через MCP сервер с использованием стандарта Anthropic",
            issue_type="Task",
            priority="Medium"
        )
        
        if create_result["success"]:
            issue_key = create_result["data"]["issue_key"]
            logger.info(f"✅ Задача создана: {issue_key}")
            
            # 3. Получение деталей задачи
            logger.info("🔍 Получение деталей задачи...")
            details_result = self.jira_server.get_issue_details(
                issue_key=issue_key,
                include_comments=True,
                include_attachments=True
            )
            
            if details_result["success"]:
                details = details_result["data"]
                logger.info(f"✅ Детали задачи получены:")
                logger.info(f"   - Статус: {details['status']}")
                logger.info(f"   - Приоритет: {details['priority']}")
                logger.info(f"   - Исполнитель: {details['assignee']}")
                logger.info(f"   - URL: {details['url']}")
        
        # 4. Поиск задач
        logger.info("🔍 Поиск задач...")
        search_result = self.jira_server.search_issues(
            jql="project = TEST AND status = 'To Do'",
            max_results=10,
            fields=["summary", "status", "assignee", "priority"]
        )
        
        if search_result["success"]:
            logger.info(f"✅ Найдено задач: {search_result['data']['total']}")
            for issue in search_result["data"]["issues"][:3]:  # Показываем первые 3
                logger.info(f"   - {issue['key']}: {issue['summary']} ({issue['status']})")
    
    async def demonstrate_gitlab_tools(self):
        """Демонстрация инструментов GitLab"""
        logger.info("🔧 Демонстрация инструментов GitLab")
        
        # Проверяем подключение
        if not self.gitlab_server.is_enabled():
            logger.warning("⚠️ GitLab сервер отключен")
            return
        
        # 1. Получение списка проектов
        logger.info("📋 Получение списка проектов...")
        projects_result = self.gitlab_server.list_projects(
            search="",  # Все проекты
            per_page=10,
            visibility="public",
            order_by="last_activity_at"
        )
        
        if projects_result["success"]:
            logger.info(f"✅ Найдено проектов: {len(projects_result['data'])}")
            for project in projects_result["data"][:3]:  # Показываем первые 3
                logger.info(f"   - {project['full_path']}: {project['name']}")
        
        # 2. Получение деталей проекта (если есть проекты)
        if projects_result["success"] and projects_result["data"]:
            project_id = projects_result["data"][0]["id"]
            logger.info(f"🔍 Получение деталей проекта {project_id}...")
            
            details_result = self.gitlab_server.get_project_details(
                project_id=str(project_id),
                include_statistics=True
            )
            
            if details_result["success"]:
                details = details_result["data"]
                logger.info(f"✅ Детали проекта получены:")
                logger.info(f"   - Название: {details['name']}")
                logger.info(f"   - Путь: {details['full_path']}")
                logger.info(f"   - Видимость: {details['visibility']}")
                logger.info(f"   - URL: {details['web_url']}")
                
                if "statistics" in details and details["statistics"] != "Недоступно":
                    stats = details["statistics"]
                    logger.info(f"   - Коммитов: {stats.get('commit_count', 'N/A')}")
                    logger.info(f"   - Размер репозитория: {stats.get('repository_size', 'N/A')} байт")
        
        # 3. Получение коммитов проекта
        if projects_result["success"] and projects_result["data"]:
            project_id = projects_result["data"][0]["id"]
            logger.info(f"📝 Получение коммитов проекта {project_id}...")
            
            commits_result = self.gitlab_server.get_project_commits(
                project_id=str(project_id),
                per_page=5,
                branch="main"  # или "master"
            )
            
            if commits_result["success"]:
                logger.info(f"✅ Получено коммитов: {len(commits_result['data'])}")
                for commit in commits_result["data"][:3]:  # Показываем первые 3
                    logger.info(f"   - {commit['short_id']}: {commit['title']} ({commit['author_name']})")
        
        # 4. Получение веток проекта
        if projects_result["success"] and projects_result["data"]:
            project_id = projects_result["data"][0]["id"]
            logger.info(f"🌿 Получение веток проекта {project_id}...")
            
            branches_result = self.gitlab_server.list_branches(
                project_id=str(project_id),
                per_page=10
            )
            
            if branches_result["success"]:
                logger.info(f"✅ Получено веток: {len(branches_result['data'])}")
                for branch in branches_result["data"][:5]:  # Показываем первые 5
                    logger.info(f"   - {branch['name']} {'(default)' if branch['default'] else ''}")
    
    async def demonstrate_tool_schemas(self):
        """Демонстрация схем инструментов"""
        logger.info("📋 Демонстрация схем инструментов")
        
        # Jira инструменты
        logger.info("🔧 Схемы инструментов Jira:")
        for tool in self.jira_server.tools:
            logger.info(f"   - {tool['name']}: {tool['description']}")
            required = tool['inputSchema'].get('required', [])
            if required:
                logger.info(f"     Обязательные параметры: {', '.join(required)}")
        
        # GitLab инструменты
        logger.info("🔧 Схемы инструментов GitLab:")
        for tool in self.gitlab_server.tools:
            logger.info(f"   - {tool['name']}: {tool['description']}")
            required = tool['inputSchema'].get('required', [])
            if required:
                logger.info(f"     Обязательные параметры: {', '.join(required)}")
    
    async def run_demo(self):
        """Запуск полной демонстрации"""
        logger.info("🚀 Запуск демонстрации MCP серверов с стандартом Anthropic")
        
        # Информация о серверах
        logger.info("📊 Информация о серверах:")
        logger.info(f"   - Jira: {'✅ Включен' if self.jira_server.is_enabled() else '❌ Отключен'}")
        logger.info(f"   - GitLab: {'✅ Включен' if self.gitlab_server.is_enabled() else '❌ Отключен'}")
        
        # Демонстрация схем
        await self.demonstrate_tool_schemas()
        
        # Демонстрация Jira
        await self.demonstrate_jira_tools()
        
        # Демонстрация GitLab
        await self.demonstrate_gitlab_tools()
        
        logger.info("✅ Демонстрация завершена")

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

async def main():
    """Главная функция"""
    example = MCPExample()
    await example.run_demo()

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())
