#!/usr/bin/env python3
"""
Скрипт для изменения хеша пароля пользователя
"""

import logging
from database import get_db, init_database
from config.config_manager import ConfigManager
from sqlalchemy import text
from chat_service import ChatService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def change_user_password(username: str, new_password: str):
    """Изменяет пароль пользователя"""
    try:
        # Инициализация базы данных
        config_manager = ConfigManager()
        database_url = config_manager.get_database_url()
        init_database(database_url)
        
        # Получение соединения с базой данных
        db = next(get_db())
        
        # Создание нового хеша пароля
        chat_service = ChatService()
        new_password_hash = chat_service.hash_password(new_password)
        
        # Обновление пароля в базе данных
        result = db.execute(text("""
            UPDATE users 
            SET password_hash = :password_hash 
            WHERE username = :username AND is_ldap_user = FALSE
        """), {
            "password_hash": new_password_hash,
            "username": username
        })
        
        if result.rowcount > 0:
            db.commit()
            logger.info(f"✅ Пароль для пользователя {username} успешно изменен")
            logger.info(f"🔐 Новый хеш: {new_password_hash[:20]}...")
        else:
            logger.warning(f"⚠️ Пользователь {username} не найден или является LDAP пользователем")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при изменении пароля: {e}")
        raise

def list_users_with_passwords():
    """Показывает список пользователей с паролями"""
    try:
        # Инициализация базы данных
        config_manager = ConfigManager()
        database_url = config_manager.get_database_url()
        init_database(database_url)
        
        # Получение соединения с базой данных
        db = next(get_db())
        
        # Получение списка пользователей
        result = db.execute(text("""
            SELECT username, password_hash, is_ldap_user, last_login
            FROM users 
            ORDER BY username
        """))
        
        users = result.fetchall()
        
        logger.info(f"👥 Найдено пользователей: {len(users)}")
        print("\n" + "="*80)
        print(f"{'Username':<20} {'Type':<10} {'Has Password':<12} {'Last Login':<20}")
        print("="*80)
        
        for username, password_hash, is_ldap_user, last_login in users:
            user_type = "LDAP" if is_ldap_user else "Local"
            has_password = "Yes" if password_hash else "No"
            last_login_str = str(last_login)[:19] if last_login else "Never"
            
            print(f"{username:<20} {user_type:<10} {has_password:<12} {last_login_str:<20}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка пользователей: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python change_password_hash.py list                    # Показать список пользователей")
        print("  python change_password_hash.py change <username> <password>  # Изменить пароль")
        print("\nПримеры:")
        print("  python change_password_hash.py list")
        print("  python change_password_hash.py change admin newpassword123")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_users_with_passwords()
    elif command == "change":
        if len(sys.argv) < 4:
            print("❌ Ошибка: Необходимо указать имя пользователя и новый пароль")
            print("Использование: python change_password_hash.py change <username> <password>")
            sys.exit(1)
        
        username = sys.argv[2]
        new_password = sys.argv[3]
        
        print(f"🔄 Изменение пароля для пользователя: {username}")
        change_user_password(username, new_password)
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Доступные команды: list, change")
        sys.exit(1)
