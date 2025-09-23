# Управление пользователями LDAP в MCP Chat

## Обзор

MCP Chat автоматически создает и управляет пользователями LDAP в базе данных PostgreSQL при их первом входе в систему. Это обеспечивает интеграцию между Active Directory и внутренней системой управления пользователями.

## Автоматическое создание пользователей

### При первом входе LDAP пользователя

Когда пользователь LDAP впервые входит в систему:

1. **Аутентификация через Active Directory** - проверяются учетные данные
2. **Получение информации из AD** - извлекаются данные пользователя:
   - `username` (sAMAccountName)
   - `display_name` (displayName)
   - `email` (mail)
   - `groups` (memberOf)
3. **Создание записи в БД** - пользователь добавляется в таблицу `users`
4. **Создание сессии** - создается JWT токен и сессия

### При повторном входе

При последующих входах:

1. **Аутентификация через AD** - проверка учетных данных
2. **Обновление данных** - информация пользователя обновляется в БД
3. **Обновление last_login** - фиксируется время последнего входа

## Структура данных пользователя

### Таблица `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    email VARCHAR(200),
    groups TEXT[],
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Маппинг LDAP → Database

| LDAP атрибут | Database поле | Описание |
|--------------|---------------|----------|
| `sAMAccountName` | `username` | Уникальное имя пользователя |
| `displayName` | `display_name` | Отображаемое имя |
| `mail` | `email` | Email адрес |
| `memberOf` | `groups` | Массив групп AD |
| - | `is_admin` | Флаг администратора (по умолчанию false) |
| - | `created_at` | Время создания записи |
| - | `last_login` | Время последнего входа |

## Управление сессиями чата

### Автоматическое создание сессий

При первом обращении к чату:

1. **Проверка активной сессии** - ищется активная сессия пользователя
2. **Создание новой сессии** - если активной нет, создается новая
3. **Сохранение сообщений** - все сообщения привязываются к сессии

### Таблица `chat_sessions`

```sql
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

## Логирование

### Создание пользователя

```
✅ Создан новый пользователь: ivanov (ID: 5)
   Display Name: Иванов Иван Иванович
   Email: ivanov@company.com
   Groups: ['CN=Developers,OU=Groups,DC=company,DC=com']
   Is Admin: False
```

### Обновление пользователя

```
✅ Обновлен пользователь: ivanov (ID: 5)
   Изменения: display_name: 'Иванов И.И.' -> 'Иванов Иван Иванович', groups: [] -> ['CN=Developers,OU=Groups,DC=company,DC=com']
```

### Только обновление времени входа

```
✅ Обновлен пользователь: ivanov (ID: 5) - только last_login
```

## API для работы с пользователями

### Получение информации о текущем пользователе

```http
GET /api/user/profile
```

**Ответ:**
```json
{
  "username": "ivanov",
  "display_name": "Иванов Иван Иванович",
  "email": "ivanov@company.com",
  "groups": ["CN=Developers,OU=Groups,DC=company,DC=com"],
  "is_admin": false,
  "created_at": "2024-01-15T10:30:00",
  "last_login": "2024-01-15T14:20:00"
}
```

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

## Администрирование

### Просмотр всех пользователей через pgAdmin

```sql
SELECT 
    id,
    username,
    display_name,
    email,
    groups,
    is_admin,
    created_at,
    last_login
FROM users 
ORDER BY created_at DESC;
```

### Статистика пользователей

```sql
SELECT 
    username,
    display_name,
    COUNT(DISTINCT s.id) as sessions_count,
    COUNT(m.id) as messages_count,
    MAX(m.created_at) as last_activity,
    last_login
FROM users u
LEFT JOIN chat_sessions s ON u.id = s.user_id
LEFT JOIN messages m ON s.id = m.session_id
GROUP BY u.id, u.username, u.display_name, u.last_login
ORDER BY last_activity DESC;
```

### Поиск пользователей по группам

```sql
SELECT username, display_name, groups
FROM users 
WHERE 'Developers' = ANY(groups);
```

## Безопасность

### Проверка прав доступа

Система автоматически проверяет группы пользователя для:

- Доступа к административным функциям
- Доступа к определенным MCP серверам
- Доступа к API эндпоинтам

### Пример проверки групп

```python
# В коде приложения
user_groups = user_info.get('groups', [])
if any('Admin' in group for group in user_groups):
    # Пользователь имеет права администратора
    pass
```

## Устранение неполадок

### Пользователь не создается в БД

1. **Проверьте логи аутентификации:**
   ```
   🔍 Создаем/обновляем пользователя LDAP в БД: username
   ✅ Пользователь LDAP создан/обновлен в БД: 123
   ```

2. **Проверьте подключение к БД:**
   ```bash
   docker exec postgres-server pg_isready -U mcp_user -d mcp_chat
   ```

3. **Проверьте таблицу users:**
   ```sql
   SELECT * FROM users WHERE username = 'problematic_user';
   ```

### Сессии не создаются

1. **Проверьте активную сессию:**
   ```sql
   SELECT * FROM chat_sessions WHERE user_id = 123 AND is_active = true;
   ```

2. **Проверьте логи чата:**
   ```
   ✅ Используется существующая сессия: 456
   или
   ✅ Создана новая сессия: 456
   ```

### Проблемы с группами LDAP

1. **Проверьте формат групп в БД:**
   ```sql
   SELECT username, groups FROM users WHERE username = 'test_user';
   ```

2. **Проверьте логи AD аутентификации:**
   ```
   Groups: ['CN=Developers,OU=Groups,DC=company,DC=com']
   ```

## Мониторинг

### Активные пользователи

```sql
SELECT 
    username,
    display_name,
    last_login,
    COUNT(DISTINCT s.id) as active_sessions
FROM users u
LEFT JOIN chat_sessions s ON u.id = s.user_id AND s.is_active = true
WHERE last_login > NOW() - INTERVAL '24 hours'
GROUP BY u.id, u.username, u.display_name, u.last_login
ORDER BY last_login DESC;
```

### Статистика входов

```sql
SELECT 
    DATE(last_login) as login_date,
    COUNT(*) as unique_users
FROM users 
WHERE last_login IS NOT NULL
GROUP BY DATE(last_login)
ORDER BY login_date DESC;
```
