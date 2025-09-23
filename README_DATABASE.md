# MCP Chat с PostgreSQL

## Быстрый старт

### 1. Запуск с базой данных

**Windows:**
```bash
scripts/start_with_db.bat
```

**Linux/macOS:**
```bash
scripts/start_with_db.sh
```

### 2. Ручной запуск

```bash
# Запуск контейнеров
docker-compose up -d

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python app.py
```

## Что добавлено

### 🗄️ База данных PostgreSQL
- **Контейнер**: `postgres-server` (порт 5432)
- **База данных**: `mcp_chat`
- **Пользователь**: `mcp_user`
- **Пароль**: `mcp_password`

### 📊 Таблицы
- **users** - Пользователи системы
- **chat_sessions** - Сессии чата
- **messages** - Сообщения пользователей и ассистента
- **tool_usage** - Использование инструментов

### 🔧 API для истории
- `GET /api/chat/sessions` - Список сессий
- `GET /api/chat/sessions/{id}/history` - История сессии
- `POST /api/chat/sessions/{id}/close` - Закрытие сессии
- `GET /api/chat/stats` - Статистика пользователя

### ⚙️ Админ-панель
- Настройки базы данных
- Управление подключением
- Мониторинг статуса

## Конфигурация

### Настройки по умолчанию
```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "mcp_chat",
    "username": "mcp_user",
    "password": "mcp_password",
    "enabled": true
  }
}
```

### Изменение пароля
1. Откройте админ-панель: `http://localhost:5000/admin`
2. Перейдите в раздел "База данных"
3. Измените пароль
4. Сохраните настройки

## Безопасность

⚠️ **Важно**: Измените пароли по умолчанию в production среде!

### Рекомендуемые изменения
1. Измените пароль базы данных
2. Ограничьте доступ к порту 5432
3. Используйте SSL для подключения
4. Регулярно создавайте резервные копии

## Мониторинг

### Проверка статуса
```bash
# Статус контейнеров
docker ps

# Проверка PostgreSQL
docker exec postgres-server pg_isready -U mcp_user -d mcp_chat

# Логи PostgreSQL
docker logs postgres-server
```

### Подключение к базе
```bash
docker exec -it postgres-server psql -U mcp_user -d mcp_chat
```

## Резервное копирование

### Создание бэкапа
```bash
docker exec postgres-server pg_dump -U mcp_user mcp_chat > backup.sql
```

### Восстановление
```bash
docker exec -i postgres-server psql -U mcp_user -d mcp_chat < backup.sql
```

## Устранение неполадок

### Проблемы с подключением
1. Проверьте статус контейнера: `docker ps`
2. Проверьте логи: `docker logs postgres-server`
3. Убедитесь, что порт 5432 свободен

### Проблемы с производительностью
1. Мониторьте ресурсы: `docker stats postgres-server`
2. Проверьте размер базы: `SELECT pg_size_pretty(pg_database_size('mcp_chat'));`
3. Оптимизируйте запросы и индексы

## Дополнительная документация

- [Полная документация по базе данных](docs/DATABASE_SETUP.md)
- [Структура проекта](docs/PROJECT_STRUCTURE.md)
- [Настройка MCP серверов](docs/MCP_SETUP.md)
