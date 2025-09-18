import ldap3
from typing import Dict, Any, List
from config.config_manager import ConfigManager

class LDAPMCPServer:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.ldap_url = None
        self.ldap_user = None
        self.ldap_password = None
        self.base_dn = None
        self.connection = None
        self._load_config()
        self._connect()
    
    def _load_config(self):
        """Загружает конфигурацию LDAP"""
        ad_config = self.config_manager.get_service_config('active_directory')
        self.ldap_url = ad_config.get('server', '')
        self.ldap_user = ad_config.get('service_user', '')
        self.ldap_password = ad_config.get('service_password', '')
        self.base_dn = ad_config.get('base_dn', '')
    
    def _connect(self):
        """Подключение к LDAP"""
        try:
            ad_config = self.config_manager.get_service_config('active_directory')
            if not ad_config.get('enabled', False):
                print("⚠️ Active Directory отключен в конфигурации")
                return
                
            if self.ldap_url and self.ldap_user and self.ldap_password:
                # Создаем подключение к LDAP
                server = ldap3.Server(self.ldap_url)
                self.connection = ldap3.Connection(
                    server, 
                    user=self.ldap_user, 
                    password=self.ldap_password,
                    auto_bind=True
                )
                print("✅ Подключение к LDAP успешно")
            else:
                print("⚠️ LDAP не настроен - отсутствуют данные в конфигурации")
        except Exception as e:
            print(f"❌ Ошибка подключения к LDAP: {e}")
    
    def reconnect(self):
        """Переподключается к LDAP с новой конфигурацией"""
        self._load_config()
        self._connect()
    
    def process_command(self, message: str) -> str:
        """Обрабатывает команды для LDAP (упрощенный метод)"""
        if not self.connection:
            return "❌ LDAP не настроен. Проверьте конфигурацию Active Directory."
        
        try:
            return self._process_command_legacy(message)
        except Exception as e:
            return f"❌ Ошибка при работе с LDAP: {str(e)}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент LDAP по имени"""
        if not self.connection:
            return {"error": "LDAP не настроен"}
        
        try:
            if tool_name == "search_user":
                return self._search_user_tool(arguments)
            elif tool_name == "list_users":
                return self._list_users_tool(arguments)
            elif tool_name == "get_user_details":
                return self._get_user_details_tool(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _process_command_legacy(self, message: str) -> str:
        """Обрабатывает команды для LDAP (старый метод)"""
        if not self.connection:
            return "❌ LDAP не настроен. Проверьте конфигурацию Active Directory."
        
        message_lower = message.lower()
        
        try:
            if any(word in message_lower for word in ['найти', 'поиск', 'найди', 'пользователь', 'сотрудник']):
                return self._search_users(message)
            elif any(word in message_lower for word in ['список', 'все', 'показать', 'пользователи']):
                return self._list_users()
            else:
                return self._get_help()
        except Exception as e:
            return f"❌ Ошибка при работе с LDAP: {str(e)}"
    
    def process_command_intelligent(self, message: str, intent_result, user_context: dict = None) -> str:
        """Обрабатывает команды для LDAP на основе анализа намерений"""
        if not self.connection:
            return "❌ LDAP не настроен. Проверьте конфигурацию Active Directory."
        
        try:
            from intent_analyzer import IntentType
            
            # Обрабатываем на основе намерения
            if intent_result.intent == IntentType.LDAP_SEARCH:
                return self._search_users_intelligent(message, intent_result)
            elif intent_result.intent == IntentType.LDAP_LIST:
                return self._list_users_intelligent(message, intent_result)
            else:
                # Fallback к старому методу
                return self.process_command(message)
        except Exception as e:
            return f"❌ Ошибка при работе с LDAP: {str(e)}"
    
    def _search_users(self, message: str) -> str:
        """Поиск пользователей в LDAP"""
        try:
            # Извлекаем поисковый запрос из сообщения
            search_query = message.strip()
            
            # Убираем служебные слова
            words_to_remove = ['найти', 'поиск', 'найди', 'пользователь', 'сотрудник', 'в', 'ldap', 'ad']
            for word in words_to_remove:
                search_query = search_query.replace(word, '')
            
            search_query = search_query.strip()
            
            if not search_query:
                return "❌ Не указан поисковый запрос. Пример: 'найди пользователя Иванов'"
            
            # Выполняем поиск
            users = self._perform_ldap_search(search_query)
            
            if not users:
                return f"🔍 Пользователи по запросу '{search_query}' не найдены"
            
            result = f"🔍 Найденные пользователи по запросу '{search_query}':\n\n"
            for user in users:
                result += f"• **{user['display_name']}**\n"
                result += f"  👤 Логин: {user['username']}\n"
                result += f"  📧 Email: {user['email']}\n"
                result += f"  🏢 Отдел: {user['department']}\n"
                result += f"  📞 Телефон: {user['phone']}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска пользователей: {str(e)}"
    
    def _list_users(self) -> str:
        """Список пользователей из LDAP"""
        try:
            # Получаем список пользователей
            users = self._perform_ldap_search("", limit=20)
            
            if not users:
                return "📋 Пользователи не найдены"
            
            result = f"📋 Список пользователей ({len(users)} из 20):\n\n"
            for user in users:
                result += f"• **{user['display_name']}**\n"
                result += f"  👤 Логин: {user['username']}\n"
                result += f"  📧 Email: {user['email']}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка пользователей: {str(e)}"
    
    def _perform_ldap_search(self, search_query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Выполняет поиск пользователей в LDAP"""
        try:
            # Формируем фильтр поиска
            if search_query:
                # Поиск по различным полям
                search_filter = f"(&(objectClass=person)(|(cn=*{search_query}*)(sn=*{search_query}*)(givenName=*{search_query}*)(sAMAccountName=*{search_query}*)(mail=*{search_query}*)))"
            else:
                # Получить всех пользователей
                search_filter = "(objectClass=person)"
            
            # Атрибуты для получения
            attributes = [
                'cn', 'sAMAccountName', 'mail', 'displayName', 
                'givenName', 'sn', 'department', 'telephoneNumber',
                'title', 'company', 'manager'
            ]
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            users = []
            for entry in self.connection.entries:
                user_data = {
                    'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else '',
                    'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.cn),
                    'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                    'first_name': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                    'last_name': str(entry.sn) if hasattr(entry, 'sn') else '',
                    'department': str(entry.department) if hasattr(entry, 'department') else '',
                    'phone': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else '',
                    'title': str(entry.title) if hasattr(entry, 'title') else '',
                    'company': str(entry.company) if hasattr(entry, 'company') else '',
                    'manager': str(entry.manager) if hasattr(entry, 'manager') else ''
                }
                users.append(user_data)
            
            return users
        except Exception as e:
            print(f"❌ Ошибка выполнения LDAP поиска: {e}")
            return []
    
    def _search_users_intelligent(self, message: str, intent_result) -> str:
        """Поиск пользователей на основе анализа намерений"""
        try:
            entities = intent_result.entities
            search_query = entities.get('ldap_search_query', '')
            
            # Если не указан запрос, пытаемся найти в сообщении
            if not search_query:
                # Ищем ФИО, фамилию или имя в сообщении
                import re
                # Убираем служебные слова и извлекаем поисковый запрос
                words_to_remove = ['найти', 'поиск', 'найди', 'пользователь', 'сотрудник', 'в', 'ldap', 'ad', 'по', 'фамилии', 'имени']
                clean_message = message
                for word in words_to_remove:
                    clean_message = clean_message.replace(word, '')
                
                search_query = clean_message.strip()
            
            if not search_query:
                return "❌ Не указан поисковый запрос. Пример: 'найди пользователя Иванов' или 'поиск по фамилии Петров'"
            
            # Определяем количество результатов
            import re
            count_match = re.search(r'(\d+)', message)
            limit = int(count_match.group(1)) if count_match else 10
            
            # Выполняем поиск
            users = self._perform_ldap_search(search_query, limit)
            
            if not users:
                return f"🔍 Пользователи по запросу '{search_query}' не найдены"
            
            result = f"🔍 Найденные пользователи по запросу '{search_query}' ({len(users)} из {limit}):\n\n"
            for user in users:
                result += f"• **{user['display_name']}**\n"
                result += f"  👤 Логин: {user['username']}\n"
                result += f"  📧 Email: {user['email']}\n"
                if user['department']:
                    result += f"  🏢 Отдел: {user['department']}\n"
                if user['phone']:
                    result += f"  📞 Телефон: {user['phone']}\n"
                if user['title']:
                    result += f"  💼 Должность: {user['title']}\n"
                result += "\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка поиска пользователей: {str(e)}"
    
    def _list_users_intelligent(self, message: str, intent_result) -> str:
        """Список пользователей на основе анализа намерений"""
        try:
            # Определяем количество пользователей
            import re
            count_match = re.search(r'(\d+)', message)
            limit = int(count_match.group(1)) if count_match else 20
            
            # Получаем список пользователей
            users = self._perform_ldap_search("", limit)
            
            if not users:
                return "📋 Пользователи не найдены"
            
            result = f"📋 Список пользователей ({len(users)} из {limit}):\n\n"
            for user in users:
                result += f"• **{user['display_name']}**\n"
                result += f"  👤 Логин: {user['username']}\n"
                result += f"  📧 Email: {user['email']}\n"
                if user['department']:
                    result += f"  🏢 Отдел: {user['department']}\n"
                result += "\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка пользователей: {str(e)}"
    
    def _get_help(self) -> str:
        """Справка по командам LDAP"""
        return """
🔧 Команды для работы с LDAP/Active Directory:

• Поиск пользователя: "найди пользователя Иванов"
• Поиск по фамилии: "поиск по фамилии Петров"
• Поиск по имени: "найди по имени Иван"
• Список пользователей: "покажи всех пользователей"
• Список с лимитом: "покажи 50 пользователей"

Примеры:
- "найди пользователя Хайрутдинов"
- "поиск по фамилии Иванов"
- "найди по имени Камиль"
- "покажи всех пользователей"
- "покажи 30 пользователей"
        """
    
    def _search_user_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ищет пользователя через инструмент"""
        try:
            limit = arguments.get('limit', 20)
            # Иногда название параметра бывает user или name
            username = arguments.get('username') or arguments.get('user') or arguments.get('name')
            email = arguments.get('email')
            
            if not username and not email:
                return {'error': 'Не указан username или email'}
            
            # Формируем фильтр поиска
            if username:
                search_query = username
            else:
                search_query = email
            
            search_filter = f"(&(objectClass=person)(|(cn=*{search_query}*)(sn=*{search_query}*)(givenName=*{search_query}*)(sAMAccountName=*{search_query}*)(mail=*{search_query}*)))"
            # Атрибуты для получения
            attributes = [
                'cn', 'sAMAccountName', 'mail', 'displayName', 
                'givenName', 'sn', 'department', 'telephoneNumber',
                'title', 'company', 'manager'
            ]
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            users = []
            for entry in self.connection.entries:
                user_data = {
                    'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else '',
                    'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.cn),
                    'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                    'first_name': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                    'last_name': str(entry.sn) if hasattr(entry, 'sn') else '',
                    'department': str(entry.department) if hasattr(entry, 'department') else '',
                    'phone': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else '',
                    'title': str(entry.title) if hasattr(entry, 'title') else '',
                    'company': str(entry.company) if hasattr(entry, 'company') else '',
                    'manager': str(entry.manager) if hasattr(entry, 'manager') else ''
                }
                users.append(user_data)
            
            return {'users': users}
        except Exception as e:
            return {'error': str(e)}
    
    def _list_users_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает список пользователей через инструмент"""
        try:
            limit = arguments.get('limit', 20)
            department = arguments.get('department')
            
            # Формируем фильтр поиска
            if department:
                search_filter = f"(&(objectClass=person)(department=*{department}*))"
            else:
                search_filter = "(objectClass=person)"
            
            # Атрибуты для получения
            attributes = [
                'cn', 'sAMAccountName', 'mail', 'displayName', 
                'givenName', 'sn', 'department', 'telephoneNumber',
                'title', 'company'
            ]
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            users = []
            for entry in self.connection.entries:
                user_data = {
                    'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else '',
                    'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.cn),
                    'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                    'first_name': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                    'last_name': str(entry.sn) if hasattr(entry, 'sn') else '',
                    'department': str(entry.department) if hasattr(entry, 'department') else '',
                    'phone': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else '',
                    'title': str(entry.title) if hasattr(entry, 'title') else '',
                    'company': str(entry.company) if hasattr(entry, 'company') else ''
                }
                users.append(user_data)
            
            return {'users': users, 'department': department}
        except Exception as e:
            return {'error': str(e)}
    
    def _get_user_details_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Получает детальную информацию о пользователе через инструмент"""
        try:
            username = arguments.get('username')
            email = arguments.get('email')
            
            if not username and not email:
                return {'error': 'Не указан username или email'}
            
            # Формируем фильтр поиска
            if username:
                search_filter = f"(&(objectClass=person)(sAMAccountName={username}))"
            else:
                search_filter = f"(&(objectClass=person)(mail={email}))"
            
            # Атрибуты для получения
            attributes = [
                'cn', 'sAMAccountName', 'mail', 'displayName', 
                'givenName', 'sn', 'department', 'telephoneNumber',
                'title', 'company', 'manager', 'userAccountControl',
                'whenCreated', 'whenChanged', 'lastLogon'
            ]
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=1
            )
            
            if not self.connection.entries:
                return {'error': 'Пользователь не найден'}
            
            entry = self.connection.entries[0]
            
            user_data = {
                'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else '',
                'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else str(entry.cn),
                'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                'first_name': str(entry.givenName) if hasattr(entry, 'givenName') else '',
                'last_name': str(entry.sn) if hasattr(entry, 'sn') else '',
                'department': str(entry.department) if hasattr(entry, 'department') else '',
                'phone': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else '',
                'title': str(entry.title) if hasattr(entry, 'title') else '',
                'company': str(entry.company) if hasattr(entry, 'company') else '',
                'manager': str(entry.manager) if hasattr(entry, 'manager') else '',
                'account_control': str(entry.userAccountControl) if hasattr(entry, 'userAccountControl') else '',
                'created': str(entry.whenCreated) if hasattr(entry, 'whenCreated') else '',
                'modified': str(entry.whenChanged) if hasattr(entry, 'whenChanged') else '',
                'last_logon': str(entry.lastLogon) if hasattr(entry, 'lastLogon') else ''
            }
            
            return {'user': user_data}
        except Exception as e:
            return {'error': str(e)}

    def get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных инструментов LDAP"""
        return [
            {
                "name": "search_user",
                "description": "Ищет пользователя в LDAP/AD. Пример запроса: найди пользователя Иванов",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "Имя пользователя"},
                        "email": {"type": "string", "description": "Email пользователя"},
                        "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                    },
                    "required": ["search_query"]
                }
            },
            {
                "name": "list_users",
                "description": "Получает список пользователей",
                "parameters": {
                    "limit": {"type": "integer", "description": "Максимальное количество результатов"},
                    "department": {"type": "string", "description": "Фильтр по отделу"}
                }
            },
            {
                "name": "get_user_details",
                "description": "Получает детальную информацию о пользователе. Пример запроса: дай более детальную информацию о пользователе",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "Имя пользователя"},
                        "email": {"type": "string", "description": "Email пользователя"},
                        "limit": {"type": "integer", "description": "Максимальное количество результатов"}
                    }
                }
            }
        ]

    def check_health(self) -> Dict[str, Any]:
        """Проверка состояния подключения к LDAP"""
        try:
            if self.connection:
                # Проверяем подключение
                self.connection.search(
                    search_base=self.base_dn,
                    search_filter="(objectClass=person)",
                    search_scope=ldap3.SUBTREE,
                    attributes=['cn'],
                    size_limit=1
                )
                return {'status': 'connected', 'url': self.ldap_url}
            else:
                return {'status': 'not_configured', 'url': None}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'url': self.ldap_url}
