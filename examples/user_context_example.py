#!/usr/bin/env python3
"""
Пример использования системы дополнительного контекста пользователя
"""

import requests
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserContextExample:
    """Пример работы с контекстом пользователя"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def login(self, username: str, password: str) -> bool:
        """Вход в систему"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Успешный вход: {username}")
                return True
            else:
                logger.error(f"❌ Ошибка входа: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при входе: {e}")
            return False
    
    def save_context(self, context: str) -> bool:
        """Сохраняет контекст пользователя"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/user/context",
                json={"context": context}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Контекст сохранен: {data.get('message')}")
                return True
            else:
                logger.error(f"❌ Ошибка сохранения контекста: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении контекста: {e}")
            return False
    
    def get_context(self) -> str:
        """Получает контекст пользователя"""
        try:
            response = self.session.get(f"{self.base_url}/api/user/context")
            
            if response.status_code == 200:
                data = response.json()
                context = data.get('context', '')
                logger.info(f"✅ Контекст получен: {len(context)} символов")
                return context
            else:
                logger.error(f"❌ Ошибка получения контекста: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении контекста: {e}")
            return ""
    
    def update_context(self, new_context: str) -> bool:
        """Обновляет контекст пользователя (добавляет к существующему)"""
        try:
            response = self.session.put(
                f"{self.base_url}/api/user/context",
                json={"context": new_context}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Контекст обновлен: {data.get('message')}")
                return True
            else:
                logger.error(f"❌ Ошибка обновления контекста: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении контекста: {e}")
            return False
    
    def clear_context(self) -> bool:
        """Очищает контекст пользователя"""
        try:
            response = self.session.delete(f"{self.base_url}/api/user/context")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Контекст очищен: {data.get('message')}")
                return True
            else:
                logger.error(f"❌ Ошибка очистки контекста: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке контекста: {e}")
            return False
    
    def send_chat_message(self, message: str) -> str:
        """Отправляет сообщение в чат"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json={"message": message}
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                logger.info(f"✅ Ответ получен: {len(response_text)} символов")
                return response_text
            else:
                logger.error(f"❌ Ошибка отправки сообщения: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке сообщения: {e}")
            return ""

def main():
    """Основная функция примера"""
    print("🚀 Пример использования системы контекста пользователя")
    
    # Создаем экземпляр
    example = UserContextExample()
    
    # Входим в систему (замените на реальные данные)
    if not example.login("admin", "admin"):
        print("❌ Не удалось войти в систему")
        return
    
    print("\n📝 Сохраняем начальный контекст...")
    initial_context = """
    Пользователь работает в IT отделе компании ABC.
    Специализируется на Python разработке.
    Предпочитает краткие и технические ответы.
    Работает с Django, FastAPI, PostgreSQL.
    """
    
    if example.save_context(initial_context):
        print("✅ Начальный контекст сохранен")
    
    print("\n📋 Получаем сохраненный контекст...")
    context = example.get_context()
    if context:
        print(f"📄 Контекст: {context[:100]}...")
    
    print("\n💬 Отправляем сообщение в чат...")
    response = example.send_chat_message("Привет! Расскажи о себе")
    if response:
        print(f"🤖 Ответ: {response[:100]}...")
    
    print("\n🔄 Обновляем контекст...")
    additional_context = """
    Дополнительная информация: пользователь интересуется машинным обучением.
    Предпочитает использовать Docker для контейнеризации.
    """
    
    if example.update_context(additional_context):
        print("✅ Контекст обновлен")
    
    print("\n📋 Получаем обновленный контекст...")
    updated_context = example.get_context()
    if updated_context:
        print(f"📄 Обновленный контекст: {updated_context[:150]}...")
    
    print("\n💬 Отправляем еще одно сообщение...")
    response2 = example.send_chat_message("Какие технологии ты знаешь?")
    if response2:
        print(f"🤖 Ответ: {response2[:100]}...")
    
    print("\n🗑️ Очищаем контекст...")
    if example.clear_context():
        print("✅ Контекст очищен")
    
    print("\n📋 Проверяем, что контекст очищен...")
    empty_context = example.get_context()
    if not empty_context:
        print("✅ Контекст успешно очищен")
    
    print("\n🎉 Пример завершен!")

if __name__ == "__main__":
    main()
