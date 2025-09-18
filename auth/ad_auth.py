import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

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
except ImportError:
    PASSWORD_AVAILABLE = False
    print("⚠️ passlib не установлен. Хеширование паролей будет недоступно.")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка для хеширования паролей
if PASSWORD_AVAILABLE:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None

class ADAuthenticator:
    def __init__(self):
        from config.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        self.ad_server = None
        self.ad_domain = None
        self.ad_base_dn = None
        self.jwt_secret = 'super-secret-key'
        self.jwt_algorithm = 'HS256'
        self.jwt_expire_hours = 24
        self._load_config()

    def _load_config(self):
        """Загружает конфигурацию Active Directory"""
        ad_config = self.config_manager.get_service_config('active_directory')
        self.ad_server = ad_config.get('server', '')
        self.ad_domain = ad_config.get('domain', '')
        self.ad_base_dn = ad_config.get('base_dn', '')
        self.ad_enabled = ad_config.get('enabled', False)
        self.ad_service_user = ad_config.get('service_user', '')
        self.ad_service_password = ad_config.get('service_password', '')
        
        jwt_config = self.config_manager.get_service_config('jwt')
        self.jwt_secret = jwt_config.get('secret', 'super-secret-key')
        self.jwt_algorithm = jwt_config.get('algorithm', 'HS256')
        self.jwt_expire_hours = jwt_config.get('expire_hours', 24)

        if not self.ad_enabled:
            logger.info("⚠️ Active Directory отключен в конфигурации")
        elif not all([self.ad_server, self.ad_domain, self.ad_base_dn]):
            logger.warning("⚠️ Active Directory не настроен - отсутствуют данные в конфигурации")
        else:
            logger.info("✅ Active Directory настроен")
            logger.info(f"Server: {self.ad_server}")
            logger.info(f"Domain: {self.ad_domain}")
            logger.info(f"Base DN: {self.ad_base_dn}")
    
    def reconnect(self):
        """Переподключается с новой конфигурацией"""
        self._load_config()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентификация пользователя через Active Directory
        """
        if not LDAP_AVAILABLE:
            logger.error("LDAP библиотека не установлена")
            return None
            
        if not self.ad_enabled:
            logger.error("Active Directory отключен в конфигурации")
            return None
            
        if not all([self.ad_server, self.ad_domain, self.ad_base_dn]):
            logger.error("Active Directory не настроен")
            return None
        
        
        try:
            # Создаем подключение к AD серверу
            server = Server(self.ad_server, get_info=ALL)
            
            # Пробуем разные методы аутентификации
            
            # 1. Простая аутентификация с sAMAccountName
            try:
                user_dn = f"CN={username},{self.ad_base_dn}"
                with Connection(server, user=user_dn, password=password) as conn:
                    if conn.bind():
                        user_info = self._get_user_info(conn, username)
                        if user_info:
                            return user_info
            except Exception as e:
                logger.warning(f"DN аутентификация не удалась: {e}")
            
            # 2. Аутентификация с UPN (User Principal Name)
            try:
                user_dn = f"{username}@{self.ad_domain}"
                with Connection(server, user=user_dn, password=password) as conn:
                    if conn.bind():
                        user_info = self._get_user_info(conn, username)
                        if user_info:
                            return user_info
            except Exception as e:
                logger.warning(f"UPN аутентификация не удалась: {e}")
            
            # 3. Аутентификация с sAMAccountName
            try:
                user_dn = f"{self.ad_domain}\\{username}"
                with Connection(server, user=user_dn, password=password) as conn:
                    if conn.bind():
                        user_info = self._get_user_info(conn, username)
                        if user_info:
                            return user_info
            except Exception as e:
                logger.warning(f"sAMAccountName аутентификация не удалась: {e}")
            
            # 4. Поиск пользователя и аутентификация по найденному DN
            try:
                user_dn = self._find_user_dn(server, username)
                if user_dn:
                    logger.info(f"Найден DN пользователя: {user_dn}")
                    
                    # Аутентифицируемся с найденным DN
                    with Connection(server, user=user_dn, password=password) as auth_conn:
                        if auth_conn.bind():
                            user_info = self._get_user_info(auth_conn, username)
                            if user_info:
                                return user_info
            except Exception as e:
                logger.warning(f"Search DN аутентификация не удалась: {e}")
            
            # Если все попытки не удались
            logger.warning(f"❌ Неверные учетные данные для пользователя {username}")
            return None
                    
        except LDAPException as e:
            logger.error(f"❌ Ошибка подключения к Active Directory: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при аутентификации: {e}")
            return None
    
    def _find_user_dn(self, server: Server, username: str) -> Optional[str]:
        """Находит DN пользователя в Active Directory"""
        try:
            search_filter = f"(sAMAccountName={username})"
            
            # Пробуем анонимное подключение
            try:
                with Connection(server, authentication='ANONYMOUS') as conn:
                    if conn.bind():
                        conn.search(
                            search_base=self.ad_base_dn,
                            search_filter=search_filter,
                            search_scope='SUBTREE',
                            attributes=['distinguishedName']
                        )
                        
                        if conn.entries:
                            return str(conn.entries[0].distinguishedName)
            except Exception as e:
                logger.warning(f"Анонимный поиск не удался: {e}")
            
            # Пробуем с service account
            if self.ad_service_user and self.ad_service_password:
                try:
                    service_dn = f"{self.ad_domain}\\{self.ad_service_user}"
                    with Connection(server, user=service_dn, password=self.ad_service_password) as conn:
                        if conn.bind():
                            conn.search(
                                search_base=self.ad_base_dn,
                                search_filter=search_filter,
                                search_scope='SUBTREE',
                                attributes=['distinguishedName']
                            )
                            
                            if conn.entries:
                                return str(conn.entries[0].distinguishedName)
                except Exception as e:
                    logger.warning(f"Поиск с service account не удался: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя: {e}")
            return None
    
    def _get_user_info(self, conn: Connection, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе из Active Directory
        """
        try:
            # Поиск пользователя в AD
            search_filter = f"(sAMAccountName={username})"
            conn.search(
                search_base=self.ad_base_dn,
                search_filter=search_filter,
                search_scope='SUBTREE',
                attributes=['cn', 'mail', 'displayName', 'memberOf', 'sAMAccountName']
            )
            
            if conn.entries:
                entry = conn.entries[0]
                user_info = {
                    'username': str(entry.sAMAccountName),
                    'display_name': str(entry.displayName) if entry.displayName else username,
                    'email': str(entry.mail) if entry.mail else None,
                    'groups': [str(group) for group in entry.memberOf] if entry.memberOf else [],
                    'authenticated_at': datetime.utcnow().isoformat()
                }
                return user_info
            else:
                logger.warning(f"Пользователь {username} не найден в Active Directory")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе: {e}")
            return None
    
    def create_access_token(self, user_info: Dict[str, Any]) -> str:
        """
        Создает JWT токен для аутентифицированного пользователя
        """
        if not JWT_AVAILABLE:
            logger.error("JWT библиотека не установлена")
            return ""
            
        to_encode = {
            'username': user_info['username'],
            'display_name': user_info['display_name'],
            'email': user_info['email'],
            'groups': user_info['groups'],
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expire_hours),
            'iat': datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Проверяет и декодирует JWT токен
        """
        if not JWT_AVAILABLE:
            logger.error("JWT библиотека не установлена")
            return None
            
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT токен истек")
            return None
        except jwt.JWTError as e:
            logger.warning(f"Ошибка проверки JWT токена: {e}")
            return None
    
    def check_user_permissions(self, user_info: Dict[str, Any], required_groups: list = None) -> bool:
        """
        Проверяет права пользователя на основе групп AD
        """
        if not required_groups:
            return True
        
        user_groups = user_info.get('groups', [])
        
        # Проверяем, есть ли у пользователя хотя бы одна из требуемых групп
        for required_group in required_groups:
            if any(required_group.lower() in group.lower() for group in user_groups):
                return True
        
        return False
    
    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе из токена
        """
        payload = self.verify_token(token)
        if payload:
            return {
                'username': payload.get('username'),
                'display_name': payload.get('display_name'),
                'email': payload.get('email'),
                'groups': payload.get('groups', [])
            }
        return None
