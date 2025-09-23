# Управление сессиями SQLAlchemy в MCP Chat

## Проблема DetachedInstanceError

### Описание ошибки

```
DetachedInstanceError('Instance <Message at 0x22a9fb36f90> is not bound to a Session; attribute refresh operation cannot proceed')
```

Эта ошибка возникает, когда объект SQLAlchemy используется вне контекста сессии базы данных.

### Причины возникновения

1. **Объект возвращается из контекста `with get_db()`**
2. **Контекст закрывается, объект становится "отсоединенным"**
3. **Попытка доступа к атрибутам объекта вне сессии**

### Пример проблемного кода

```python
def add_message(self, session_id: int, user_id: int, message_type: str, 
               content: str, metadata: Dict[str, Any] = None) -> Message:
    with get_db() as session:  # Сессия открывается
        message = Message(...)
        session.add(message)
        session.commit()
        session.refresh(message)
        return message  # ❌ Объект возвращается из контекста
    # Сессия закрывается, объект становится отсоединенным
```

## Решения

### Решение 1: Использование session.expunge()

```python
def add_message(self, session_id: int, user_id: int, message_type: str, 
               content: str, metadata: Dict[str, Any] = None) -> Message:
    with get_db() as session:
        message = Message(...)
        session.add(message)
        session.commit()
        session.refresh(message)
        
        # Отсоединяем объект от сессии
        session.expunge(message)
        
        return message  # ✅ Объект можно использовать вне сессии
```

### Решение 2: Возврат данных вместо объектов

```python
def add_message(self, session_id: int, user_id: int, message_type: str, 
               content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    with get_db() as session:
        message = Message(...)
        session.add(message)
        session.commit()
        session.refresh(message)
        
        # Отсоединяем объект от сессии
        session.expunge(message)
        
        # Возвращаем данные вместо объекта
        return {
            'id': message.id,
            'session_id': message.session_id,
            'user_id': message.user_id,
            'message_type': message.message_type,
            'content': message.content,
            'message_metadata': message.message_metadata,
            'created_at': message.created_at
        }
```

## Реализованные исправления

### ChatService методы

#### 1. `add_message()`
- **Было:** Возвращал объект `Message`
- **Стало:** Возвращает словарь с данными
- **Исправление:** `session.expunge(message)` + возврат данных

#### 2. `get_session_messages()`
- **Было:** Возвращал список объектов `Message`
- **Стало:** Возвращает список словарей
- **Исправление:** `session.expunge()` для каждого объекта

#### 3. `add_tool_usage()`
- **Было:** Возвращал объект `ToolUsage`
- **Стало:** Возвращает словарь с данными
- **Исправление:** `session.expunge(tool_usage)` + возврат данных

#### 4. `get_session_history()`
- **Было:** Использовал связанные объекты
- **Стало:** Отдельные запросы для инструментов
- **Исправление:** `session.expunge()` для всех объектов

#### 5. `get_or_create_user()`
- **Было:** Возвращал объект `User`
- **Стало:** Возвращает объект `User` (отсоединенный)
- **Исправление:** `session.expunge(user)`

#### 6. `create_chat_session()`
- **Было:** Возвращал объект `ChatSession`
- **Стало:** Возвращает объект `ChatSession` (отсоединенный)
- **Исправление:** `session.expunge(chat_session)`

#### 7. `get_active_session()`
- **Было:** Возвращал объект `ChatSession`
- **Стало:** Возвращает объект `ChatSession` (отсоединенный)
- **Исправление:** `session.expunge(chat_session)`

#### 8. `get_user_sessions()`
- **Было:** Возвращал список объектов `ChatSession`
- **Стало:** Возвращает список объектов `ChatSession` (отсоединенных)
- **Исправление:** `session.expunge()` для каждого объекта

### Обновления в app.py

#### Использование add_message

**Было:**
```python
user_message_obj = chat_service.add_message(...)
logger.info(f"✅ Сообщение пользователя сохранено: {user_message_obj.id}")
```

**Стало:**
```python
user_message_data = chat_service.add_message(...)
logger.info(f"✅ Сообщение пользователя сохранено: {user_message_data['id']}")
```

## Лучшие практики

### 1. Всегда используйте session.expunge()

```python
with get_db() as session:
    obj = session.query(Model).first()
    session.expunge(obj)  # Отсоединяем объект
    return obj  # Безопасно использовать вне сессии
```

### 2. Возвращайте данные вместо объектов

```python
def get_user_data(self, user_id: int) -> Dict[str, Any]:
    with get_db() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.expunge(user)
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        return None
```

### 3. Избегайте ленивой загрузки

```python
# ❌ Плохо - может вызвать DetachedInstanceError
def get_user_with_sessions(self, user_id: int):
    with get_db() as session:
        user = session.query(User).filter(User.id == user_id).first()
        session.expunge(user)
        return user  # user.sessions может вызвать ошибку

# ✅ Хорошо - явная загрузка
def get_user_with_sessions(self, user_id: int):
    with get_db() as session:
        user = session.query(User).options(joinedload(User.sessions)).filter(User.id == user_id).first()
        session.expunge(user)
        return user
```

### 4. Используйте session.merge() для обновления

```python
def update_user(self, user_data: Dict[str, Any]):
    with get_db() as session:
        # Если объект отсоединен, используем merge
        user = session.merge(User(**user_data))
        session.commit()
        session.expunge(user)
        return user
```

## Отладка DetachedInstanceError

### 1. Проверьте стек вызовов

```python
try:
    # Код, вызывающий ошибку
    pass
except DetachedInstanceError as e:
    import traceback
    traceback.print_exc()
    print(f"Объект отсоединен от сессии: {e}")
```

### 2. Проверьте состояние объекта

```python
from sqlalchemy.orm import object_session

obj = some_query()
session = object_session(obj)
if session is None:
    print("Объект отсоединен от сессии")
else:
    print("Объект привязан к сессии")
```

### 3. Используйте session.refresh()

```python
with get_db() as session:
    obj = session.query(Model).first()
    session.refresh(obj)  # Обновляем данные объекта
    session.expunge(obj)
    return obj
```

## Мониторинг

### Логирование сессий

```python
import logging
from sqlalchemy.orm import object_session

logger = logging.getLogger(__name__)

def log_object_session(obj, operation: str):
    session = object_session(obj)
    if session is None:
        logger.warning(f"Объект {obj} отсоединен от сессии при операции {operation}")
    else:
        logger.debug(f"Объект {obj} привязан к сессии при операции {operation}")
```

### Проверка в тестах

```python
def test_no_detached_instances():
    """Тест на отсутствие отсоединенных объектов"""
    with get_db() as session:
        users = chat_service.get_user_sessions(1)
        
        for user in users:
            session_state = object_session(user)
            assert session_state is None, f"Объект {user} не должен быть привязан к сессии"
```

## Заключение

Исправление `DetachedInstanceError` требует:

1. **Понимания жизненного цикла объектов SQLAlchemy**
2. **Правильного использования `session.expunge()`**
3. **Возврата данных вместо объектов где это возможно**
4. **Избегания ленивой загрузки вне сессии**

Реализованные исправления обеспечивают стабильную работу с базой данных без ошибок отсоединения объектов.
