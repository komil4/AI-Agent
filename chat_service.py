#!/usr/bin/env python3
"""
Сервис для работы с историей чата
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from database import get_db, User, ChatSession, Message, ToolUsage

# Импорт для работы с паролями
try:
    from passlib.context import CryptContext
    PASSWORD_AVAILABLE = True
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    PASSWORD_AVAILABLE = False
    pwd_context = None
    print("⚠️ passlib не установлен. Хеширование паролей будет недоступно.")

logger = logging.getLogger(__name__)

class ChatService:
    """Сервис для работы с историей чата"""
    
    def __init__(self):
        pass
    
    def hash_password(self, password: str) -> str:
        """Хеширует пароль"""
        if not PASSWORD_AVAILABLE:
            raise RuntimeError("passlib не установлен")
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        if not PASSWORD_AVAILABLE:
            raise RuntimeError("passlib не установлен")
        return pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_local_user(self, username: str, password: str) -> Optional[User]:
        """Аутентификация локального пользователя по паролю"""
        with get_db() as session:
            user = session.query(User).filter(
                User.username == username,
                User.is_ldap_user == False,
                User.password_hash.isnot(None)
            ).first()
            
            if user and self.verify_password(password, user.password_hash):
                # Обновляем время последнего входа
                user.last_login = datetime.utcnow()
                session.commit()
                logger.info(f"✅ Локальная аутентификация успешна: {username}")
                return user
            
            logger.warning(f"❌ Неверные учетные данные для локального пользователя: {username}")
            return None
    
    def get_or_create_user(self, username: str, user_info: Dict[str, Any]) -> User:
        """Получает или создает пользователя"""
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
                logger.info(f"✅ Создан новый пользователь: {username} (ID: {user.id})")
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
                    logger.info(f"✅ Обновлен пользователь: {username} (ID: {user.id})")
                    logger.info(f"   Изменения: {', '.join(changes)}")
                else:
                    logger.info(f"✅ Обновлен пользователь: {username} (ID: {user.id}) - только last_login")
            
            return user
    
    def create_chat_session(self, user_id: int, session_name: str = None) -> ChatSession:
        """Создает новую сессию чата"""
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
            logger.info(f"✅ Создана новая сессия чата: {session_name}")
            return chat_session
    
    def get_active_session(self, user_id: int) -> Optional[ChatSession]:
        """Получает активную сессию пользователя"""
        with get_db() as session:
            return session.query(ChatSession).filter(
                and_(ChatSession.user_id == user_id, ChatSession.is_active == True)
            ).first()
    
    def get_user_sessions(self, user_id: int, limit: int = 20) -> List[ChatSession]:
        """Получает список сессий пользователя"""
        with get_db() as session:
            return session.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(desc(ChatSession.updated_at)).limit(limit).all()
    
    def add_message(self, session_id: int, user_id: int, message_type: str, 
                   content: str, metadata: Dict[str, Any] = None) -> Message:
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
            
            logger.info(f"✅ Добавлено сообщение в сессию {session_id}")
            return message
    
    def get_session_messages(self, session_id: int, limit: int = 50) -> List[Message]:
        """Получает сообщения сессии"""
        with get_db() as session:
            return session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at).limit(limit).all()
    
    def add_tool_usage(self, message_id: int, tool_name: str, server_name: str,
                      arguments: Dict[str, Any] = None, result: Dict[str, Any] = None,
                      execution_time_ms: int = None) -> ToolUsage:
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
            logger.info(f"✅ Добавлено использование инструмента: {tool_name}")
            return tool_usage
    
    def get_session_history(self, session_id: int) -> List[Dict[str, Any]]:
        """Получает полную историю сессии с инструментами"""
        with get_db() as session:
            messages = session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at).all()
            
            history = []
            for msg in messages:
                message_data = {
                    'id': msg.id,
                    'type': msg.message_type,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'metadata': msg.message_metadata or {},
                    'tools': []
                }
                
                # Добавляем информацию об использованных инструментах
                for tool in msg.tool_usage:
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
    
    def close_session(self, session_id: int):
        """Закрывает сессию чата"""
        with get_db() as session:
            chat_session = session.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.is_active = False
                chat_session.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"✅ Сессия {session_id} закрыта")
    
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

# Глобальный экземпляр сервиса
chat_service = ChatService()
