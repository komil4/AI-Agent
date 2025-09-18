import os
import gitlab
from typing import Dict, Any, List
from config.config_manager import ConfigManager

class GitLabMCPServer:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.gitlab_url = None
        self.gitlab_token = None
        self.gl = None
        self._load_config()
        self._connect()
    
    def _load_config(self):
        """Загружает конфигурацию GitLab"""
        gitlab_config = self.config_manager.get_service_config('gitlab')
        self.gitlab_url = gitlab_config.get('url', '')
        self.gitlab_token = gitlab_config.get('token', '')
    
    def _connect(self):
        """Подключение к GitLab"""
        try:
            gitlab_config = self.config_manager.get_service_config('gitlab')
            if not gitlab_config.get('enabled', False):
                print("⚠️ GitLab отключен в конфигурации")
                return
                
            if self.gitlab_url and self.gitlab_token:
                self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.gitlab_token)
                self.gl.auth()
                print("✅ Подключение к GitLab успешно")
            else:
                print("⚠️ GitLab не настроен - отсутствуют данные в конфигурации")
        except Exception as e:
            print(f"❌ Ошибка подключения к GitLab: {e}")
    
    def reconnect(self):
        """Переподключается к GitLab с новой конфигурацией"""
        self._load_config()
        self._connect()
    
    def process_command(self, message: str) -> str:
        """Обрабатывает команды для GitLab (упрощенный метод)"""
        if not self.gl:
            return "❌ GitLab не настроен. Проверьте переменные окружения."
        
        try:
            return self._process_command_legacy(message)
        except Exception as e:
            return f"❌ Ошибка при работе с GitLab: {str(e)}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент GitLab по имени"""
        if not self.gl:
            return {"error": "GitLab не настроен"}
        
        try:
            if tool_name == "list_projects":
                return self._list_projects_tool(arguments)
            elif tool_name == "get_project_commits":
                return self._get_project_commits_tool(arguments)
            elif tool_name == "create_merge_request":
                return self._create_merge_request_tool(arguments)
            elif tool_name == "get_project_branches":
                return self._get_project_branches_tool(arguments)
            elif tool_name == "search_commits_by_task":
                return self._search_commits_by_task_tool(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _process_command_legacy(self, message: str) -> str:
        """Обрабатывает команды для GitLab (старый метод)"""
        if not self.gl:
            return "❌ GitLab не настроен. Проверьте переменные окружения."
        
        message_lower = message.lower()
        
        try:
            if any(word in message_lower for word in ['создать', 'новая', 'создай', 'проект']):
                return self._create_project(message)
            elif any(word in message_lower for word in ['найти', 'поиск', 'найди', 'репозиторий']):
                return self._search_projects(message)
            elif any(word in message_lower for word in ['список', 'все', 'показать', 'проекты']):
                return self._list_projects()
            elif any(word in message_lower for word in ['коммит', 'commit', 'изменения']):
                return self._get_commits(message)
            elif any(word in message_lower for word in ['ветка', 'branch', 'ветки']):
                return self._get_branches(message)
            elif any(word in message_lower for word in ['merge', 'мерж', 'слить']):
                return self._create_merge_request(message)
            else:
                return self._get_help()
        except Exception as e:
            return f"❌ Ошибка при работе с GitLab: {str(e)}"
    
    def process_command_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Обрабатывает команды для GitLab на основе анализа намерений"""
        if not self.gl:
            return "❌ GitLab не настроен. Проверьте переменные окружения."
        
        try:
            from intent_analyzer import IntentType
            
            # Обрабатываем на основе намерения
            if intent_result.intent == IntentType.GITLAB_PROJECTS:
                return self._list_projects_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.GITLAB_COMMITS:
                return self._get_commits_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.GITLAB_MY_COMMITS:
                return self._get_my_commits_intelligent(message, intent_result, user_context)
            elif intent_result.intent == IntentType.GITLAB_TASK_COMMITS:
                return self._get_task_commits_intelligent(message, intent_result, user_context)
            elif intent_result.intent == IntentType.GITLAB_MERGE:
                return self._create_merge_request_intelligent(message, intent_result)
            else:
                # Fallback к старому методу
                return self.process_command(message)
        except Exception as e:
            return f"❌ Ошибка при работе с GitLab: {str(e)}"
    
    def _create_project(self, message: str) -> str:
        """Создает новый проект в GitLab"""
        try:
            # Извлекаем название проекта из сообщения
            project_name = "new-project"
            if 'название' in message.lower():
                parts = message.split('название')
                if len(parts) > 1:
                    project_name = parts[1].strip().strip('"').strip("'")
            elif 'проект' in message.lower():
                parts = message.split('проект')
                if len(parts) > 1:
                    project_name = parts[1].strip().strip('"').strip("'")
            
            project_data = {
                'name': project_name,
                'description': f'Проект создан из чат-бота: {message}',
                'visibility': 'private'
            }
            
            project = self.gl.projects.create(project_data)
            return f"✅ Создан проект: {project.name}\n🔗 URL: {project.web_url}"
        except Exception as e:
            return f"❌ Ошибка создания проекта: {str(e)}"
    
    def _search_projects(self, message: str) -> str:
        """Поиск проектов в GitLab"""
        try:
            projects = self.gl.projects.list(search=message, per_page=5)
            
            if not projects:
                return "🔍 Проекты не найдены"
            
            result = "🔍 Найденные проекты:\n"
            for project in projects:
                result += f"• {project.name}\n  📝 {project.description or 'Без описания'}\n  🔗 {project.web_url}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"
    
    def _list_projects(self) -> str:
        """Список последних проектов"""
        try:
            projects = self.gl.projects.list(per_page=10, order_by='last_activity_at')
            
            if not projects:
                return "📋 Проектов не найдено"
            
            result = "📋 Последние проекты:\n"
            for project in projects:
                result += f"• {project.name}\n  📝 {project.description or 'Без описания'}\n  🔗 {project.web_url}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    def _get_commits(self, message: str) -> str:
        """Получает коммиты проекта"""
        try:
            # Извлекаем название проекта из сообщения
            project_name = None
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ['проект', 'репозиторий'] and i + 1 < len(words):
                    project_name = words[i + 1]
                    break
            
            if not project_name:
                return "❌ Не указано название проекта"
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return f"❌ Проект '{project_name}' не найден"
            
            project = projects[0]
            commits = project.commits.list(per_page=5)
            
            if not commits:
                return f"📝 В проекте {project.name} нет коммитов"
            
            result = f"📝 Последние коммиты в проекте {project.name}:\n"
            for commit in commits:
                result += f"• {commit.short_id}: {commit.title}\n  👤 {commit.author_name}\n  📅 {commit.created_at}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения коммитов: {str(e)}"
    
    def _get_branches(self, message: str) -> str:
        """Получает ветки проекта"""
        try:
            # Извлекаем название проекта из сообщения
            project_name = None
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ['проект', 'репозиторий'] and i + 1 < len(words):
                    project_name = words[i + 1]
                    break
            
            if not project_name:
                return "❌ Не указано название проекта"
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return f"❌ Проект '{project_name}' не найден"
            
            project = projects[0]
            branches = project.branches.list(per_page=10)
            
            if not branches:
                return f"🌿 В проекте {project.name} нет веток"
            
            result = f"🌿 Ветки в проекте {project.name}:\n"
            for branch in branches:
                result += f"• {branch.name}\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения веток: {str(e)}"
    
    def _create_merge_request(self, message: str) -> str:
        """Создает merge request"""
        try:
            # Простое извлечение данных из сообщения
            project_name = "test-project"  # Замените на ваш проект
            source_branch = "feature-branch"
            target_branch = "main"
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return f"❌ Проект '{project_name}' не найден"
            
            project = projects[0]
            
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': 'Merge Request из чат-бота',
                'description': f'Создан из чат-бота: {message}'
            }
            
            mr = project.mergerequests.create(mr_data)
            return f"✅ Создан Merge Request: {mr.title}\n🔗 URL: {mr.web_url}"
        except Exception as e:
            return f"❌ Ошибка создания Merge Request: {str(e)}"
    
    def _get_help(self) -> str:
        """Справка по командам GitLab"""
        return """
🔧 Команды для работы с GitLab:

• Создать проект: "создай проект в gitlab"
• Найти проекты: "найди проекты по ключевому слову"
• Список проектов: "покажи все проекты"
• Коммиты проекта: "покажи коммиты проекта название"
• Мои коммиты: "мои коммиты проекта название"
• Коммиты по задаче: "коммиты по задаче #PROJ-123"
• Ветки проекта: "покажи ветки проекта название"
• Создать MR: "создай merge request"

Примеры:
- "создай проект с названием 'мой-новый-проект'"
- "найди все проекты связанные с API"
- "покажи коммиты проекта my-project"
- "мои коммиты проекта my-project"
- "коммиты по задаче #PROJ-123"
- "покажи ветки проекта my-project"
        """
    
    def _list_projects_intelligent(self, message: str, intent_result) -> str:
        """Список проектов GitLab на основе анализа намерений"""
        try:
            entities = intent_result.entities
            search_query = entities.get('search_query', '')
            
            # Определяем количество проектов из сообщения
            import re
            count_match = re.search(r'(\d+)', message)
            per_page = int(count_match.group(1)) if count_match else 10
            
            if search_query:
                # Поиск проектов по запросу
                projects = self.gl.projects.list(search=search_query, per_page=per_page)
                if not projects:
                    return f"🔍 Проекты по запросу '{search_query}' не найдены"
                
                result = f"🔍 Найденные проекты по запросу '{search_query}':\n\n"
            else:
                # Список последних проектов
                projects = self.gl.projects.list(per_page=per_page, order_by='last_activity_at')
                if not projects:
                    return "📋 Проектов не найдено"
                
                result = f"📋 Последние {len(projects)} проектов:\n\n"
            
            for project in projects:
                result += f"• **{project.name}**\n"
                result += f"  📝 {project.description or 'Без описания'}\n"
                result += f"  🔗 {project.web_url}\n"
                result += f"  📅 Последняя активность: {project.last_activity_at[:10]}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения проектов: {str(e)}"
    
    def _get_commits_intelligent(self, message: str, intent_result) -> str:
        """Получает коммиты проекта на основе анализа намерений"""
        try:
            entities = intent_result.entities
            project_name = entities.get('project_name', '')
            
            # Если не указан проект, пытаемся найти в сообщении
            if not project_name:
                import re
                # Ищем название проекта в сообщении
                words = message.split()
                for i, word in enumerate(words):
                    if word.lower() in ['проект', 'репозиторий', 'repo'] and i + 1 < len(words):
                        project_name = words[i + 1]
                        break
            
            if not project_name:
                return "❌ Не указано название проекта. Пример: 'покажи коммиты проекта my-project'"
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return f"❌ Проект '{project_name}' не найден"
            
            project = projects[0]
            
            # Определяем количество коммитов
            import re
            count_match = re.search(r'(\d+)', message)
            per_page = int(count_match.group(1)) if count_match else 5
            
            commits = project.commits.list(per_page=per_page)
            
            if not commits:
                return f"📝 В проекте {project.name} нет коммитов"
            
            result = f"📝 Последние {len(commits)} коммитов в проекте **{project.name}**:\n\n"
            for commit in commits:
                result += f"• **{commit.short_id}**: {commit.title}\n"
                result += f"  👤 Автор: {commit.author_name}\n"
                result += f"  📅 Дата: {commit.created_at[:10]}\n"
                result += f"  🔗 [Посмотреть коммит]({project.web_url}/-/commit/{commit.id})\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения коммитов: {str(e)}"
    
    def _create_merge_request_intelligent(self, message: str, intent_result) -> str:
        """Создает merge request на основе анализа намерений"""
        try:
            entities = intent_result.entities
            project_name = entities.get('project_name', '')
            
            # Если не указан проект, используем первый доступный
            if not project_name:
                projects = self.gl.projects.list(per_page=1)
                if not projects:
                    return "❌ Нет доступных проектов для создания Merge Request"
                project = projects[0]
            else:
                projects = self.gl.projects.list(search=project_name)
                if not projects:
                    return f"❌ Проект '{project_name}' не найден"
                project = projects[0]
            
            # Извлекаем информацию о ветках из сообщения
            import re
            source_branch = "feature-branch"
            target_branch = "main"
            
            # Ищем упоминания веток в сообщении
            branch_match = re.search(r'из\s+ветки\s+(\w+)', message, re.IGNORECASE)
            if branch_match:
                source_branch = branch_match.group(1)
            
            branch_match = re.search(r'в\s+ветку\s+(\w+)', message, re.IGNORECASE)
            if branch_match:
                target_branch = branch_match.group(1)
            
            # Создаем описание на основе сообщения
            description = f"Merge Request создан из чат-бота\n\nИсходное сообщение: {message}"
            
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': f'MR из чат-бота: {message[:50]}...',
                'description': description
            }
            
            mr = project.mergerequests.create(mr_data)
            return f"✅ Создан Merge Request: **{mr.title}**\n\n🔗 [Открыть MR]({mr.web_url})\n📋 Проект: {project.name}\n🌿 Из ветки: {source_branch} → {target_branch}"
        except Exception as e:
            return f"❌ Ошибка создания Merge Request: {str(e)}"
    
    def _get_my_commits_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Получает мои коммиты в проекте на основе анализа намерений"""
        try:
            entities = intent_result.entities
            project_name = entities.get('my_project_name', '')
            
            # Если не указан проект, пытаемся найти в сообщении
            if not project_name:
                import re
                # Ищем название проекта в сообщении
                words = message.split()
                for i, word in enumerate(words):
                    if word.lower() in ['проект', 'репозиторий', 'repo'] and i + 1 < len(words):
                        project_name = words[i + 1]
                        break
            
            if not project_name:
                return "❌ Не указано название проекта. Пример: 'мои коммиты проекта my-project'"
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return f"❌ Проект '{project_name}' не найден"
            
            project = projects[0]
            
            # Получаем email пользователя из контекста приложения
            user_email = None
            if user_context and isinstance(user_context, dict):
                user_info = user_context.get('user', {})
                user_email = user_info.get('email')
            
            # Если не нашли email в контексте, пытаемся получить из GitLab
            if not user_email:
                try:
                    current_user = self.gl.user
                    if current_user and hasattr(current_user, 'email'):
                        user_email = current_user.email
                except:
                    pass
            
            if not user_email:
                return "❌ Не удалось определить email пользователя для поиска коммитов"
            
            # Определяем количество коммитов
            import re
            count_match = re.search(r'(\d+)', message)
            per_page = int(count_match.group(1)) if count_match else 10
            
            # Получаем коммиты пользователя по email
            # Фильтр по author_email не работает в некоторых версиях python-gitlab/GitLab API.
            # Поэтому фильтруем вручную по email после получения коммитов.
            commits = project.commits.list(
                per_page=100,  # Получаем больше, чтобы потом отфильтровать
                order_by='created_at',
                sort='desc'
            )
            # Фильтруем коммиты по email автора
            filtered_commits = []
            for commit in commits:
                # Иногда author_email может отсутствовать, поэтому используем get
                if hasattr(commit, 'author_email') and commit.author_email == user_email:
                    filtered_commits.append(commit)
                # Если набрали нужное количество, останавливаемся
                if len(filtered_commits) >= per_page:
                    break
            commits = filtered_commits
            
            if not commits:
                return f"📝 В проекте {project.name} нет коммитов пользователя {user_email}"
            
            result = f"👤 Коммиты пользователя {user_email} в проекте **{project.name}**:\n\n"
            for commit in commits:
                result += f"• **{commit.short_id}**: {commit.title}\n"
                result += f"  📅 Дата: {commit.created_at[:10]}\n"
                result += f"  🔗 [Посмотреть коммит]({project.web_url}/-/commit/{commit.id})\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения коммитов пользователя: {str(e)}"
    
    def _get_task_commits_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Получает коммиты по задаче на основе анализа намерений"""
        try:
            entities = intent_result.entities
            task_key = entities.get('task_key', '') or entities.get('task_number', '')
            
            # Если не указан номер задачи, пытаемся найти в сообщении
            if not task_key:
                import re
                # Ищем номер задачи в сообщении
                task_match = re.search(r'#?([A-Z]+-\d+)', message)
                if task_match:
                    task_key = task_match.group(1)
                else:
                    return "❌ Не указан номер задачи. Пример: 'коммиты по задаче #PROJ-123'"
            
            # Определяем количество коммитов
            import re
            count_match = re.search(r'(\d+)', message)
            per_page = int(count_match.group(1)) if count_match else 20
            
            # Ищем коммиты по всем проектам, которые содержат номер задачи в сообщении
            all_commits = []
            
            # Получаем все проекты пользователя
            projects = self.gl.projects.list(per_page=100, membership=True)
            
            for project in projects:
                try:
                    # Ищем коммиты, содержащие номер задачи в сообщении
                    commits = project.commits.list(
                        per_page=per_page,
                        search=task_key,
                        order_by='created_at',
                        sort='desc'
                    )
                    
                    for commit in commits:
                        # Проверяем, что коммит действительно содержит номер задачи в начале сообщения
                        if commit.title.startswith(task_key) or f" {task_key}" in commit.title:
                            all_commits.append({
                                'commit': commit,
                                'project': project
                            })
                except Exception as e:
                    # Пропускаем проекты с ошибками доступа
                    continue
            
            if not all_commits:
                return f"📝 Коммиты по задаче {task_key} не найдены"
            
            # Сортируем по дате создания
            all_commits.sort(key=lambda x: x['commit'].created_at, reverse=True)
            
            # Ограничиваем количество результатов
            all_commits = all_commits[:per_page]
            
            result = f"🎯 Коммиты по задаче **{task_key}**:\n\n"
            for item in all_commits:
                commit = item['commit']
                project = item['project']
                
                result += f"• **{commit.short_id}**: {commit.title}\n"
                result += f"  📁 Проект: {project.name}\n"
                result += f"  👤 Автор: {commit.author_name}\n"
                result += f"  📅 Дата: {commit.created_at[:10]}\n"
                result += f"  🔗 [Посмотреть коммит]({project.web_url}/-/commit/{commit.id})\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска коммитов по задаче: {str(e)}"
    
    def _list_projects_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает список проектов через инструмент"""
        try:
            search = arguments.get('search', '')
            per_page = arguments.get('per_page', 10)
            
            if search:
                projects = self.gl.projects.list(search=search, per_page=per_page)
            else:
                projects = self.gl.projects.list(per_page=per_page, order_by='last_activity_at')
            
            result = []
            for project in projects:
                result.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description or 'Без описания',
                    'web_url': project.web_url,
                    'last_activity_at': project.last_activity_at,
                    'visibility': project.visibility
                })
            
            return {'projects': result}
        except Exception as e:
            return {'error': str(e)}
    
    def _get_project_commits_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает коммиты проекта через инструмент"""
        try:
            project_name = arguments.get('project_name')
            per_page = arguments.get('per_page', 5)
            author_email = arguments.get('author_email')
            
            if not project_name:
                return {'error': 'Не указано название проекта'}
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return {'error': f'Проект "{project_name}" не найден'}
            
            project = projects[0]
            
            # Получаем коммиты
            commits = project.commits.list(per_page=per_page)
            
            result = []
            for commit in commits:
                # Фильтруем по email автора если указан
                if author_email and hasattr(commit, 'author_email') and commit.author_email != author_email:
                    continue
                
                result.append({
                    'id': commit.id,
                    'short_id': commit.short_id,
                    'title': commit.title,
                    'message': commit.message,
                    'author_name': commit.author_name,
                    'author_email': getattr(commit, 'author_email', ''),
                    'created_at': commit.created_at,
                    'web_url': f"{project.web_url}/-/commit/{commit.id}"
                })
            
            return {'commits': result, 'project_name': project.name}
        except Exception as e:
            return {'error': str(e)}
    
    def _create_merge_request_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Создает merge request через инструмент"""
        try:
            project_name = arguments.get('project_name')
            source_branch = arguments.get('source_branch')
            target_branch = arguments.get('target_branch')
            title = arguments.get('title')
            description = arguments.get('description', '')
            
            if not all([project_name, source_branch, target_branch, title]):
                return {'error': 'Не указаны обязательные параметры: project_name, source_branch, target_branch, title'}
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return {'error': f'Проект "{project_name}" не найден'}
            
            project = projects[0]
            
            # Создаем MR
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description
            }
            
            mr = project.mergerequests.create(mr_data)
            
            return {
                'success': True,
                'id': mr.id,
                'iid': mr.iid,
                'title': mr.title,
                'web_url': mr.web_url,
                'source_branch': mr.source_branch,
                'target_branch': mr.target_branch
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_project_branches_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает ветки проекта через инструмент"""
        try:
            project_name = arguments.get('project_name')
            
            if not project_name:
                return {'error': 'Не указано название проекта'}
            
            # Находим проект
            projects = self.gl.projects.list(search=project_name)
            if not projects:
                return {'error': f'Проект "{project_name}" не найден'}
            
            project = projects[0]
            
            # Получаем ветки
            branches = project.branches.list()
            
            result = []
            for branch in branches:
                result.append({
                    'name': branch.name,
                    'default': branch.default,
                    'protected': branch.protected,
                    'web_url': f"{project.web_url}/-/tree/{branch.name}"
                })
            
            return {'branches': result, 'project_name': project.name}
        except Exception as e:
            return {'error': str(e)}
    
    def _search_commits_by_task_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ищет коммиты по номеру задачи через инструмент"""
        try:
            task_key = arguments.get('task_key')
            per_page = arguments.get('per_page', 20)
            
            if not task_key:
                return {'error': 'Не указан номер задачи'}
            
            # Ищем коммиты по всем проектам, которые содержат номер задачи
            all_commits = []
            
            # Получаем все проекты пользователя
            projects = self.gl.projects.list(per_page=100, membership=True)
            
            for project in projects:
                try:
                    # Ищем коммиты, содержащие номер задачи в сообщении
                    commits = project.commits.list(
                        per_page=per_page,
                        search=task_key,
                        order_by='created_at',
                        sort='desc'
                    )
                    
                    for commit in commits:
                        # Проверяем, что коммит действительно содержит номер задачи
                        if commit.title.startswith(task_key) or f" {task_key}" in commit.title:
                            all_commits.append({
                                'id': commit.id,
                                'short_id': commit.short_id,
                                'title': commit.title,
                                'message': commit.message,
                                'author_name': commit.author_name,
                                'author_email': getattr(commit, 'author_email', ''),
                                'created_at': commit.created_at,
                                'project_name': project.name,
                                'web_url': f"{project.web_url}/-/commit/{commit.id}"
                            })
                except Exception:
                    # Пропускаем проекты с ошибками доступа
                    continue
            
            # Сортируем по дате создания
            all_commits.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Ограничиваем количество результатов
            all_commits = all_commits[:per_page]
            
            return {'commits': all_commits, 'task_key': task_key}
        except Exception as e:
            return {'error': str(e)}

    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов GitLab"""
        return [
            {
                "name": "list_projects",
                "description": "Получает список проектов GitLab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search": {"type": "string", "description": "Поисковый запрос"},
                        "per_page": {"type": "integer", "description": "Количество результатов на странице"}
                    }
                }
            },
            {
                "name": "get_project_commits",
                "description": "Получает коммиты проекта",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Название проекта"},
                        "per_page": {"type": "integer", "description": "Количество коммитов"},
                        "author_email": {"type": "string", "description": "Email автора для фильтрации"}
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "create_merge_request",
                "description": "Создает merge request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Название проекта"},
                        "source_branch": {"type": "string", "description": "Исходная ветка"},
                        "target_branch": {"type": "string", "description": "Целевая ветка"},
                        "title": {"type": "string", "description": "Заголовок MR"},
                        "description": {"type": "string", "description": "Описание MR"}
                    },
                    "required": ["project_name", "source_branch", "target_branch", "title"]
                }
            },
            {
                "name": "get_project_branches",
                "description": "Получает ветки проекта",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Название проекта"}
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "search_commits_by_task",
                "description": "Ищет коммиты по номеру задачи",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_key": {"type": "string", "description": "Номер задачи (например, PROJ-123)"},
                        "per_page": {"type": "integer", "description": "Количество результатов"}
                    },
                    "required": ["task_key"]
                }
            }
        ]

    def check_health(self) -> Dict[str, Any]:
        """Проверка состояния подключения к GitLab"""
        try:
            if self.gl:
                # Проверяем подключение
                self.gl.user
                return {'status': 'connected', 'url': self.gitlab_url}
            else:
                return {'status': 'not_configured', 'url': None}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'url': self.gitlab_url}
