# Исправление методов проверки здоровья MCP серверов

## 🔍 Проблема

**Ошибка:** MCP серверы не могли вернуть состояние `is_enabled` и `check_health` в строке 211 `mcp_client.py`

**Причина:** MCP серверы не имели методов `check_health()`, а код пытался обращаться к несуществующим методам.

## 🛠️ Исправления

### **1. Добавлен метод `get_health_status()` в `BaseFastMCPServer`**

```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья сервера"""
    try:
        is_enabled = self.is_enabled()
        is_connected = self.test_connection()
        
        if not is_enabled:
            return {
                'status': 'disabled',
                'provider': self.server_name,
                'message': 'Сервер отключен в конфигурации'
            }
        
        if is_connected:
            return {
                'status': 'healthy',
                'provider': self.server_name,
                'message': 'Сервер работает нормально'
            }
        else:
            return {
                'status': 'unhealthy',
                'provider': self.server_name,
                'message': 'Не удается подключиться к серверу'
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса здоровья {self.server_name}: {e}")
        return {
            'status': 'unhealthy',
            'provider': self.server_name,
            'error': str(e)
        }
```

### **2. Реализованы специфичные методы во всех MCP серверах**

#### **Jira Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья Jira сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'jira', 'message': 'Jira отключен в конфигурации'}
        
        if hasattr(self, 'jira') and self.jira:
            current_user = self.jira.current_user()
            return {
                'status': 'healthy',
                'provider': 'jira',
                'message': f'Подключение к Jira успешно. Пользователь: {current_user}',
                'server_url': self.jira_url
            }
        else:
            return {'status': 'unhealthy', 'provider': 'jira', 'message': 'Jira клиент не инициализирован'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'jira', 'error': str(e)}
```

#### **GitLab Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья GitLab сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'gitlab', 'message': 'GitLab отключен в конфигурации'}
        
        if hasattr(self, 'gitlab') and self.gitlab:
            current_user = self.gitlab.user
            return {
                'status': 'healthy',
                'provider': 'gitlab',
                'message': f'Подключение к GitLab успешно. Пользователь: {current_user.username}',
                'server_url': self.gitlab_url
            }
        else:
            return {'status': 'unhealthy', 'provider': 'gitlab', 'message': 'GitLab клиент не инициализирован'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'gitlab', 'error': str(e)}
```

#### **Atlassian Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья Atlassian сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'atlassian', 'message': 'Atlassian отключен в конфигурации'}
        
        if hasattr(self, 'confluence') and self.confluence:
            current_user = self.confluence.get_current_user()
            return {
                'status': 'healthy',
                'provider': 'atlassian',
                'message': f'Подключение к Confluence успешно. Пользователь: {current_user.get("displayName", "Unknown")}',
                'server_url': self.confluence_url
            }
        else:
            return {'status': 'unhealthy', 'provider': 'atlassian', 'message': 'Confluence клиент не инициализирован'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'atlassian', 'error': str(e)}
```

#### **1C Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья 1C сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'onec', 'message': '1C отключен в конфигурации'}
        
        if hasattr(self, 'auth') and self.auth:
            response = requests.get(f"{self.base_url}/api/v1/tasks", headers=self.auth, timeout=5)
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'provider': 'onec',
                    'message': f'Подключение к 1C успешно. Сервер: {self.base_url}',
                    'server_url': self.base_url
                }
            else:
                return {'status': 'unhealthy', 'provider': 'onec', 'message': f'1C сервер недоступен. Статус: {response.status_code}'}
        else:
            return {'status': 'unhealthy', 'provider': 'onec', 'message': '1C клиент не инициализирован'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'onec', 'error': str(e)}
```

#### **LDAP Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья LDAP сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'ldap', 'message': 'LDAP отключен в конфигурации'}
        
        if hasattr(self, 'server') and self.server:
            from ldap3 import Connection, Server
            
            server = Server(self.server)
            conn = Connection(server, auto_bind=True)
            
            if conn.bind():
                conn.unbind()
                return {
                    'status': 'healthy',
                    'provider': 'ldap',
                    'message': f'Подключение к LDAP успешно. Сервер: {self.server}',
                    'server_url': self.server
                }
            else:
                return {'status': 'unhealthy', 'provider': 'ldap', 'message': 'Не удается подключиться к LDAP серверу'}
        else:
            return {'status': 'unhealthy', 'provider': 'ldap', 'message': 'LDAP сервер не настроен'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'ldap', 'error': str(e)}
```

#### **File Server:**
```python
def get_health_status(self) -> Dict[str, Any]:
    """Возвращает статус здоровья File сервера"""
    try:
        if not self.is_enabled():
            return {'status': 'disabled', 'provider': 'file', 'message': 'File сервер отключен в конфигурации'}
        
        if not os.path.exists(self.base_path):
            return {'status': 'unhealthy', 'provider': 'file', 'message': f'Базовая директория не существует: {self.base_path}'}
        
        # Проверяем права на чтение и запись
        test_file = os.path.join(self.base_path, '.test_write')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return {
                'status': 'healthy',
                'provider': 'file',
                'message': f'Файловая система доступна. Базовая директория: {self.base_path}',
                'base_path': self.base_path
            }
        except (OSError, IOError) as e:
            return {'status': 'unhealthy', 'provider': 'file', 'message': f'Нет прав доступа к файловой системе: {str(e)}'}
    except Exception as e:
        return {'status': 'unhealthy', 'provider': 'file', 'error': str(e)}
```

### **3. Обновлен метод `_is_server_available()` в `mcp_client.py`**

#### **До (проблема):**
```python
def _is_server_available(self, server_name: str, server: Any) -> bool:
    """Проверяет доступность сервера"""
    try:
        # Проверяем, что сервер включен и имеет метод check_health
        if hasattr(server, 'is_enabled') and hasattr(server, 'check_health'):
            if server.is_enabled():
                health = server.check_health()  # ❌ Метод не существует
                return health.get('status') == 'healthy'
        return False
    except Exception:
        return False
```

#### **После (исправлено):**
```python
def _is_server_available(self, server_name: str, server: Any) -> bool:
    """Проверяет доступность сервера"""
    try:
        # Проверяем, что сервер включен
        if hasattr(server, 'is_enabled') and callable(server.is_enabled):
            if server.is_enabled():
                # Проверяем здоровье сервера через get_health_status
                if hasattr(server, 'get_health_status') and callable(server.get_health_status):
                    health = server.get_health_status()
                    return health.get('status') == 'healthy'
                # Или через test_connection если есть
                elif hasattr(server, 'test_connection') and callable(server.test_connection):
                    return server.test_connection()
                # Если нет методов проверки, считаем доступным
                else:
                    logger.warning(f"⚠️ Сервер {server_name} не имеет методов проверки здоровья")
                    return True
        return False
    except Exception as e:
        logger.warning(f"⚠️ Ошибка проверки доступности сервера {server_name}: {e}")
        return False
```

## ✅ Результат

### **Что исправлено:**
- ✅ **Добавлен метод `get_health_status()`** во все MCP серверы
- ✅ **Реализованы специфичные проверки** для каждого типа сервера
- ✅ **Обновлен `mcp_client.py`** для использования методов вместо свойств
- ✅ **Добавлены проверки `callable()`** для безопасности
- ✅ **Улучшено логирование** ошибок и предупреждений

### **Поддерживаемые статусы:**
- ✅ **`healthy`** - сервер работает нормально
- ✅ **`unhealthy`** - сервер недоступен или ошибка
- ✅ **`disabled`** - сервер отключен в конфигурации

### **Информация в ответе:**
- ✅ **`status`** - статус сервера
- ✅ **`provider`** - имя провайдера
- ✅ **`message`** - описание статуса
- ✅ **`server_url`** - URL сервера (если применимо)
- ✅ **`error`** - описание ошибки (если есть)

## 🚀 Преимущества исправления

### **Надежность:**
- ✅ **Проверка методов** - `callable()` предотвращает ошибки
- ✅ **Обработка исключений** - все ошибки логируются
- ✅ **Fallback логика** - если нет методов проверки, сервер считается доступным

### **Информативность:**
- ✅ **Детальные статусы** - понятные сообщения о состоянии
- ✅ **Контекстная информация** - URL серверов, пользователи
- ✅ **Диагностика ошибок** - подробные сообщения об ошибках

### **Гибкость:**
- ✅ **Универсальный интерфейс** - все серверы используют один метод
- ✅ **Специфичные проверки** - каждый сервер проверяется по-своему
- ✅ **Расширяемость** - легко добавить новые типы проверок

## 🎯 Итог

**Проблема с методами проверки здоровья MCP серверов полностью решена!**

- ✅ **Все MCP серверы** имеют метод `get_health_status()`
- ✅ **`mcp_client.py`** корректно использует методы вместо свойств
- ✅ **Проверки безопасности** предотвращают ошибки
- ✅ **Детальная диагностика** помогает в отладке

**Система теперь корректно проверяет состояние всех MCP серверов!** 🚀
