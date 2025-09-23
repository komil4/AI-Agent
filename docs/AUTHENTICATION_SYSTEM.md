# Система аутентификации MCP Chat

## Обзор

MCP Chat использует гибридную систему аутентификации, которая поддерживает как локальных пользователей (с паролями в PostgreSQL), так и LDAP пользователей (через Active Directory).

## Архитектура аутентификации

### Приоритет проверки

1. **Локальная аутентификация** - проверка в таблице `users` PostgreSQL
2. **LDAP аутентификация** - проверка через Active Directory (если включен)

### Типы пользователей

- **Локальные пользователи** (`is_ldap_user = false`) - пароли хранятся в БД
- **LDAP пользователи** (`is_ldap_user = true`) - аутентификация через AD

## Структура таблицы users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),           -- Хеш пароля для локальных пользователей
    display_name VARCHAR(200),
    email VARCHAR(200),
    groups TEXT[],
    is_admin BOOLEAN DEFAULT FALSE,
    is_ldap_user BOOLEAN DEFAULT FALSE,  -- Флаг LDAP пользователя
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

## Процесс аутентификации

### Шаг 1: Локальная проверка

```python
# Проверяем локального пользователя в БД
db_user = chat_service.authenticate_local_user(username, password)
```

**Условия успешной локальной аутентификации:**
- Пользователь существует в таблице `users`
- `is_ldap_user = false`
- `password_hash` не пустой
- Пароль совпадает с хешем

### Шаг 2: LDAP проверка (если локальная не удалась)

```python
# Проверяем LDAP только если локальная аутентификация не удалась
if not db_user and ldap_enabled:
    ldap_user_info = ad_auth.authenticate_user(username, password)
```

**Условия LDAP аутентификации:**
- LDAP включен в конфигурации (`active_directory.enabled = true`)
- Пользователь найден в Active Directory
- Пароль корректный

### Шаг 3: Создание/обновление пользователя

```python
# Если LDAP аутентификация успешна, создаем/обновляем пользователя в БД
if ldap_user_info:
    ldap_user_info['is_ldap_user'] = True
    db_user = chat_service.get_or_create_user(username, ldap_user_info)
```

## Создание локальных пользователей

### Через утилиту командной строки

```bash
# Создать пользователя
python scripts/create_local_user.py create

# Показать список пользователей
python scripts/create_local_user.py list
```

### Программно

```python
from chat_service import ChatService

chat_service = ChatService()

# Хешируем пароль
password_hash = chat_service.hash_password("user_password")

# Создаем пользователя
user_info = {
    'username': 'local_user',
    'password_hash': password_hash,
    'display_name': 'Local User',
    'email': 'user@company.com',
    'groups': [],
    'is_admin': False,
    'is_ldap_user': False
}

user = chat_service.get_or_create_user('local_user', user_info)
```

## Миграция существующих данных

### Добавление новых полей

```bash
# Выполните миграцию для добавления новых полей
docker exec -i postgres-server psql -U mcp_user -d mcp_chat < migrate_add_password_fields.sql
```

### Обновление существующих пользователей

```sql
-- Пометить существующих пользователей как локальных
UPDATE users 
SET is_ldap_user = FALSE 
WHERE is_ldap_user IS NULL;

-- Создать пароль для пользователя admin (если нужно)
UPDATE users 
SET password_hash = '$2b$12$...'  -- замените на реальный хеш
WHERE username = 'admin';
```

## Конфигурация

### Локальные пользователи

Локальные пользователи создаются через:
- Утилиту командной строки
- Админ-панель (если реализована)
- Программно через API

### LDAP пользователи

LDAP настраивается в `app_config.json`:

```json
{
  "active_directory": {
    "server": "ldap.company.com",
    "domain": "company.com",
    "base_dn": "OU=Users,DC=company,DC=com",
    "service_user": "service_account",
    "service_password": "service_password",
    "enabled": true
  }
}
```

## Безопасность

### Хеширование паролей

- Используется bcrypt с солью
- Автоматическая генерация соли
- Защита от rainbow table атак

### Проверка паролей

```python
# Проверка пароля
is_valid = chat_service.verify_password(plain_password, hashed_password)
```

### Сессии

- JWT токены с истечением срока действия
- HttpOnly cookies для безопасности
- Обновление времени последнего входа

## Логирование

### Успешная локальная аутентификация

```
🔍 Попытка входа пользователя: local_user
📋 Проверяем локальную аутентификацию в БД...
✅ Локальная аутентификация успешна: local_user
```

### Успешная LDAP аутентификация

```
🔍 Попытка входа пользователя: ldap_user
📋 Проверяем локальную аутентификацию в БД...
🔍 Локальная аутентификация не удалась, проверяем LDAP...
🌐 Проверяем аутентификацию через LDAP...
✅ LDAP аутентификация успешна: ldap_user
💾 Создаем/обновляем LDAP пользователя в БД: ldap_user
✅ LDAP пользователь создан/обновлен в БД: 123
```

### Неудачная аутентификация

```
🔍 Попытка входа пользователя: unknown_user
📋 Проверяем локальную аутентификацию в БД...
❌ Неверные учетные данные для локального пользователя: unknown_user
🔍 Локальная аутентификация не удалась, проверяем LDAP...
❌ LDAP аутентификация не удалась для: unknown_user
```

## API эндпоинты

### POST /api/auth/login

**Запрос:**
```json
{
  "username": "user",
  "password": "password"
}
```

**Ответ (успех):**
```json
{
  "success": true,
  "message": "Успешная локальная аутентификация",
  "user_info": {
    "username": "user",
    "display_name": "User Name",
    "email": "user@company.com",
    "groups": [],
    "is_admin": false
  }
}
```

**Ответ (ошибка):**
```json
{
  "success": false,
  "message": "Неверные учетные данные"
}
```

## Устранение неполадок

### Пользователь не может войти

1. **Проверьте логи аутентификации**
2. **Проверьте тип пользователя:**
   ```sql
   SELECT username, is_ldap_user, password_hash IS NOT NULL as has_password
   FROM users WHERE username = 'problematic_user';
   ```

3. **Для локальных пользователей проверьте пароль:**
   ```python
   chat_service.verify_password("password", user.password_hash)
   ```

4. **Для LDAP пользователей проверьте конфигурацию AD**

### LDAP не работает

1. **Проверьте конфигурацию:**
   ```json
   {
     "active_directory": {
       "enabled": true,
       "server": "correct_server",
       "domain": "correct_domain"
     }
   }
   ```

2. **Проверьте подключение к AD серверу**
3. **Проверьте права доступа service account**

### Миграция данных

1. **Выполните миграцию полей:**
   ```bash
   docker exec -i postgres-server psql -U mcp_user -d mcp_chat < migrate_add_password_fields.sql
   ```

2. **Создайте пароли для существующих пользователей:**
   ```python
   python scripts/create_local_user.py create
   ```

## Мониторинг

### Статистика аутентификации

```sql
SELECT 
    is_ldap_user,
    COUNT(*) as user_count,
    COUNT(CASE WHEN last_login IS NOT NULL THEN 1 END) as active_users
FROM users 
GROUP BY is_ldap_user;
```

### Последние входы

```sql
SELECT 
    username,
    is_ldap_user,
    last_login
FROM users 
WHERE last_login IS NOT NULL
ORDER BY last_login DESC
LIMIT 10;
```
