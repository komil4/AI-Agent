#!/usr/bin/env python3
"""
MCP сервер для работы с LDAP/Active Directory с использованием стандарта Anthropic
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import ldap3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_mcp_server import BaseMCPServer, create_tool_schema, validate_tool_parameters, format_tool_response

logger = logging.getLogger(__name__)

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class LDAPMCPServer(BaseMCPServer):
    """MCP сервер для работы с LDAP/Active Directory - поиск пользователей, групп и управление корпоративными данными"""
    
    def __init__(self):
        """Инициализация LDAP MCP сервера"""
        # Инициализируем переменные ДО вызова super().__init__()
        self.ldap_url = None
        self.ldap_user = None
        self.ldap_password = None
        self.base_dn = None
        self.domain = None
        self.connection = None
        
        # Теперь вызываем родительский конструктор
        super().__init__("active_directory")
        
        # Настройки для админ-панели
        self.display_name = "LDAP MCP"
        self.icon = "fas fa-users"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'ldap_url', 'label': 'URL сервера LDAP', 'type': 'text', 'placeholder': 'ldap://domain.local:389' },
            { 'key': 'domain', 'label': 'Домен', 'type': 'text', 'placeholder': 'domain.local' },
            { 'key': 'base_dn', 'label': 'Base DN', 'type': 'text', 'placeholder': 'CN=Users,DC=domain,DC=local' },
            { 'key': 'ldap_user', 'label': 'LDAP User', 'type': 'text', 'placeholder': 'service_account' },
            { 'key': 'ldap_password', 'label': 'LDAP Password', 'type': 'password', 'placeholder': 'пароль для service account' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        
        # Определяем инструменты в стандарте Anthropic
        self.tools = [
            create_tool_schema(
                name="search_users",
                description="Ищет пользователей в LDAP/Active Directory по различным критериям",
                parameters={
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос (имя пользователя, email, имя или фамилия)"
                        },
                        "search_base": {
                            "type": "string",
                            "description": "Базовый DN для поиска (по умолчанию используется конфигурационный)"
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата (по умолчанию основные атрибуты)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "search_scope": {
                            "type": "string",
                            "description": "Область поиска",
                            "enum": ["BASE", "LEVEL", "SUBTREE"],
                            "default": "SUBTREE"
                        }
                    },
                    "required": ["query"]
                }
            ),
            create_tool_schema(
                name="get_user_details",
                description="Получает детальную информацию о конкретном пользователе",
                parameters={
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Имя пользователя (sAMAccountName)"
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата"
                        },
                        "include_groups": {
                            "type": "boolean",
                            "description": "Включать информацию о группах пользователя"
                        },
                        "include_permissions": {
                            "type": "boolean",
                            "description": "Включать информацию о правах доступа"
                        }
                    },
                    "required": ["username"]
                }
            ),
            create_tool_schema(
                name="list_users",
                description="Получает список пользователей с возможностью фильтрации и сортировки",
                parameters={
                    "properties": {
                        "search_base": {
                            "type": "string",
                            "description": "Базовый DN для поиска"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата"
                        },
                        "filter_disabled": {
                            "type": "boolean",
                            "description": "Исключать отключенных пользователей"
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Поле для сортировки",
                            "enum": ["cn", "displayName", "sAMAccountName", "mail", "whenCreated"]
                        }
                    }
                }
            ),
            create_tool_schema(
                name="search_groups",
                description="Ищет группы в LDAP/Active Directory по различным критериям",
                parameters={
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос (название группы, описание)"
                        },
                        "search_base": {
                            "type": "string",
                            "description": "Базовый DN для поиска"
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "group_type": {
                            "type": "string",
                            "description": "Тип группы для фильтрации",
                            "enum": ["security", "distribution", "all"]
                        }
                    },
                    "required": ["query"]
                }
            ),
            create_tool_schema(
                name="get_group_details",
                description="Получает детальную информацию о конкретной группе",
                parameters={
                    "properties": {
                        "group_name": {
                            "type": "string",
                            "description": "Название группы (cn или sAMAccountName)"
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата"
                        },
                        "include_members": {
                            "type": "boolean",
                            "description": "Включать список участников группы"
                        },
                        "include_nested_groups": {
                            "type": "boolean",
                            "description": "Включать вложенные группы"
                        }
                    },
                    "required": ["group_name"]
                }
            ),
            create_tool_schema(
                name="list_groups",
                description="Получает список групп с возможностью фильтрации",
                parameters={
                    "properties": {
                        "search_base": {
                            "type": "string",
                            "description": "Базовый DN для поиска"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Максимальное количество результатов (по умолчанию 50)",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список атрибутов для возврата"
                        },
                        "group_type": {
                            "type": "string",
                            "description": "Тип группы для фильтрации",
                            "enum": ["security", "distribution", "all"]
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Поле для сортировки",
                            "enum": ["cn", "name", "description", "whenCreated"]
                        }
                    }
                }
            ),
            create_tool_schema(
                name="get_user_groups",
                description="Получает список групп, в которых состоит пользователь",
                parameters={
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Имя пользователя (sAMAccountName)"
                        },
                        "include_nested": {
                            "type": "boolean",
                            "description": "Включать вложенные группы"
                        },
                        "group_type": {
                            "type": "string",
                            "description": "Тип групп для фильтрации",
                            "enum": ["security", "distribution", "all"]
                        }
                    },
                    "required": ["username"]
                }
            ),
            create_tool_schema(
                name="get_group_members",
                description="Получает список участников группы",
                parameters={
                    "properties": {
                        "group_name": {
                            "type": "string",
                            "description": "Название группы (cn или sAMAccountName)"
                        },
                        "include_nested": {
                            "type": "boolean",
                            "description": "Включать участников вложенных групп"
                        },
                        "member_type": {
                            "type": "string",
                            "description": "Тип участников для фильтрации",
                            "enum": ["users", "groups", "all"]
                        }
                    },
                    "required": ["group_name"]
                }
            ),
            create_tool_schema(
                name="authenticate_user",
                description="Проверяет аутентификацию пользователя в LDAP/AD",
                parameters={
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Имя пользователя для аутентификации"
                        },
                        "password": {
                            "type": "string",
                            "description": "Пароль пользователя"
                        },
                        "return_user_info": {
                            "type": "boolean",
                            "description": "Возвращать информацию о пользователе при успешной аутентификации"
                        }
                    },
                    "required": ["username", "password"]
                }
            ),
            create_tool_schema(
                name="get_ldap_info",
                description="Получает информацию о LDAP сервере и его конфигурации",
                parameters={
                    "properties": {
                        "include_schema": {
                            "type": "boolean",
                            "description": "Включать схему LDAP"
                        },
                        "include_stats": {
                            "type": "boolean",
                            "description": "Включать статистику сервера"
                        }
                    }
                }
            )
        ]
    
    def _get_description(self) -> str:
        """Возвращает описание сервера"""
        return "LDAP/Active Directory MCP сервер - поиск пользователей, групп и управление корпоративными данными в LDAP/AD"
    
    def _load_config(self):
        """Загружает конфигурацию LDAP"""
        ad_config = self.config_manager.get_service_config('active_directory')
        self.ldap_url = ad_config.get('server', '')
        self.ldap_user = ad_config.get('service_user', '')
        self.ldap_password = ad_config.get('service_password', '')
        self.base_dn = ad_config.get('base_dn', '')
        self.domain = ad_config.get('domain', '')
    
    def _connect(self):
        """Подключение к LDAP"""
        try:
            ad_config = self.config_manager.get_service_config('active_directory')
            if not ad_config.get('enabled', False):
                logger.info("ℹ️ Active Directory отключен в конфигурации")
                return
            
            if not all([self.ldap_url, self.ldap_user, self.ldap_password, self.base_dn]):
                logger.warning("⚠️ Неполная конфигурация LDAP")
                return
            
            # Создаем подключение к LDAP
            server = ldap3.Server(self.ldap_url)
            self.connection = ldap3.Connection(
                server,
                user=self.ldap_user,
                password=self.ldap_password,
                auto_bind=True
            )
            
            logger.info(f"✅ Подключение к LDAP успешно: {self.ldap_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к LDAP: {e}")
            self.connection = None
    
    def _test_connection(self) -> bool:
        """Тестирует подключение к LDAP"""
        if not self.connection:
            return False
        
        try:
            self.connection.bind()
            return True
        except Exception:
            return False
    
    # ============================================================================
    # ИНСТРУМЕНТЫ LDAP/ACTIVE DIRECTORY
    # ============================================================================
    
    def search_users(self, query: str, search_base: str = None, attributes: List[str] = None,
                    limit: int = 50, search_scope: str = "SUBTREE") -> Dict[str, Any]:
        """Ищет пользователей в LDAP/Active Directory"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['sAMAccountName', 'displayName', 'mail', 'cn', 'givenName', 'sn', 'userPrincipalName']
            
            # Определяем базовый DN
            base_dn = search_base or self.base_dn
            
            # Создаем фильтр поиска
            search_filter = f"(&(objectClass=user)(objectClass=person)(!(objectClass=computer))(|(sAMAccountName=*{query}*)(displayName=*{query}*)(mail=*{query}*)(cn=*{query}*)))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=getattr(ldap3, search_scope),
                attributes=attributes,
                size_limit=limit
            )
            
            # Форматируем результаты
            users = []
            for entry in self.connection.entries:
                user_data = {}
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr)
                        if isinstance(value, list) and len(value) > 0:
                            user_data[attr] = str(value[0])
                        elif value:
                            user_data[attr] = str(value)
                users.append(user_data)
            
            logger.info(f"✅ Найдено пользователей: {len(users)}")
            return format_tool_response(
                True,
                f"Найдено {len(users)} пользователей",
                {
                    "total": len(users),
                    "users": users,
                    "query": query,
                    "search_base": base_dn
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска пользователей: {e}")
            return format_tool_response(False, f"Ошибка поиска пользователей: {str(e)}")
    
    def get_user_details(self, username: str, attributes: List[str] = None,
                        include_groups: bool = False, include_permissions: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о пользователе"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['sAMAccountName', 'displayName', 'mail', 'cn', 'givenName', 'sn', 
                             'userPrincipalName', 'telephoneNumber', 'department', 'title', 
                             'manager', 'whenCreated', 'whenChanged', 'userAccountControl']
            
            # Создаем фильтр поиска
            search_filter = f"(&(objectClass=user)(objectClass=person)(sAMAccountName={username}))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes
            )
            
            if not self.connection.entries:
                return format_tool_response(False, f"Пользователь {username} не найден")
            
            # Получаем данные пользователя
            user_entry = self.connection.entries[0]
            user_data = {}
            
            for attr in attributes:
                if hasattr(user_entry, attr):
                    value = getattr(user_entry, attr)
                    if isinstance(value, list) and len(value) > 0:
                        user_data[attr] = str(value[0])
                    elif value:
                        user_data[attr] = str(value)
            
            # Группы пользователя
            if include_groups:
                try:
                    groups_result = self.get_user_groups(username, include_nested=True)
                    if groups_result["success"]:
                        user_data["groups"] = groups_result["data"]["groups"]
                except Exception:
                    user_data["groups"] = "Недоступно"
            
            # Права доступа
            if include_permissions:
                try:
                    # Получаем информацию о правах доступа
                    user_data["permissions"] = {
                        "account_disabled": "1" in user_data.get("userAccountControl", ""),
                        "password_expired": "2" in user_data.get("userAccountControl", ""),
                        "account_locked": "16" in user_data.get("userAccountControl", "")
                    }
                except Exception:
                    user_data["permissions"] = "Недоступно"
            
            logger.info(f"✅ Получены детали пользователя: {username}")
            return format_tool_response(True, "Детали пользователя получены", user_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей пользователя: {e}")
            return format_tool_response(False, f"Ошибка получения деталей пользователя: {str(e)}")
    
    def list_users(self, search_base: str = None, limit: int = 50, attributes: List[str] = None,
                  filter_disabled: bool = True, sort_by: str = "displayName") -> Dict[str, Any]:
        """Получает список пользователей"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['sAMAccountName', 'displayName', 'mail', 'cn', 'givenName', 'sn', 'userAccountControl']
            
            # Определяем базовый DN
            base_dn = search_base or self.base_dn
            
            # Создаем фильтр поиска
            search_filter = "(&(objectClass=user)(objectClass=person)(!(objectClass=computer)))"
            if filter_disabled:
                search_filter += "(!(userAccountControl:1.2.840.113556.1.4.803:=2))"  # Исключаем отключенных
            
            # Выполняем поиск
            self.connection.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            # Форматируем результаты
            users = []
            for entry in self.connection.entries:
                user_data = {}
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr)
                        if isinstance(value, list) and len(value) > 0:
                            user_data[attr] = str(value[0])
                        elif value:
                            user_data[attr] = str(value)
                users.append(user_data)
            
            # Сортируем
            if sort_by in ['displayName', 'cn', 'sAMAccountName', 'mail']:
                users.sort(key=lambda x: x.get(sort_by, ''), reverse=False)
            
            logger.info(f"✅ Получен список пользователей: {len(users)}")
            return format_tool_response(True, f"Получен список пользователей: {len(users)}", users)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка пользователей: {e}")
            return format_tool_response(False, f"Ошибка получения списка пользователей: {str(e)}")
    
    def search_groups(self, query: str, search_base: str = None, attributes: List[str] = None,
                     limit: int = 50, group_type: str = "all") -> Dict[str, Any]:
        """Ищет группы в LDAP/Active Directory"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['cn', 'sAMAccountName', 'description', 'groupType', 'memberCount']
            
            # Определяем базовый DN
            base_dn = search_base or self.base_dn
            
            # Создаем фильтр поиска
            search_filter = f"(&(objectClass=group)(|(cn=*{query}*)(sAMAccountName=*{query}*)(description=*{query}*)))"
            
            # Фильтр по типу группы
            if group_type == "security":
                search_filter += "(groupType:1.2.840.113556.1.4.803:=2147483648)"
            elif group_type == "distribution":
                search_filter += "(!(groupType:1.2.840.113556.1.4.803:=2147483648))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            # Форматируем результаты
            groups = []
            for entry in self.connection.entries:
                group_data = {}
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr)
                        if isinstance(value, list) and len(value) > 0:
                            group_data[attr] = str(value[0])
                        elif value:
                            group_data[attr] = str(value)
                groups.append(group_data)
            
            logger.info(f"✅ Найдено групп: {len(groups)}")
            return format_tool_response(
                True,
                f"Найдено {len(groups)} групп",
                {
                    "total": len(groups),
                    "groups": groups,
                    "query": query,
                    "search_base": base_dn
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска групп: {e}")
            return format_tool_response(False, f"Ошибка поиска групп: {str(e)}")
    
    def get_group_details(self, group_name: str, attributes: List[str] = None,
                         include_members: bool = False, include_nested_groups: bool = False) -> Dict[str, Any]:
        """Получает детальную информацию о группе"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['cn', 'sAMAccountName', 'description', 'groupType', 'member', 'memberOf']
            
            # Создаем фильтр поиска
            search_filter = f"(&(objectClass=group)(|(cn={group_name})(sAMAccountName={group_name})))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes
            )
            
            if not self.connection.entries:
                return format_tool_response(False, f"Группа {group_name} не найдена")
            
            # Получаем данные группы
            group_entry = self.connection.entries[0]
            group_data = {}
            
            for attr in attributes:
                if hasattr(group_entry, attr):
                    value = getattr(group_entry, attr)
                    if isinstance(value, list) and len(value) > 0:
                        group_data[attr] = str(value[0])
                    elif value:
                        group_data[attr] = str(value)
            
            # Участники группы
            if include_members:
                try:
                    members_result = self.get_group_members(group_name, include_nested=include_nested_groups)
                    if members_result["success"]:
                        group_data["members"] = members_result["data"]["members"]
                except Exception:
                    group_data["members"] = "Недоступно"
            
            logger.info(f"✅ Получены детали группы: {group_name}")
            return format_tool_response(True, "Детали группы получены", group_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей группы: {e}")
            return format_tool_response(False, f"Ошибка получения деталей группы: {str(e)}")
    
    def list_groups(self, search_base: str = None, limit: int = 50, attributes: List[str] = None,
                   group_type: str = "all", sort_by: str = "cn") -> Dict[str, Any]:
        """Получает список групп"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Определяем атрибуты для поиска
            if not attributes:
                attributes = ['cn', 'sAMAccountName', 'description', 'groupType']
            
            # Определяем базовый DN
            base_dn = search_base or self.base_dn
            
            # Создаем фильтр поиска
            search_filter = "(objectClass=group)"
            
            # Фильтр по типу группы
            if group_type == "security":
                search_filter += "(groupType:1.2.840.113556.1.4.803:=2147483648)"
            elif group_type == "distribution":
                search_filter += "(!(groupType:1.2.840.113556.1.4.803:=2147483648))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
                size_limit=limit
            )
            
            # Форматируем результаты
            groups = []
            for entry in self.connection.entries:
                group_data = {}
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr)
                        if isinstance(value, list) and len(value) > 0:
                            group_data[attr] = str(value[0])
                        elif value:
                            group_data[attr] = str(value)
                groups.append(group_data)
            
            # Сортируем
            if sort_by in ['cn', 'sAMAccountName', 'description']:
                groups.sort(key=lambda x: x.get(sort_by, ''), reverse=False)
            
            logger.info(f"✅ Получен список групп: {len(groups)}")
            return format_tool_response(True, f"Получен список групп: {len(groups)}", groups)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка групп: {e}")
            return format_tool_response(False, f"Ошибка получения списка групп: {str(e)}")
    
    def get_user_groups(self, username: str, include_nested: bool = False,
                       group_type: str = "all") -> Dict[str, Any]:
        """Получает список групп пользователя"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Создаем фильтр поиска
            search_filter = f"(&(objectClass=group)(member:1.2.840.113556.1.4.1941:={self.base_dn}))"
            
            # Выполняем поиск
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=['cn', 'sAMAccountName', 'description', 'groupType']
            )
            
            # Форматируем результаты
            groups = []
            for entry in self.connection.entries:
                group_data = {
                    "cn": str(entry.cn),
                    "sAMAccountName": str(entry.sAMAccountName),
                    "description": str(entry.description) if hasattr(entry, 'description') else "",
                    "groupType": str(entry.groupType) if hasattr(entry, 'groupType') else ""
                }
                groups.append(group_data)
            
            logger.info(f"✅ Получены группы пользователя: {len(groups)}")
            return format_tool_response(True, f"Получены группы пользователя: {len(groups)}", {"groups": groups})
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения групп пользователя: {e}")
            return format_tool_response(False, f"Ошибка получения групп пользователя: {str(e)}")
    
    def get_group_members(self, group_name: str, include_nested: bool = False,
                         member_type: str = "all") -> Dict[str, Any]:
        """Получает список участников группы"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Создаем фильтр поиска для группы
            search_filter = f"(&(objectClass=group)(|(cn={group_name})(sAMAccountName={group_name})))"
            
            # Выполняем поиск группы
            self.connection.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=['member']
            )
            
            if not self.connection.entries:
                return format_tool_response(False, f"Группа {group_name} не найдена")
            
            # Получаем участников
            members = []
            group_entry = self.connection.entries[0]
            
            if hasattr(group_entry, 'member'):
                for member_dn in group_entry.member:
                    # Получаем информацию об участнике
                    member_filter = f"(distinguishedName={member_dn})"
                    self.connection.search(
                        search_base=self.base_dn,
                        search_filter=member_filter,
                        search_scope=ldap3.SUBTREE,
                        attributes=['cn', 'sAMAccountName', 'objectClass']
                    )
                    
                    if self.connection.entries:
                        member_entry = self.connection.entries[0]
                        member_data = {
                            "dn": str(member_dn),
                            "cn": str(member_entry.cn),
                            "sAMAccountName": str(member_entry.sAMAccountName) if hasattr(member_entry, 'sAMAccountName') else "",
                            "type": "group" if "group" in str(member_entry.objectClass).lower() else "user"
                        }
                        members.append(member_data)
            
            logger.info(f"✅ Получены участники группы: {len(members)}")
            return format_tool_response(True, f"Получены участники группы: {len(members)}", {"members": members})
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения участников группы: {e}")
            return format_tool_response(False, f"Ошибка получения участников группы: {str(e)}")
    
    def authenticate_user(self, username: str, password: str, return_user_info: bool = False) -> Dict[str, Any]:
        """Проверяет аутентификацию пользователя"""
        try:
            if not self.ldap_url or not self.domain:
                return format_tool_response(False, "LDAP не настроен для аутентификации")
            
            # Создаем временное подключение для аутентификации
            server = ldap3.Server(self.ldap_url)
            auth_connection = ldap3.Connection(
                server,
                user=f"{self.domain}\\{username}",
                password=password,
                auto_bind=True
            )
            
            # Если дошли до сюда, аутентификация успешна
            auth_connection.unbind()
            
            result_data = {"authenticated": True}
            
            # Получаем информацию о пользователе, если запрошено
            if return_user_info:
                user_info = self.get_user_details(username)
                if user_info["success"]:
                    result_data["user_info"] = user_info["data"]
            
            logger.info(f"✅ Аутентификация пользователя успешна: {username}")
            return format_tool_response(True, f"Пользователь {username} аутентифицирован", result_data)
            
        except Exception as e:
            logger.warning(f"❌ Ошибка аутентификации пользователя {username}: {e}")
            return format_tool_response(False, f"Ошибка аутентификации: {str(e)}")
    
    def get_ldap_info(self, include_schema: bool = False, include_stats: bool = False) -> Dict[str, Any]:
        """Получает информацию о LDAP сервере"""
        try:
            if not self.connection:
                return format_tool_response(False, "LDAP не подключен")
            
            # Базовая информация
            ldap_info = {
                "server_url": self.ldap_url,
                "base_dn": self.base_dn,
                "domain": self.domain,
                "connected": True,
                "server_info": {
                    "vendor": "Microsoft Active Directory",
                    "version": "Unknown"
                }
            }
            
            # Схема LDAP
            if include_schema:
                try:
                    # Получаем информацию о схеме
                    ldap_info["schema"] = "Схема LDAP доступна"
                except Exception:
                    ldap_info["schema"] = "Недоступно"
            
            # Статистика
            if include_stats:
                try:
                    # Получаем статистику сервера
                    ldap_info["stats"] = {
                        "users_count": "Недоступно",
                        "groups_count": "Недоступно"
                    }
                except Exception:
                    ldap_info["stats"] = "Недоступно"
            
            logger.info("✅ Получена информация о LDAP сервере")
            return format_tool_response(True, "Информация о LDAP сервере получена", ldap_info)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о LDAP: {e}")
            return format_tool_response(False, f"Ошибка получения информации о LDAP: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья LDAP сервера"""
        try:
            if not self.is_enabled():
                return {
                    'status': 'disabled',
                    'provider': 'ldap',
                    'message': 'LDAP отключен в конфигурации'
                }
            
            # Проверяем подключение к LDAP
            if hasattr(self, 'server') and self.server:
                # Пытаемся подключиться к LDAP серверу
                from ldap3 import Connection, Server
                
                server = Server(self.server)
                conn = Connection(server, auto_bind=True)
                
                if conn.bind():
                    conn.unbind()
                    return {
                        'status': 'healthy',
                        'provider': 'ldap',
                        'message': f'Подключение к LDAP успешно. Сервер: {self.server}',
                        'server_url': self.server
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'provider': 'ldap',
                        'message': 'Не удается подключиться к LDAP серверу'
                    }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'ldap',
                    'message': 'LDAP сервер не настроен'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья LDAP: {e}")
            return {
                'status': 'unhealthy',
                'provider': 'ldap',
                'error': str(e)
            }
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Возвращает список инструментов LDAP сервера"""
        return self.tools

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр LDAP сервера
ldap_server = LDAPMCPServer()
