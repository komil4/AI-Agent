# Настройка pgAdmin для управления PostgreSQL

## Обзор

pgAdmin - это веб-интерфейс для управления PostgreSQL базами данных. Добавлен в Docker Compose для удобного администрирования базы данных MCP Chat.

## Запуск pgAdmin

### Автоматический запуск с остальными сервисами

```bash
docker-compose up -d
```

### Только pgAdmin

```bash
docker-compose up -d pgadmin
```

## Доступ к pgAdmin

- **URL:** http://localhost:8080
- **Email:** admin@mcp.local
- **Пароль:** admin123

## Настройка подключения к PostgreSQL

### 1. Войдите в pgAdmin

Откройте браузер и перейдите по адресу http://localhost:8080

### 2. Добавьте новый сервер

1. Щелкните правой кнопкой мыши на "Servers" в левой панели
2. Выберите "Register" → "Server..."

### 3. Заполните данные подключения

**General Tab:**
- **Name:** MCP Chat Database

**Connection Tab:**
- **Host name/address:** postgres-server
- **Port:** 5432
- **Maintenance database:** mcp_chat
- **Username:** mcp_user
- **Password:** mcp_password

**Advanced Tab:**
- **DB restriction:** mcp_chat (опционально)

### 4. Сохраните подключение

Нажмите "Save" для сохранения настроек подключения.

## Основные функции

### Просмотр структуры базы данных

1. Разверните "MCP Chat Database" → "Databases" → "mcp_chat" → "Schemas" → "public" → "Tables"
2. Вы увидите все таблицы:
   - `users` - пользователи
   - `chat_sessions` - сессии чата
   - `messages` - сообщения
   - `tool_usage` - использование инструментов

### Выполнение SQL запросов

1. Щелкните правой кнопкой на базе данных "mcp_chat"
2. Выберите "Query Tool"
3. Введите SQL запросы и нажмите F5 для выполнения

### Полезные SQL запросы

#### Просмотр всех пользователей
```sql
SELECT * FROM users ORDER BY created_at DESC;
```

#### Просмотр активных сессий
```sql
SELECT s.*, u.username 
FROM chat_sessions s 
JOIN users u ON s.user_id = u.id 
WHERE s.is_active = true 
ORDER BY s.updated_at DESC;
```

#### Просмотр последних сообщений
```sql
SELECT m.*, u.username, s.session_name
FROM messages m
JOIN users u ON m.user_id = u.id
JOIN chat_sessions s ON m.session_id = s.id
ORDER BY m.created_at DESC
LIMIT 50;
```

#### Статистика по пользователям
```sql
SELECT 
    u.username,
    COUNT(DISTINCT s.id) as sessions_count,
    COUNT(m.id) as messages_count,
    MAX(m.created_at) as last_activity
FROM users u
LEFT JOIN chat_sessions s ON u.id = s.user_id
LEFT JOIN messages m ON s.id = m.session_id
GROUP BY u.id, u.username
ORDER BY messages_count DESC;
```

#### Размер базы данных
```sql
SELECT pg_size_pretty(pg_database_size('mcp_chat'));
```

#### Размер таблиц
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Резервное копирование

#### Создание бэкапа через pgAdmin

1. Щелкните правой кнопкой на базе данных "mcp_chat"
2. Выберите "Backup..."
3. Укажите путь для сохранения файла
4. Нажмите "Backup"

#### Создание бэкапа через командную строку

```bash
docker exec postgres-server pg_dump -U mcp_user mcp_chat > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
docker exec -i postgres-server psql -U mcp_user -d mcp_chat < backup_file.sql
```

## Мониторинг

### Активные подключения
```sql
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    query
FROM pg_stat_activity 
WHERE datname = 'mcp_chat';
```

### Статистика производительности
```sql
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;
```

## Безопасность

### Изменение паролей по умолчанию

Для production среды рекомендуется изменить пароли:

1. **pgAdmin пароль:**
   ```bash
   # Остановите контейнер
   docker-compose stop pgadmin
   
   # Измените переменные окружения в docker-compose.yml
   PGADMIN_DEFAULT_PASSWORD=your_secure_password
   
   # Запустите заново
   docker-compose up -d pgadmin
   ```

2. **PostgreSQL пароль:**
   ```bash
   # Подключитесь к PostgreSQL
   docker exec -it postgres-server psql -U mcp_user -d mcp_chat
   
   # Измените пароль
   ALTER USER mcp_user PASSWORD 'your_new_password';
   ```

### Ограничение доступа

В production среде рекомендуется:

1. Изменить порт pgAdmin с 8080 на нестандартный
2. Использовать reverse proxy с SSL
3. Ограничить доступ по IP адресам
4. Регулярно обновлять пароли

## Устранение неполадок

### pgAdmin не запускается

```bash
# Проверьте логи
docker logs pgadmin-server

# Проверьте статус контейнера
docker ps | grep pgadmin
```

### Не удается подключиться к PostgreSQL

```bash
# Проверьте, что PostgreSQL запущен
docker exec postgres-server pg_isready -U mcp_user -d mcp_chat

# Проверьте сеть между контейнерами
docker network ls
docker network inspect mcp_default
```

### Очистка данных pgAdmin

```bash
# Остановите pgAdmin
docker-compose stop pgadmin

# Удалите том с данными
docker volume rm mcp_pgadmin_data

# Запустите заново
docker-compose up -d pgadmin
```
