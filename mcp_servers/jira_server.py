import os
import requests
from jira import JIRA
from typing import Dict, Any, List
from analyzers.code_analyzer import CodeAnalyzer
from config.config_manager import ConfigManager
from . import BaseMCPServer

class JiraMCPServer(BaseMCPServer):
    """MCP сервер для работы с Jira - управление задачами, проектами и отслеживанием проблем"""
    
    def __init__(self):
        super().__init__()
        self.description = "Jira - управление задачами, проектами и отслеживанием проблем"
        self.tools = [
            {
                "name": "create_issue",
                "description": "Создает новую задачу в Jira",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Краткое описание задачи"},
                        "description": {"type": "string", "description": "Подробное описание задачи"},
                        "project_key": {"type": "string", "description": "Ключ проекта (например, TEST)"},
                        "issue_type": {"type": "string", "description": "Тип задачи (Task, Bug, Story)"}
                    },
                    "required": ["summary", "project_key"]
                }
            },
            {
                "name": "search_issues",
                "description": "Ищет задачи в Jira по JQL запросу",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL запрос для поиска"},
                        "max_results": {"type": "integer", "description": "Максимальное количество результатов"}
                    },
                    "required": ["jql"]
                }
            },
            {
                "name": "list_issues",
                "description": "Получает список задач проекта",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_key": {"type": "string", "description": "Ключ проекта"},
                        "status": {"type": "string", "description": "Статус задач"},
                        "assignee": {"type": "string", "description": "Исполнитель задач"}
                    }
                }
            },
            {
                "name": "update_issue_status",
                "description": "Обновляет статус задачи",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Ключ задачи"},
                        "status": {"type": "string", "description": "Новый статус"}
                    },
                    "required": ["issue_key", "status"]
                }
            },
            {
                "name": "get_issue_details",
                "description": "Получает детальную информацию о задаче",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Ключ задачи"}
                    },
                    "required": ["issue_key"]
                }
            }
        ]
        
        self.config_manager = ConfigManager()
        self.jira_url = None
        self.username = None
        self.api_token = None
        self.jira = None
        self.code_analyzer = CodeAnalyzer()
        self._load_config()
        self._connect()
    
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
                print("⚠️ Jira отключен в конфигурации")
                return
                
            if self.jira_url and self.username and self.api_token:
                self.jira = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.username, self.api_token)
                )
                print("✅ Подключение к Jira успешно")
            else:
                print("⚠️ Jira не настроен - отсутствуют данные в конфигурации")
        except Exception as e:
            print(f"❌ Ошибка подключения к Jira: {e}")
    
    def reconnect(self):
        """Переподключается к Jira с новой конфигурацией"""
        self._load_config()
        self._connect()
    
    def process_command(self, message: str) -> str:
        """Обрабатывает команды для Jira (упрощенный метод)"""
        if not self.jira:
            return "❌ Jira не настроен. Проверьте переменные окружения."
        
        message_lower = message.lower()
        
        try:
            if any(word in message_lower for word in ['создать', 'новая', 'создай']):
                return self._create_issue(message)
            elif any(word in message_lower for word in ['найти', 'поиск', 'найди']):
                return self._search_issues(message)
            elif any(word in message_lower for word in ['список', 'все', 'показать']):
                return self._list_issues()
            elif any(word in message_lower for word in ['статус', 'обновить', 'изменить']):
                return self._update_issue_status(message)
            elif any(word in message_lower for word in ['проанализируй', 'анализ', 'анализируй']):
                return self._analyze_task_code(message)
            else:
                return self._get_help()
        except Exception as e:
            return f"❌ Ошибка при работе с Jira: {str(e)}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент Jira по имени"""
        if not self.jira:
            return {"error": "Jira не настроен"}
        
        try:
            if tool_name == "create_issue":
                return self._create_issue_tool(arguments)
            elif tool_name == "search_issues":
                return self._search_issues_tool(arguments)
            elif tool_name == "list_issues":
                return self._list_issues_tool(arguments)
            elif tool_name == "update_issue_status":
                return self._update_issue_status_tool(arguments)
            elif tool_name == "get_issue_details":
                return self._get_issue_details_tool(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def process_command_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Обрабатывает команды для Jira на основе анализа намерений"""
        if not self.jira:
            return "❌ Jira не настроен. Проверьте переменные окружения."
        
        try:
            # Временная заглушка для intent_analyzer
            class IntentType:
                JIRA_CREATE = "jira_create"
                JIRA_SEARCH = "jira_search"
                JIRA_LIST = "jira_list"
                JIRA_UPDATE = "jira_update"
                JIRA_ANALYZE = "jira_analyze"
            
            # Обрабатываем на основе намерения
            if intent_result.intent == IntentType.JIRA_CREATE:
                return self._create_issue_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.JIRA_SEARCH:
                return self._search_issues_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.JIRA_LIST:
                return self._list_issues_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.JIRA_UPDATE:
                return self._update_issue_status_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.JIRA_ANALYZE:
                return self._analyze_task_code_intelligent(message, intent_result)
            else:
                # Fallback к старому методу
                return self.process_command(message)
        except Exception as e:
            return f"❌ Ошибка при работе с Jira: {str(e)}"
    
    def _create_issue(self, message: str) -> str:
        """Создает новую задачу в Jira"""
        # Простое извлечение данных из сообщения
        issue_data = {
            'project': {'key': 'TEST'},  # Замените на ваш проект
            'summary': 'Новая задача из чат-бота',
            'description': message,
            'issuetype': {'name': 'Task'}
        }
        
        try:
            issue = self.jira.create_issue(fields=issue_data)
            return f"✅ Создана задача: {issue.key} - {issue.fields.summary}"
        except Exception as e:
            return f"❌ Ошибка создания задачи: {str(e)}"
    
    def _search_issues(self, message: str) -> str:
        """Поиск задач в Jira"""
        try:
            # Простой поиск по ключевым словам
            jql = f'text ~ "{message}" ORDER BY created DESC'
            issues = self.jira.search_issues(jql, maxResults=5)
            
            if not issues:
                return "🔍 Задачи не найдены"
            
            result = "🔍 Найденные задачи:\n"
            for issue in issues:
                result += f"• {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"
    
    def _list_issues(self) -> str:
        """Список последних задач"""
        try:
            jql = 'ORDER BY created DESC'
            issues = self.jira.search_issues(jql, maxResults=10)
            
            if not issues:
                return "📋 Задач не найдено"
            
            result = "📋 Последние задачи:\n"
            for issue in issues:
                result += f"• {issue.key}: {issue.fields.summary} ({issue.fields.status.name})\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    def _update_issue_status(self, message: str) -> str:
        """Обновляет статус задачи"""
        # Извлекаем ключ задачи из сообщения
        words = message.split()
        issue_key = None
        for word in words:
            if '-' in word and len(word.split('-')) == 2:
                issue_key = word
                break
        
        if not issue_key:
            return "❌ Не указан ключ задачи (например: TEST-123)"
        
        try:
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            if transitions:
                # Переводим в первый доступный статус
                transition_id = transitions[0]['id']
                self.jira.transition_issue(issue, transition_id)
                return f"✅ Статус задачи {issue_key} обновлен"
            else:
                return f"❌ Нет доступных переходов для задачи {issue_key}"
        except Exception as e:
            return f"❌ Ошибка обновления статуса: {str(e)}"
    
    def _analyze_task_code(self, message: str) -> str:
        """Анализирует код по задаче"""
        import re
        
        # Извлекаем номер задачи из сообщения
        task_pattern = r'№\s*([A-Z]+-\d+)|задач[аи]\s*№\s*([A-Z]+-\d+)|([A-Z]+-\d+)'
        matches = re.findall(task_pattern, message, re.IGNORECASE)
        
        task_key = None
        for match in matches:
            task_key = match[0] or match[1] or match[2]
            if task_key:
                break
        
        if not task_key:
            return """
❌ Не удалось найти номер задачи в сообщении.

Примеры использования:
- "проанализируй код под задачу №PROJ-123"
- "анализ задачи PROJ-456"
- "анализируй код задачи №TEST-789"
            """
        
        try:
            # Выполняем анализ
            report = self.code_analyzer.analyze_task_code(task_key)
            
            if not report:
                return f"❌ Не удалось проанализировать задачу {task_key}. Проверьте подключения к сервисам."
            
            # Генерируем отчет
            return self.code_analyzer.generate_report_text(report)
            
        except Exception as e:
            return f"❌ Ошибка анализа задачи {task_key}: {str(e)}"
    
    def _get_help(self) -> str:
        """Справка по командам Jira"""
        return """
🔧 Команды для работы с Jira:

• Создать задачу: "создай задачу в jira"
• Найти задачи: "найди задачи по ключевому слову"
• Список задач: "покажи все задачи"
• Обновить статус: "измени статус задачи TEST-123"
• Анализ кода: "проанализируй код под задачу №PROJ-123"

Примеры:
- "создай новую задачу в jira с описанием 'исправить баг'"
- "найди все задачи связанные с авторизацией"
- "покажи последние 10 задач"
- "проанализируй код под задачу №PROJ-123"
        """
    
    def _create_issue_intelligent(self, message: str, intent_result) -> str:
        """Создает новую задачу в Jira на основе анализа намерений"""
        try:
            # Извлекаем информацию из сущностей
            entities = intent_result.entities
            search_query = entities.get('search_query', '')
            
            # Создаем описание на основе сообщения
            description = message
            if search_query:
                description = f"{message}\n\nКлючевые слова: {search_query}"
            
            issue_data = {
                'project': {'key': 'TEST'},  # Замените на ваш проект
                'summary': f"Задача из чат-бота: {message[:50]}...",
                'description': description,
                'issuetype': {'name': 'Task'}
            }
            
            issue = self.jira.create_issue(fields=issue_data)
            return f"✅ Создана задача: {issue.key} - {issue.fields.summary}\n\n📝 Описание: {description}"
        except Exception as e:
            return f"❌ Ошибка создания задачи: {str(e)}"
    
    def _search_issues_intelligent(self, message: str, intent_result) -> str:
        """Поиск задач в Jira на основе анализа намерений"""
        try:
            entities = intent_result.entities
            search_query = entities.get('search_query', '')
            
            # Используем поисковый запрос из сущностей или весь текст сообщения
            query = search_query if search_query else message
            
            jql = f'text ~ "{query}" ORDER BY created DESC'
            issues = self.jira.search_issues(jql, maxResults=5)
            
            if not issues:
                return f"🔍 Задачи по запросу '{query}' не найдены"
            
            result = f"🔍 Найденные задачи по запросу '{query}':\n\n"
            for issue in issues:
                result += f"• **{issue.key}**: {issue.fields.summary} ({issue.fields.status.name})\n"
                result += f"  📅 Создана: {issue.fields.created[:10]}\n"
                result += f"  👤 Автор: {issue.fields.reporter.displayName}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"
    
    def _list_issues_intelligent(self, message: str, intent_result) -> str:
        """Список задач в Jira на основе анализа намерений"""
        try:
            # Определяем количество задач из сообщения
            import re
            count_match = re.search(r'(\d+)', message)
            max_results = int(count_match.group(1)) if count_match else 10
            
            jql = 'ORDER BY created DESC'
            issues = self.jira.search_issues(jql, maxResults=max_results)
            
            if not issues:
                return "📋 Задач не найдено"
            
            result = f"📋 Последние {len(issues)} задач:\n\n"
            for issue in issues:
                result += f"• **{issue.key}**: {issue.fields.summary}\n"
                result += f"  📊 Статус: {issue.fields.status.name}\n"
                result += f"  📅 Создана: {issue.fields.created[:10]}\n"
                result += f"  👤 Автор: {issue.fields.reporter.displayName}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    def _update_issue_status_intelligent(self, message: str, intent_result) -> str:
        """Обновляет статус задачи в Jira на основе анализа намерений"""
        try:
            entities = intent_result.entities
            task_key = entities.get('task_key', '')
            
            if not task_key:
                # Пытаемся найти ключ задачи в сообщении
                import re
                key_match = re.search(r'([A-Z]+-\d+)', message)
                if key_match:
                    task_key = key_match.group(1)
                else:
                    return "❌ Не указан ключ задачи (например: PROJ-123)"
            
            issue = self.jira.issue(task_key)
            transitions = self.jira.transitions(issue)
            
            if transitions:
                # Переводим в первый доступный статус
                transition_id = transitions[0]['id']
                transition_name = transitions[0]['name']
                self.jira.transition_issue(issue, transition_id)
                return f"✅ Задача {task_key} переведена в статус '{transition_name}'"
            else:
                return f"❌ Нет доступных переходов для задачи {task_key}"
        except Exception as e:
            return f"❌ Ошибка обновления статуса: {str(e)}"
    
    def _analyze_task_code_intelligent(self, message: str, intent_result) -> str:
        """Анализирует код по задаче на основе анализа намерений"""
        try:
            entities = intent_result.entities
            task_key = entities.get('task_key', '') or entities.get('task_number', '')
            
            if not task_key:
                # Пытаемся найти ключ задачи в сообщении
                import re
                key_match = re.search(r'([A-Z]+-\d+)', message)
                if key_match:
                    task_key = key_match.group(1)
                else:
                    return """
❌ Не удалось найти номер задачи в сообщении.

Примеры использования:
- "проанализируй код под задачу №PROJ-123"
- "анализ задачи PROJ-456"
- "анализируй код задачи №TEST-789"
                    """
            
            # Выполняем анализ
            report = self.code_analyzer.analyze_task_code(task_key)
            
            if not report:
                return f"❌ Не удалось проанализировать задачу {task_key}. Проверьте подключения к сервисам."
            
            # Генерируем отчет
            return self.code_analyzer.generate_report_text(report)
            
        except Exception as e:
            return f"❌ Ошибка анализа задачи: {str(e)}"
    
    def _create_issue_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Создает задачу через инструмент"""
        try:
            issue_data = {
                'project': {'key': arguments.get('project_key', 'TEST')},
                'summary': arguments.get('summary', 'Новая задача'),
                'description': arguments.get('description', ''),
                'issuetype': {'name': arguments.get('issue_type', 'Task')}
            }
            
            issue = self.jira.create_issue(fields=issue_data)
            return {
                'success': True,
                'issue_key': issue.key,
                'summary': issue.fields.summary,
                'url': f"{self.jira_url}/browse/{issue.key}"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _search_issues_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ищет задачи через инструмент"""
        try:
            jql = arguments.get('jql', 'ORDER BY created DESC')
            max_results = arguments.get('max_results', 10)
            
            issues = self.jira.search_issues(jql, maxResults=max_results)
            
            result = []
            for issue in issues:
                result.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Не назначен',
                    'created': str(issue.fields.created),
                    'url': f"{self.jira_url}/browse/{issue.key}"
                })
            
            return {'issues': result}
        except Exception as e:
            return {'error': str(e)}
    
    def _list_issues_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает список задач через инструмент"""
        try:
            max_results = arguments.get('max_results', 10)
            project_key = arguments.get('project_key')
            
            if project_key:
                jql = f'project = {project_key} ORDER BY created DESC'
            else:
                jql = 'ORDER BY created DESC'
            
            issues = self.jira.search_issues(jql, maxResults=max_results)
            
            result = []
            for issue in issues:
                result.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Не назначен',
                    'created': str(issue.fields.created),
                    'url': f"{self.jira_url}/browse/{issue.key}"
                })
            
            return {'issues': result}
        except Exception as e:
            return {'error': str(e)}
    
    def _update_issue_status_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет статус задачи через инструмент"""
        try:
            issue_key = arguments.get('issue_key')
            transition_name = arguments.get('transition_name')
            
            if not issue_key:
                return {'error': 'Не указан ключ задачи'}
            
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            if not transitions:
                return {'error': f'Нет доступных переходов для задачи {issue_key}'}
            
            # Если указано название перехода, ищем его
            if transition_name:
                transition = None
                for t in transitions:
                    if t['name'].lower() == transition_name.lower():
                        transition = t
                        break
                
                if not transition:
                    return {'error': f'Переход "{transition_name}" не найден'}
                
                self.jira.transition_issue(issue, transition['id'])
                return {
                    'success': True,
                    'issue_key': issue_key,
                    'new_status': transition['name']
                }
            else:
                # Используем первый доступный переход
                transition = transitions[0]
                self.jira.transition_issue(issue, transition['id'])
                return {
                    'success': True,
                    'issue_key': issue_key,
                    'new_status': transition['name']
                }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_issue_details_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает детали задачи через инструмент"""
        try:
            issue_key = arguments.get('issue_key')
            
            if not issue_key:
                return {'error': 'Не указан ключ задачи'}
            
            issue = self.jira.issue(issue_key)
            
            return {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': issue.fields.description,
                'status': issue.fields.status.name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Не назначен',
                'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Неизвестно',
                'created': str(issue.fields.created),
                'updated': str(issue.fields.updated),
                'priority': issue.fields.priority.name if issue.fields.priority else 'Не указан',
                'url': f"{self.jira_url}/browse/{issue.key}"
            }
        except Exception as e:
            return {'error': str(e)}

    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов Jira"""
        return [
            {
                "name": "create_issue",
                "description": "Создает новую задачу в Jira",
                "parameters": {
                    "summary": {"type": "string", "description": "Краткое описание задачи"},
                    "description": {"type": "string", "description": "Подробное описание задачи"},
                    "project_key": {"type": "string", "description": "Ключ проекта (например, TEST)"},
                    "issue_type": {"type": "string", "description": "Тип задачи (Task, Bug, Story)"}
                }
            },
            {
                "name": "search_issues",
                "description": "Ищет задачи в Jira по JQL запросу",
                "parameters": {
                    "jql": {"type": "string", "description": "JQL запрос для поиска"},
                    "max_results": {"type": "integer", "description": "Максимальное количество результатов"}
                }
            },
            {
                "name": "list_issues",
                "description": "Получает список последних задач",
                "parameters": {
                    "max_results": {"type": "integer", "description": "Максимальное количество результатов"},
                    "project_key": {"type": "string", "description": "Фильтр по проекту"}
                }
            },
            {
                "name": "update_issue_status",
                "description": "Обновляет статус задачи",
                "parameters": {
                    "issue_key": {"type": "string", "description": "Ключ задачи (например, TEST-123)"},
                    "transition_name": {"type": "string", "description": "Название перехода статуса"}
                }
            },
            {
                "name": "get_issue_details",
                "description": "Получает детальную информацию о задаче",
                "parameters": {
                    "issue_key": {"type": "string", "description": "Ключ задачи"}
                }
            }
        ]

    def check_health(self) -> Dict[str, Any]:
        """Проверка состояния подключения к Jira"""
        try:
            if self.jira:
                # Проверяем подключение
                self.jira.projects()
                return {'status': 'connected', 'url': self.jira_url}
            else:
                return {'status': 'not_configured', 'url': None}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'url': self.jira_url}
