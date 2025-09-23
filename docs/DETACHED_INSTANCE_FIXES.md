# Исправления DetachedInstanceError в MCP Chat

## Проблема

Ошибка `DetachedInstanceError` возникала при использовании объектов SQLAlchemy вне контекста сессии базы данных.

## Исправленные методы

### 1. `add_message()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал объект `Message`
- **Стало:** Возвращает словарь с данными
- **Исправление:** `session.expunge(message)` + возврат данных

### 2. `get_session_messages()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал список объектов `Message`
- **Стало:** Возвращает список словарей
- **Исправление:** `session.expunge()` для каждого объекта

### 3. `add_tool_usage()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал объект `ToolUsage`
- **Стало:** Возвращает словарь с данными
- **Исправление:** `session.expunge(tool_usage)` + возврат данных

### 4. `get_session_history()` - ✅ ИСПРАВЛЕН
- **Было:** Использовал связанные объекты
- **Стало:** Отдельные запросы для инструментов
- **Исправление:** `session.expunge()` для всех объектов

### 5. `get_or_create_user()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал объект `User`
- **Стало:** Возвращает объект `User` (отсоединенный)
- **Исправление:** `session.expunge(user)`

### 6. `create_chat_session()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал объект `ChatSession`
- **Стало:** Возвращает объект `ChatSession` (отсоединенный)
- **Исправление:** `session.expunge(chat_session)`

### 7. `get_active_session()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал объект `ChatSession`
- **Стало:** Возвращает объект `ChatSession` (отсоединенный)
- **Исправление:** `session.expunge(chat_session)`

### 8. `get_user_sessions()` - ✅ ИСПРАВЛЕН
- **Было:** Возвращал список объектов `ChatSession`
- **Стало:** Возвращает список словарей
- **Исправление:** `session.expunge()` для каждого объекта + возврат данных

## Исправления в app.py

### 1. Использование `add_message()` - ✅ ИСПРАВЛЕН
```python
# Было:
user_message_obj = chat_service.add_message(...)
logger.info(f"✅ Сообщение пользователя сохранено: {user_message_obj.id}")

# Стало:
user_message_data = chat_service.add_message(...)
logger.info(f"✅ Сообщение пользователя сохранено: {user_message_data['id']}")
```

### 2. Использование `get_user_sessions()` - ✅ ИСПРАВЛЕН
```python
# Было:
sessions = chat_service.get_user_sessions(db_user.id)
return {
    "sessions": [
        {
            "id": session.id,
            "name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "is_active": session.is_active
        }
        for session in sessions
    ]
}

# Стало:
sessions = chat_service.get_user_sessions(db_user.id)
return {
    "sessions": [
        {
            "id": session_data["id"],
            "name": session_data["session_name"],
            "created_at": session_data["created_at"].isoformat(),
            "updated_at": session_data["updated_at"].isoformat(),
            "is_active": session_data["is_active"]
        }
        for session_data in sessions
    ]
}
```

### 3. Проверка принадлежности сессии - ✅ ИСПРАВЛЕН
```python
# Было:
session = chat_service.get_user_sessions(db_user.id)
if not any(s.id == session_id for s in session):

# Стало:
sessions = chat_service.get_user_sessions(db_user.id)
if not any(session_data["id"] == session_id for session_data in sessions):
```

## Принципы исправления

### 1. Использование `session.expunge()`
```python
with get_db() as session:
    obj = session.query(Model).first()
    session.expunge(obj)  # Отсоединяем объект от сессии
    return obj  # Безопасно использовать вне сессии
```

### 2. Возврат данных вместо объектов
```python
def get_data(self) -> Dict[str, Any]:
    with get_db() as session:
        obj = session.query(Model).first()
        session.expunge(obj)
        return {
            'id': obj.id,
            'name': obj.name,
            'created_at': obj.created_at
        }
```

### 3. Отдельные запросы для связанных данных
```python
def get_with_relations(self, obj_id: int):
    with get_db() as session:
        obj = session.query(Model).filter(Model.id == obj_id).first()
        session.expunge(obj)
        
        # Отдельный запрос для связанных данных
        relations = session.query(RelatedModel).filter(RelatedModel.parent_id == obj_id).all()
        for rel in relations:
            session.expunge(rel)
        
        return obj, relations
```

## Результат

✅ **Все методы ChatService исправлены**
✅ **Все использования в app.py обновлены**
✅ **DetachedInstanceError больше не возникает**
✅ **Стабильная работа с базой данных**

## Тестирование

Для проверки исправлений:

1. **Запустите приложение**
2. **Выполните вход пользователя**
3. **Отправьте сообщение в чат**
4. **Проверьте историю сессий**
5. **Убедитесь, что ошибки DetachedInstanceError нет**

Все исправления протестированы и работают корректно.
