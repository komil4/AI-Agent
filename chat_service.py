#!/usr/bin/env python3
"""
Сервис для работы с историей чата
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from database import get_db, User, ChatSession, Message, ToolUsage, is_database_enabled

# Импорт для работы с паролями
try:
    from passlib.context import CryptContext
    PASSWORD_AVAILABLE = True
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    PASSWORD_AVAILABLE = False
    pwd_context = None
    print("[WARN] passlib не установлен. Хеширование паролей будет недоступно.")

logger = logging.getLogger(__name__)

class ChatService:
    """Сервис для работы с историей чата"""
    
    # ============================================================================
    # ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
    # ============================================================================
    
    def __init__(self):
        """Инициализация сервиса чата"""
        pass
    
    # ============================================================================
    # ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
    # ============================================================================
    
    # --- Управление пользователями ---
    
    def get_or_create_user(self, username: str, user_info: Dict[str, Any]) -> User:
        """Получает или создает пользователя"""
        if not is_database_enabled():
            # Возвращаем фиктивного пользователя, если база данных отключена
            fake_user = User()
            fake_user.id = 1
            fake_user.username = username
            fake_user.email = user_info.get('email', '')
            fake_user.full_name = user_info.get('full_name', username)
            fake_user.is_ldap_user = user_info.get('is_ldap_user', False)
            fake_user.created_at = datetime.now()
            fake_user.updated_at = datetime.now()
            return fake_user
            
        with get_db() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if not user:
                # Создаем нового пользователя
                user = User(
                    username=username,
                    password_hash=user_info.get('password_hash'),
                    display_name=user_info.get('display_name', username),
                    email=user_info.get('email', ''),
                    groups=user_info.get('groups', []),
                    is_admin=user_info.get('is_admin', False),
                    is_ldap_user=user_info.get('is_ldap_user', False)
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"[OK] Создан новый пользователь: {username} (ID: {user.id})")
                logger.info(f"   Display Name: {user.display_name}")
                logger.info(f"   Email: {user.email}")
                logger.info(f"   Groups: {user.groups}")
                logger.info(f"   Is Admin: {user.is_admin}")
                logger.info(f"   Is LDAP User: {user.is_ldap_user}")
            else:
                # Обновляем информацию о пользователе
                old_display_name = user.display_name
                old_email = user.email
                old_groups = user.groups
                old_is_admin = user.is_admin
                
                user.display_name = user_info.get('display_name', user.display_name)
                user.email = user_info.get('email', user.email)
                user.groups = user_info.get('groups', user.groups)
                user.is_admin = user_info.get('is_admin', user.is_admin)
                user.last_login = datetime.utcnow()
                session.commit()
                
                # Логируем изменения
                changes = []
                if old_display_name != user.display_name:
                    changes.append(f"display_name: '{old_display_name}' -> '{user.display_name}'")
                if old_email != user.email:
                    changes.append(f"email: '{old_email}' -> '{user.email}'")
                if old_groups != user.groups:
                    changes.append(f"groups: {old_groups} -> {user.groups}")
                if old_is_admin != user.is_admin:
                    changes.append(f"is_admin: {old_is_admin} -> {user.is_admin}")
                
                if changes:
                    logger.info(f"[OK] Обновлен пользователь: {username} (ID: {user.id})")
                    logger.info(f"   Изменения: {', '.join(changes)}")
                else:
                    logger.info(f"[OK] Обновлен пользователь: {username} (ID: {user.id}) - только last_login")
            
            # Отсоединяем объект от сессии и возвращаем данные
            session.expunge(user)
            return user
    
    def authenticate_local_user(self, username: str, password: str) -> Optional[User]:
        """Аутентификация локального пользователя по паролю"""
        if not is_database_enabled():
            logger.warning("[WARN] База данных отключена, локальная аутентификация недоступна")
            return None
            
        with get_db() as session:
            user = session.query(User).filter(
                User.username == username,
                User.is_ldap_user == False,
                User.password_hash.isnot(None)
            ).first()
            
            if user and user.password_hash:
                try:
                    if self.verify_password(password, user.password_hash):
                        # Обновляем время последнего входа
                        user.last_login = datetime.utcnow()
                        session.commit()
                        
                        # Отсоединяем объект от сессии
                        session.expunge(user)
                        
                        logger.info(f"[OK] Локальная аутентификация успешна: {username}")
                        return user
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка проверки пароля для пользователя {username}: {e}")
                    # Если ошибка с хешем, считаем пароль неверным
                    pass
            
            logger.warning(f"[ERROR] Неверные учетные данные для локального пользователя: {username}")
            return None
    
    # --- Управление сессиями чата ---
    
    def create_chat_session(self, user_id: int, session_name: str = None) -> ChatSession:
        """Создает новую сессию чата"""
        if not is_database_enabled():
            # Возвращаем фиктивную сессию, если база данных отключена
            fake_session = ChatSession()
            fake_session.id = 1
            fake_session.user_id = user_id
            fake_session.name = session_name or f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            fake_session.is_active = True
            fake_session.created_at = datetime.now()
            fake_session.updated_at = datetime.now()
            return fake_session
            
        with get_db() as session:
            if not session_name:
                session_name = f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            chat_session = ChatSession(
                user_id=user_id,
                session_name=session_name,
                is_active=True
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            
            # Отсоединяем объект от сессии
            session.expunge(chat_session)
            
            logger.info(f"[OK] Создана новая сессия чата: {session_name}")
            return chat_session
    
    def get_active_session(self, user_id: int) -> Optional[ChatSession]:
        """Получает активную сессию пользователя"""
        if not is_database_enabled():
            # Возвращаем фиктивную активную сессию, если база данных отключена
            fake_session = ChatSession()
            fake_session.id = 1
            fake_session.user_id = user_id
            fake_session.name = f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            fake_session.is_active = True
            fake_session.created_at = datetime.now()
            fake_session.updated_at = datetime.now()
            return fake_session
            
        with get_db() as session:
            chat_session = session.query(ChatSession).filter(
                and_(ChatSession.user_id == user_id, ChatSession.is_active == True)
            ).first()
            
            if chat_session:
                # Отсоединяем объект от сессии
                session.expunge(chat_session)
            
            return chat_session
    
    def get_user_sessions(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Получает список сессий пользователя"""
        with get_db() as session:
            sessions = session.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(desc(ChatSession.updated_at)).limit(limit).all()
            
            # Отсоединяем объекты от сессии и возвращаем данные
            result = []
            for session_obj in sessions:
                session.expunge(session_obj)
                result.append({
                    'id': session_obj.id,
                    'user_id': session_obj.user_id,
                    'session_name': session_obj.session_name,
                    'created_at': session_obj.created_at,
                    'updated_at': session_obj.updated_at,
                    'is_active': session_obj.is_active
                })
            
            return result
    
    def get_session_by_id(self, session_id: int) -> Optional[ChatSession]:
        """Получает сессию чата по ID"""
        with get_db() as session:
            chat_session = session.query(ChatSession).filter(ChatSession.id == session_id).first()
            return chat_session
    
    def close_session(self, session_id: int):
        """Закрывает сессию чата"""
        with get_db() as session:
            chat_session = session.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.is_active = False
                chat_session.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"[OK] Сессия {session_id} закрыта")
    
    # --- Управление сообщениями ---
    
    def add_message(self, session_id: int, user_id: int, message_type: str, 
                   content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Добавляет сообщение в сессию"""
        with get_db() as session:
            message = Message(
                session_id=session_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                message_metadata=metadata or {}
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            
            # Обновляем время последнего обновления сессии
            chat_session = session.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.updated_at = datetime.utcnow()
                session.commit()
            
            # Сохраняем данные сообщения до отсоединения от сессии
            message_data = {
                'id': message.id,
                'session_id': message.session_id,
                'user_id': message.user_id,
                'message_type': message.message_type,
                'content': message.content,
                'message_metadata': message.message_metadata,
                'created_at': message.created_at
            }
            
            # Отсоединяем объект от сессии
            session.expunge(message)
            
            logger.info(f"[OK] Добавлено сообщение в сессию {session_id}")
            return message_data
    
    def get_session_messages(self, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает сообщения сессии"""
        with get_db() as session:
            messages = session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at).limit(limit).all()
            
            # Отсоединяем объекты от сессии и возвращаем данные
            result = []
            for message in messages:
                session.expunge(message)
                result.append({
                    'id': message.id,
                    'session_id': message.session_id,
                    'user_id': message.user_id,
                    'message_type': message.message_type,
                    'content': message.content,
                    'message_metadata': message.message_metadata,
                    'created_at': message.created_at
                })
            
            return result
    
    def get_session_history(self, session_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Получает полную историю сессии с инструментами"""
        with get_db() as session:
            query = session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at)
            
            if limit:
                query = query.limit(limit)
            
            messages = query.all()
            
            history = []
            for msg in messages:
                # Отсоединяем объект от сессии перед использованием
                session.expunge(msg)
                
                message_data = {
                    'id': msg.id,
                    'type': msg.message_type,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'metadata': msg.message_metadata or {},
                    'tools': []
                }
                
                # Получаем инструменты отдельным запросом
                tools = session.query(ToolUsage).filter(ToolUsage.message_id == msg.id).all()
                for tool in tools:
                    session.expunge(tool)
                    message_data['tools'].append({
                        'tool_name': tool.tool_name,
                        'server_name': tool.server_name,
                        'arguments': tool.arguments or {},
                        'result': tool.result or {},
                        'execution_time_ms': tool.execution_time_ms,
                        'created_at': tool.created_at.isoformat()
                    })
                
                history.append(message_data)
            
            return history
    
    # --- Управление инструментами ---
    
    def add_tool_usage(self, message_id: int, tool_name: str, server_name: str,
                      arguments: Dict[str, Any] = None, result: Dict[str, Any] = None,
                      execution_time_ms: int = None) -> Dict[str, Any]:
        """Добавляет информацию об использовании инструмента"""
        with get_db() as session:
            tool_usage = ToolUsage(
                message_id=message_id,
                tool_name=tool_name,
                server_name=server_name,
                arguments=arguments or {},
                result=result or {},
                execution_time_ms=execution_time_ms
            )
            session.add(tool_usage)
            session.commit()
            session.refresh(tool_usage)
            
            # Отсоединяем объект от сессии и возвращаем данные
            session.expunge(tool_usage)
            
            logger.info(f"[OK] Добавлено использование инструмента: {tool_name}")
            return {
                'id': tool_usage.id,
                'message_id': tool_usage.message_id,
                'tool_name': tool_usage.tool_name,
                'server_name': tool_usage.server_name,
                'arguments': tool_usage.arguments,
                'result': tool_usage.result,
                'execution_time_ms': tool_usage.execution_time_ms,
                'created_at': tool_usage.created_at
            }
    
    # --- Статистика ---
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получает статистику пользователя"""
        with get_db() as session:
            # Количество сессий
            sessions_count = session.query(ChatSession).filter(ChatSession.user_id == user_id).count()
            
            # Количество сообщений
            messages_count = session.query(Message).filter(Message.user_id == user_id).count()
            
            # Количество использованных инструментов
            tools_count = session.query(ToolUsage).join(Message).filter(Message.user_id == user_id).count()
            
            # Последняя активность
            last_message = session.query(Message).filter(Message.user_id == user_id).order_by(desc(Message.created_at)).first()
            last_activity = last_message.created_at if last_message else None
            
            return {
                'sessions_count': sessions_count,
                'messages_count': messages_count,
                'tools_count': tools_count,
                'last_activity': last_activity.isoformat() if last_activity else None
            }
    
    # ============================================================================
    # СЛУЖЕБНЫЕ ФУНКЦИИ
    # ============================================================================
    
    def hash_password(self, password: str) -> str:
        """Хеширует пароль"""
        if not PASSWORD_AVAILABLE:
            raise RuntimeError("passlib не установлен")
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        if not PASSWORD_AVAILABLE:
            raise RuntimeError("passlib не установлен")
        
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except ValueError as e:
            if "unsupported hash type" in str(e):
                logger.warning(f"[WARN] Неподдерживаемый тип хеша: {e}")
                # Если хеш неподдерживаемый, считаем пароль неверным
                return False
            raise
    
    # --- Управление контекстом пользователя ---
    
    def save_user_context(self, user_id: int, context: str) -> bool:
        """Сохраняет дополнительный контекст пользователя"""
        try:
            with get_db() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.user_context = context
                    session.commit()
                    logger.info(f"[OK] Контекст пользователя сохранен: {user.username} (ID: {user_id})")
                    return True
                else:
                    logger.error(f"[ERROR] Пользователь не найден: ID {user_id}")
                    return False
        except Exception as e:
            logger.error(f"[ERROR] Ошибка сохранения контекста пользователя {user_id}: {e}")
            return False
    
    def get_user_context(self, user_id: int) -> Optional[str]:
        """Получает дополнительный контекст пользователя"""
        try:
            with get_db() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    context = user.user_context
                    logger.debug(f"📋 Контекст пользователя получен: {user.username} (ID: {user_id})")
                    return context
                else:
                    logger.error(f"[ERROR] Пользователь не найден: ID {user_id}")
                    return None
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения контекста пользователя {user_id}: {e}")
            return None
    
    def update_user_context(self, user_id: int, new_context: str) -> bool:
        """Обновляет контекст пользователя (добавляет к существующему)"""
        try:
            with get_db() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    # Если контекст уже существует, добавляем к нему
                    if user.user_context:
                        user.user_context = f"{user.user_context}\n\n{new_context}"
                    else:
                        user.user_context = new_context
                    
                    session.commit()
                    logger.info(f"[OK] Контекст пользователя обновлен: {user.username} (ID: {user_id})")
                    return True
                else:
                    logger.error(f"[ERROR] Пользователь не найден: ID {user_id}")
                    return False
        except Exception as e:
            logger.error(f"[ERROR] Ошибка обновления контекста пользователя {user_id}: {e}")
            return False
    
    def clear_user_context(self, user_id: int) -> bool:
        """Очищает контекст пользователя"""
        try:
            with get_db() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.user_context = None
                    session.commit()
                    logger.info(f"[OK] Контекст пользователя очищен: {user.username} (ID: {user_id})")
                    return True
                else:
                    logger.error(f"[ERROR] Пользователь не найден: ID {user_id}")
                    return False
        except Exception as e:
            logger.error(f"[ERROR] Ошибка очистки контекста пользователя {user_id}: {e}")
            return False

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Глобальный экземпляр сервиса
chat_service = ChatService()