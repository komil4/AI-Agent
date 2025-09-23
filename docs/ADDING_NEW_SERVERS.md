# Добавление новых MCP серверов

Система MCP серверов спроектирована так, чтобы добавление нового сервера было максимально простым. Для добавления нового сервера нужно выполнить всего несколько шагов.

## Шаги для добавления нового сервера

### 1. Создание файла сервера

Создайте новый файл в директории `mcp_servers/` с именем `{server_name}_server.py`:

```python
import os
from typing import Dict, Any, List
from config.config_manager import ConfigManager
from . import BaseMCPServer

class {ServerName}MCPServer(BaseMCPServer):
    """Описание сервера - что он делает"""
    
    def __init__(self):
        super().__init__()
        self.description = "Краткое описание сервера"
        self.tools = [
            {
                "name": "tool_name",
                "description": "Описание инструмента",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "Описание параметра"}
                    },
                    "required": ["param1"]
                }
            }
        ]
        
        self.config_manager = ConfigManager()
        # Инициализация сервера
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент сервера"""
        try:
            if tool_name == "tool_name":
                return self._tool_method(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": f"Ошибка выполнения {tool_name}: {str(e)}"}
    
    def _tool_method(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Реализация инструмента"""
        # Логика инструмента
        return {"result": "success"}
    
    def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность сервера"""
        try:
            # Проверка доступности
            return {
                'status': 'healthy',
                'provider': 'server_name'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'server_name',
                'error': str(e)
            }
```

### 2. Добавление в список серверов

Добавьте новый сервер в `mcp_client.py` в словарь `server_modules`:

```python
server_modules = {
    'jira': 'mcp_servers.jira_server',
    'gitlab': 'mcp_servers.gitlab_server',
    'atlassian': 'mcp_servers.atlassian_server',
    'ldap': 'mcp_servers.ldap_server',
    'onec': 'mcp_servers.onec_server',
    'file': 'mcp_servers.file_server',
    'new_server': 'mcp_servers.new_server_server'  # Добавьте здесь
}
```

### 3. Добавление конфигурации

Добавьте конфигурацию сервера в `config/config_manager.py` в `default_config`:

```python
"new_server": {
    "param1": "",
    "param2": "",
    "enabled": False
},
```

### 4. Добавление в веб-интерфейс

#### Админ-панель (`templates/admin.html`)

1. Добавьте кнопку в навигацию:
```html
<button class="btn btn-outline-success btn-sm" onclick="showSection('new_server')">
    <i class="fas fa-icon"></i> Новый сервер
</button>
```

2. Добавьте название в `sectionNames`:
```javascript
const sectionNames = {
    // ... другие серверы
    'new_server': 'Новый сервер'
};
```

3. Добавьте конфигурацию в `sectionConfigs`:
```javascript
'new_server': [
    { key: 'param1', label: 'Параметр 1', type: 'text', placeholder: 'значение' },
    { key: 'param2', label: 'Параметр 2', type: 'password', placeholder: 'пароль' },
    { key: 'enabled', label: 'Включено', type: 'checkbox' }
],
```

4. Добавьте в MCP серверы:
```javascript
'mcp_servers': [
    // ... другие серверы
    { key: 'new_server', label: 'Новый сервер MCP', type: 'section' }
]
```

#### Главный интерфейс (`templates/index.html`)

1. Добавьте статус сервера:
```html
<div class="mb-2" data-service="new_server">
    <span class="status-indicator" id="new_server-status"></span>
    <small>Новый сервер MCP</small>
</div>
```

2. Добавьте быструю команду:
```html
<button class="btn btn-outline-success btn-sm" onclick="sendQuickCommand('команда для нового сервера')" data-service="new_server">
    <i class="fas fa-icon"></i> Новый сервер
</button>
```

3. Добавьте категорию промтов:
```html
<div class="prompt-category mb-3" data-service="new_server">
    <small class="text-muted fw-bold">🔧 Новый сервер</small>
    <div class="d-flex flex-wrap gap-1 mt-1">
        <span class="badge bg-light text-dark prompt-badge" onclick="sendQuickCommand('команда 1')">
            команда 1
        </span>
        <span class="badge bg-light text-dark prompt-badge" onclick="sendQuickCommand('команда 2')">
            команда 2
        </span>
    </div>
</div>
```

## Пример: Файловый сервер

В качестве примера реализован файловый сервер (`mcp_servers/file_server.py`), который демонстрирует:

- Наследование от `BaseMCPServer`
- Определение инструментов
- Реализацию методов `call_tool` и `check_health`
- Интеграцию с веб-интерфейсом

## Принципы проектирования

1. **Расширяемость**: Новые серверы добавляются без изменения существующего кода
2. **Единообразие**: Все серверы следуют одному интерфейсу
3. **Автоматическое обнаружение**: Серверы автоматически загружаются и проверяются
4. **Динамический промт**: Описания серверов автоматически включаются в промт LLM
5. **Конфигурируемость**: Каждый сервер может быть включен/отключен через конфигурацию

## Требования к серверу

- Наследование от `BaseMCPServer`
- Реализация методов `call_tool` и `check_health`
- Определение `description` и `tools` в `__init__`
- Обработка ошибок в методах
- Возврат результатов в стандартном формате

## Формат ответов

Все методы должны возвращать словарь с результатом:

```python
# Успешный результат
{"result": "data", "status": "success"}

# Ошибка
{"error": "описание ошибки"}

# Результат с данными
{"data": [...], "count": 5, "status": "success"}
```
