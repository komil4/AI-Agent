#!/usr/bin/env python3
"""
Модели базы данных для MCP Chat
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================================================

Base = declarative_base()

# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255))  # Хеш пароля для локальных пользователей
    display_name = Column(String(200))
    email = Column(String(200))
    groups = Column(ARRAY(String))
    is_admin = Column(Boolean, default=False)
    is_ldap_user = Column(Boolean, default=False)  # Флаг LDAP пользователя
    user_context = Column(Text)  # Дополнительный контекст пользователя от LLM
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Связи
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")

class ChatSession(Base):
    """Модель сессии чата"""
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Связи
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    """Модель сообщения"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_type = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="messages")
    tool_usage = relationship("ToolUsage", back_populates="message", cascade="all, delete-orphan")

class ToolUsage(Base):
    """Модель использования инструментов"""
    __tablename__ = 'tool_usage'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    tool_name = Column(String(100), nullable=False)
    server_name = Column(String(100), nullable=False)
    arguments = Column(JSON)
    result = Column(JSON)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    message = relationship("Message", back_populates="tool_usage")

# ============================================================================
# ПРОГРАММНЫЙ ИНТЕРФЕЙС (API)
# ============================================================================

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, database_url: str):
        """Инициализация менеджера базы данных"""
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Создает все таблицы"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Таблицы базы данных созданы")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise
    
    def get_session(self):
        """Возвращает сессию базы данных"""
        return self.SessionLocal()
    
    def test_connection(self):
        """Тестирует подключение к базе данных"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                logger.info("✅ Подключение к базе данных успешно")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            return False

# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

# Глобальный экземпляр менеджера базы данных
db_manager = None

def init_database(database_url: str):
    """Инициализирует базу данных"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager

def get_db():
    """Возвращает сессию базы данных"""
    if db_manager is None:
        raise RuntimeError("База данных не инициализирована")
    return db_manager.get_session()