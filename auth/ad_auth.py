#!/usr/bin/env python3
"""
Аутентификация через Active Directory (LDAP)
"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Проверка доступности зависимостей
try:
    from ldap3 import Server, Connection, ALL, NTLM
    from ldap3.core.exceptions import LDAPException
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    print("⚠️ ldap3 не установлен. Active Directory будет недоступен.")

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ PyJWT не установлен. JWT токены будут недоступны.")

try:
    from passlib.context import CryptContext
    PASSWORD_AVAILABLE = True
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    PASSWORD_AVAILABLE = False
    pwd_context = None
    print("⚠️ passlib не установлен. Хеширование паролей будет недоступно.")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# pwd_context уже создан выше в блоке try/except

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class ADAuthenticator:
    """Аутентификатор Active Directory"""
    
    def __init__(self):
        """Инициализация аутентификатора"""
        from config.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        self.ad_server = None
        self.ad_domain = None
        self.ad_base_dn = None
        self.ad_service_user = None
        self.ad_service_password = None
        self.jwt_secret = 'super-secret-key'
        self.jwt_algorithm = 'HS256'
        self.jwt_expire_hours = 24
        self._load_config()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя через LDAP"""
        if not LDAP_AVAILABLE:
            logger.error("❌ LDAP недоступен - библиотека ldap3 не установлена")
            return None
        
        if not self.ad_server:
            logger.error("❌ LDAP сервер не настроен")
            return None
        
        try:

            server = self.ad_server
            # 1. Простая аутентификация с sAMAccountName
            try:
                user_dn = f"CN={self.ad_service_user},{self.ad_base_dn}"
                connection = Connection(server, user=user_dn, password=self.ad_service_password)
                if connection.bind():
                    user_info = self._get_user_info(connection, username)
                    if user_info:
                        return user_info
            except Exception as e:
                logger.warning(f"DN аутентификация не удалась: {e}")
            
            # 2. Аутентификация с UPN (User Principal Name)
            try:
                user_dn = f"{self.ad_service_user}@{self.ad_domain}"
                connection = Connection(server, user=user_dn, password=self.ad_service_password)
                if connection.bind():
                    user_info = self._get_user_info(connection, username)
                    if user_info:
                        return user_info    
            except Exception as e:
                logger.warning(f"UPN аутентификация не удалась: {e}")
            
            # 3. Аутентификация с sAMAccountName
            try:
                user_dn = f"{self.ad_domain}\\{self.ad_service_user}"
                connection = Connection(server, user=user_dn, password=self.ad_service_password)
                if connection.bind():
                    user_info = self._get_user_info(connection, username)
                    if user_info:
                        return user_info 
            except Exception as e:
                logger.warning(f"sAMAccountName аутентификация не удалась: {e}")
                       
            logger.warning(f"❌ Пользователь не найден в AD: {username}")
            connection.unbind()
            return None
            
        except LDAPException as e:
            logger.error(f"❌ Ошибка LDAP аутентификации: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка аутентификации: {e}")
            return None
    
    def create_access_token(self, user_info: Dict[str, Any]) -> str:
        """Создает JWT токен доступа"""
        if not JWT_AVAILABLE:
            logger.error("❌ JWT недоступен - библиотека PyJWT не установлена")
            return ""
        
        try:
            # Подготавливаем данные для токена
            token_data = {
                'username': user_info['username'],
                'display_name': user_info.get('display_name', user_info['username']),
                'email': user_info.get('email', ''),
                'groups': user_info.get('groups', []),
                'is_admin': user_info.get('is_admin', False),
                'exp': datetime.utcnow() + timedelta(hours=self.jwt_expire_hours),
                'iat': datetime.utcnow()
            }
            
            # Создаем токен
            token = jwt.encode(token_data, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.info(f"✅ Создан JWT токен для пользователя: {user_info['username']}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания JWT токена: {e}")
            return ""
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверяет JWT токен доступа"""
        if not JWT_AVAILABLE:
            logger.error("❌ JWT недоступен - библиотека PyJWT не установлена")
            return None
        
        try:
            # Декодируем токен
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Проверяем срок действия
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                logger.warning("❌ JWT токен истек")
                return None
            
            logger.info(f"✅ JWT токен валиден для пользователя: {payload['username']}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("❌ JWT токен истек")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Невалидный JWT токен: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки JWT токена: {e}")
            return None
    
    def reconnect(self):
        """Переподключение к LDAP серверу"""
        logger.info("🔄 Переподключение к LDAP серверу...")
        self._load_config()
        logger.info("✅ Переподключение к LDAP завершено")
    
    def is_connected(self) -> bool:
        """Проверяет подключение к LDAP серверу"""
        if not LDAP_AVAILABLE or not self.ad_server:
            return False
        
        try:
            # Пробуем подключиться
            conn = Connection(self.ad_server, auto_bind=True)
            conn.unbind()
            return True
        except Exception:
            return False

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================
    
    def _load_config(self):
        """Загружает конфигурацию LDAP"""
        try:
            ad_config = self.config_manager.get_service_config('active_directory')
            
            if ad_config.get('enabled', False):
                self.ad_server = Server(
                    ad_config.get('server'),
                    get_info=ALL,
                    connect_timeout=60
                )
                self.ad_domain = ad_config.get('domain')
                self.ad_base_dn = ad_config.get('base_dn')
                self.ad_service_user = ad_config.get('service_user', '')
                self.ad_service_password = ad_config.get('service_password', '')
                
                # JWT настройки
                jwt_config = ad_config.get('jwt', {})
                self.jwt_secret = jwt_config.get('secret', 'super-secret-key')
                self.jwt_algorithm = jwt_config.get('algorithm', 'HS256')
                self.jwt_expire_hours = jwt_config.get('expire_hours', 24)
                
                logger.info(f"✅ Конфигурация LDAP загружена: {ad_config.get('server')}")
            else:
                logger.info("ℹ️ LDAP отключен в конфигурации")
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации LDAP: {e}")

    def _get_user_info(self, conn: Connection, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе из Active Directory
        """
        try:
            attributes=['sAMAccountName', 'displayName', 'mail', 'cn', 'givenName', 'sn', 'userPrincipalName']
            search_filter = f"(sAMAccountName={username})"
            # Пробуем анонимное подключение
            conn.search(
                search_base=self.ad_base_dn,
                search_filter=search_filter,
                search_scope='SUBTREE',
                attributes = attributes
            )
                        
            if conn.entries:       
                # Извлекаем группы
                entry = conn.entries[0]
                groups = []
                if hasattr(entry, 'memberOf'):
                    for group_dn in entry.memberOf.values:
                        # Извлекаем имя группы из DN
                        group_name = group_dn.split(',')[0].replace('CN=', '')
                        groups.append(group_name)
                        
                # Определяем права администратора
                is_admin = any('admin' in group.lower() for group in groups)

                # Форматируем результаты
                user_data = {}
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr)
                        if isinstance(value, list) and len(value) > 0:
                            user_data[attr] = str(value[0])
                        elif value:
                            user_data[attr] = str(value)

                if conn.entries:
                    entry = conn.entries[0]
                    user_info = {
                        'username': str(user_data['sAMAccountName']),
                        'display_name': str(user_data['displayName']) if user_data['displayName'] else username,
                        'email': str(user_data['mail']) if user_data['mail'] else None,
                        'groups': groups,
                        'is_admin': is_admin
                    }
                    return user_info
                else:
                    logger.warning(f"Пользователь {username} не найден в Active Directory")
                    return None
            return None    
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе: {e}")
            return None

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр аутентификатора
ad_auth = ADAuthenticator()
