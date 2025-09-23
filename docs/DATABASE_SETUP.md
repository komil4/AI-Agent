# Настройка базы данных PostgreSQL

## Обзор

MCP Chat использует PostgreSQL для хранения истории чата, пользователей и статистики использования инструментов.

## Структура базы данных

### Таблицы

1. **users** - Пользователи системы
   - `id` - Уникальный идентификатор
   - `username` - Имя пользователя
   - `display_name` - Отображаемое имя
   - `email` - Email адрес
   - `groups` - Группы пользователя
   - `is_admin` - Флаг администратора
   - `created_at` - Дата создания
   - `last_login` - Последний вход

2. **chat_sessions** - Сессии чата
   - `id` - Уникальный идентификатор
   - `user_id` - Ссылка на пользователя
   - `session_name` - Название сессии
   - `created_at` - Дата создания
   - `updated_at` - Дата обновления
   - `is_active` - Активна ли сессия

3. **messages** - Сообщения
   - `id` - Уникальный идентификатор
   - `session_id` - Ссылка на сессию
   - `user_id` - Ссылка на пользователя
   - `message_type` - Тип сообщения (user/assistant/system)
   - `content` - Содержимое сообщения
   - `metadata` - Дополнительные данные (JSON)
   - `created_at` - Дата создания

4. **tool_usage** - Использование инструментов
   - `id` - Уникальный идентификатор
   - `message_id` - Ссылка на сообщение
   - `tool_name` - Название инструмента
   - `server_name` - Название сервера
   - `arguments` - Аргументы вызова (JSON)
   - `result` - Результат выполнения (JSON)
   - `execution_time_ms` - Время выполнения в миллисекундах
   - `created_at` - Дата создания

## Запуск с базой данных

### Автоматический запуск

Используйте готовые скрипты:

**Windows:**
```bash
scripts/start_with_db.bat
```

**Linux/macOS:**
```bash
scripts/start_with_db.sh
```

### Ручной запуск

1. **Запуск контейнеров:**
```bash
docker-compose up -d
```

2. **Проверка статуса:**
```bash
docker ps
```

3. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

4. **Запуск приложения:**
```bash
python app.py
```

## Конфигурация

### Настройки базы данных

В админ-панели доступны следующие настройки:

- **Хост** - Адрес сервера PostgreSQL (по умолчанию: localhost)
- **Порт** - Порт подключения (по умолчанию: 5432)
- **База данных** - Название базы данных (по умолчанию: mcp_chat)
- **Пользователь** - Имя пользователя (по умолчанию: mcp_user)
- **Пароль** - Пароль пользователя (по умолчанию: mcp_password)
- **Включена** - Включить/выключить использование базы данных

### Переменные окружения

Можно использовать переменные окружения:

```bash
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=mcp_chat
export DATABASE_USER=mcp_user
export DATABASE_PASSWORD=mcp_password
```

## API для работы с историей

### Получение сессий пользователя

```http
GET /api/chat/sessions
```

**Ответ:**
```json
{
  "sessions": [
    {
      "id": 1,
      "name": "Сессия 2024-01-15 10:30",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T11:45:00",
      "is_active": true
    }
  ]
}
```

### Получение истории сессии

```http
GET /api/chat/sessions/{session_id}/history
```

**Ответ:**
```json
{
  "history": [
    {
      "id": 1,
      "type": "user",
      "content": "Привет!",
      "created_at": "2024-01-15T10:30:00",
      "metadata": {},
      "tools": []
    },
    {
      "id": 2,
      "type": "assistant",
      "content": "Привет! Чем могу помочь?",
      "created_at": "2024-01-15T10:30:05",
      "metadata": {},
      "tools": []
    }
  ]
}
```

### Закрытие сессии

```http
POST /api/chat/sessions/{session_id}/close
```

### Получение статистики пользователя

```http
GET /api/chat/stats
```

**Ответ:**
```json
{
  "sessions_count": 5,
  "messages_count": 150,
  "tools_count": 25,
  "last_activity": "2024-01-15T11:45:00"
}
```

## Управление базой данных

### Подключение к PostgreSQL

```bash
docker exec -it postgres-server psql -U mcp_user -d mcp_chat
```

### Резервное копирование

```bash
docker exec postgres-server pg_dump -U mcp_user mcp_chat > backup.sql
```

### Восстановление

```bash
docker exec -i postgres-server psql -U mcp_user -d mcp_chat < backup.sql
```

### Очистка старых данных

```sql
-- Удаление сообщений старше 30 дней
DELETE FROM messages WHERE created_at < NOW() - INTERVAL '30 days';

-- Удаление закрытых сессий старше 90 дней
DELETE FROM chat_sessions WHERE is_active = false AND updated_at < NOW() - INTERVAL '90 days';
```

## Мониторинг

### Проверка статуса

```bash
docker exec postgres-server pg_isready -U mcp_user -d mcp_chat
```

### Размер базы данных

```sql
SELECT pg_size_pretty(pg_database_size('mcp_chat'));
```

### Статистика таблиц

```sql
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
```

## Безопасность

### Рекомендации

1. **Измените пароли по умолчанию** в production среде
2. **Используйте SSL** для подключения к базе данных
3. **Ограничьте доступ** к порту 5432 только для приложения
4. **Регулярно создавайте резервные копии**
5. **Мониторьте использование ресурсов**

### Настройка SSL

Добавьте в `docker-compose.yml`:

```yaml
postgres:
  environment:
    - POSTGRES_SSLMODE=require
  volumes:
    - ./ssl:/var/lib/postgresql/ssl
```

## Устранение неполадок

### Проблемы с подключением

1. **Проверьте статус контейнера:**
```bash
docker ps | grep postgres
```

2. **Проверьте логи:**
```bash
docker logs postgres-server
```

3. **Проверьте сеть:**
```bash
docker network ls
```

### Проблемы с производительностью

1. **Проверьте использование ресурсов:**
```bash
docker stats postgres-server
```

2. **Оптимизируйте запросы:**
```sql
EXPLAIN ANALYZE SELECT * FROM messages WHERE session_id = 1;
```

3. **Настройте индексы:**
```sql
CREATE INDEX CONCURRENTLY idx_messages_session_created ON messages(session_id, created_at);
```
