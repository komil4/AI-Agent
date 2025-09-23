#!/usr/bin/env python3
"""
Утилита для создания локальных пользователей в MCP Chat
"""

import sys
import os
import getpass
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chat_service import ChatService
from config.config_manager import ConfigManager
from database import init_database

def create_local_user():
    """Создает локального пользователя"""
    print("🔧 Создание локального пользователя в MCP Chat")
    print("=" * 50)
    
    # Получаем данные пользователя
    username = input("Введите имя пользователя: ").strip()
    if not username:
        print("❌ Имя пользователя не может быть пустым")
        return
    
    display_name = input("Введите отображаемое имя (опционально): ").strip()
    if not display_name:
        display_name = username
    
    email = input("Введите email (опционально): ").strip()
    
    # Получаем пароль
    password = getpass.getpass("Введите пароль: ")
    if not password:
        print("❌ Пароль не может быть пустым")
        return
    
    password_confirm = getpass.getpass("Подтвердите пароль: ")
    if password != password_confirm:
        print("❌ Пароли не совпадают")
        return
    
    # Проверяем права администратора
    is_admin_input = input("Сделать пользователя администратором? (y/N): ").strip().lower()
    is_admin = is_admin_input in ['y', 'yes', 'да', 'д']
    
    try:
        # Инициализируем конфигурацию и базу данных
        config_manager = ConfigManager()
        database_url = config_manager.get_database_url()
        init_database(database_url)
        
        # Создаем сервис чата
        chat_service = ChatService()
        
        # Хешируем пароль
        password_hash = chat_service.hash_password(password)
        
        # Подготавливаем данные пользователя
        user_info = {
            'username': username,
            'password_hash': password_hash,
            'display_name': display_name,
            'email': email,
            'groups': [],
            'is_admin': is_admin,
            'is_ldap_user': False
        }
        
        # Создаем пользователя
        print(f"💾 Создаем пользователя {username}...")
        user = chat_service.get_or_create_user(username, user_info)
        
        print("✅ Пользователь успешно создан!")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Display Name: {user.display_name}")
        print(f"   Email: {user.email}")
        print(f"   Is Admin: {user.is_admin}")
        print(f"   Is LDAP User: {user.is_ldap_user}")
        
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        import traceback
        traceback.print_exc()

def list_users():
    """Показывает список пользователей"""
    try:
        from database import get_db, User
        
        print("👥 Список пользователей:")
        print("=" * 50)
        
        with get_db() as session:
            users = session.query(User).order_by(User.created_at.desc()).all()
            
            if not users:
                print("Пользователи не найдены")
                return
            
            for user in users:
                user_type = "LDAP" if user.is_ldap_user else "Локальный"
                admin_flag = " (Admin)" if user.is_admin else ""
                print(f"ID: {user.id:3d} | {user.username:15s} | {user_type:10s} | {user.display_name or 'N/A':20s}{admin_flag}")
                print(f"     Email: {user.email or 'N/A'}")
                print(f"     Groups: {user.groups or []}")
                print(f"     Created: {user.created_at}")
                print(f"     Last Login: {user.last_login or 'Never'}")
                print("-" * 50)
                
    except Exception as e:
        print(f"❌ Ошибка получения списка пользователей: {e}")

def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "list":
            list_users()
        elif command == "create":
            create_local_user()
        else:
            print("❌ Неизвестная команда. Используйте 'create' или 'list'")
    else:
        print("🔧 Утилита управления пользователями MCP Chat")
        print("=" * 50)
        print("Использование:")
        print("  python create_local_user.py create  - создать пользователя")
        print("  python create_local_user.py list    - показать список пользователей")
        print()
        
        choice = input("Выберите действие (create/list): ").strip().lower()
        if choice == "create":
            create_local_user()
        elif choice == "list":
            list_users()
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
