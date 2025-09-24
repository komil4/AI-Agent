# Автоматическое обнаружение MCP серверов

## 📋 Обзор

Реализована система автоматического обнаружения MCP серверов, которая позволяет добавлять новые серверы простым добавлением файла без изменения основного кода.

## 🔧 Архитектура

### 1. **Автоматическое обнаружение**
- **Сканирование папки** `mcp_servers` на наличие Python файлов
- **Динамический импорт** модулей серверов
- **Автоматическое определение** классов серверов
- **Создание экземпляров** без хардкода

### 2. **Модульная структура**
```
mcp_servers/
├── __init__.py                 # Экспорт функций обнаружения
├── server_discovery.py         # Система автоматического обнаружения
├── base_fastmcp_server.py     # Базовый класс для серверов
├── jira_server.py             # Jira сервер (автоматически обнаруживается)
├── gitlab_server.py           # GitLab сервер (автоматически обнаруживается)
├── atlassian_server.py        # Atlassian сервер (автоматически обнаруживается)
├── ldap_server.py             # LDAP сервер (автоматически обнаруживается)
├── onec_server.py             # 1C сервер (автоматически обнаруживается)
└── file_server.py             # File сервер (автоматически обнаруживается)
```

## 🚀 Как это работает

### 1. **Сканирование серверов**
```python
class MCPServerDiscovery:
    def _scan_servers(self):
        """Сканирует папку с серверами и обнаруживает классы"""
        # Получаем все Python файлы в папке
        python_files = list(servers_path.glob("*.py"))
        
        # Исключаем служебные файлы
        excluded_files = {
            "__init__.py",
            "base_fastmcp_server.py", 
            "server_discovery.py"
        }
        
        for file_path in python_files:
            if file_path.name not in excluded_files:
                # Импортируем модуль и ищем классы серверов
                self._find_server_classes(module, module_name)
```

### 2. **Обнаружение классов**
```python
def _find_server_classes(self, module: Any, module_name: str) -> Dict[str, Type]:
    """Находит классы серверов в модуле"""
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            # Ищем классы, которые заканчиваются на MCPServer или FastMCPServer
            if name.endswith('MCPServer') or name.endswith('FastMCPServer'):
                server_name = self._extract_server_name(name, module_name)
                server_classes[server_name] = obj
```

### 3. **Создание экземпляров**
```python
def create_server_instance(self, server_name: str) -> Any:
    """Создает экземпляр сервера по имени"""
    server_class = self.get_server_class(server_name)
    if server_class:
        return server_class()
    return None
```

## 📝 Как добавить новый MCP сервер

### Шаг 1: Создать файл сервера
Создайте новый файл в папке `mcp_servers/` с именем `your_server.py`:

```python
#!/usr/bin/env python3
"""
MCP сервер для YourService
"""

from .base_fastmcp_server import BaseFastMCPServer, create_tool_schema, format_tool_response

class YourServiceFastMCPServer(BaseFastMCPServer):
    """MCP сервер для YourService"""
    
    def __init__(self):
        super().__init__("your_service")  # Имя сервиса в конфигурации
        
        # Определяем инструменты
        self.tools = [
            create_tool_schema(
                name="your_tool",
                description="Описание вашего инструмента",
                parameters={
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Описание параметра"
                        }
                    },
                    "required": ["param1"]
                }
            )
        ]
    
    def your_tool(self, param1: str) -> Dict[str, Any]:
        """Реализация вашего инструмента"""
        try:
            # Ваша логика здесь
            result = f"Обработано: {param1}"
            
            return format_tool_response(True, "Операция выполнена", {"result": result})
            
        except Exception as e:
            return format_tool_response(False, f"Ошибка: {str(e)}")

# Глобальный экземпляр сервера
your_service_server = YourServiceFastMCPServer()
```

### Шаг 2: Добавить конфигурацию
Добавьте конфигурацию в `app_config.json`:

```json
{
  "your_service": {
    "enabled": true,
    "url": "https://your-service.com",
    "api_key": "your-api-key",
    "additional_params": {}
  }
}
```

### Шаг 3: Готово!
Сервер автоматически обнаружится при следующем запуске приложения.

## 🔍 Правила именования

### 1. **Имя файла**
- Должно заканчиваться на `_server.py`
- Примеры: `jira_server.py`, `gitlab_server.py`, `your_service_server.py`

### 2. **Имя класса**
- Должно заканчиваться на `MCPServer` или `FastMCPServer`
- Примеры: `JiraMCPServer`, `GitLabFastMCPServer`, `YourServiceFastMCPServer`

### 3. **Имя сервера**
- Извлекается автоматически из имени класса или файла
- Приводится к нижнему регистру
- Используется для поиска конфигурации

## 📊 Преимущества новой системы

### ✅ **Модульность**
- Добавление сервера = добавление файла
- Нет необходимости изменять основной код
- Автоматическое обнаружение новых серверов

### ✅ **Гибкость**
- Поддержка различных типов серверов
- Легкое включение/отключение серверов
- Динамическая загрузка инструментов

### ✅ **Масштабируемость**
- Неограниченное количество серверов
- Автоматическое управление зависимостями
- Изоляция серверов друг от друга

### ✅ **Простота разработки**
- Стандартизированный интерфейс
- Базовый класс с общими функциями
- Автоматическая валидация и форматирование

## 🛠️ Технические детали

### **Автоматическое обнаружение**
```python
# Сканирование папки
python_files = list(servers_path.glob("*.py"))

# Импорт модулей
module = importlib.import_module(f"mcp_servers.{module_name}")

# Поиск классов
for name, obj in inspect.getmembers(module, inspect.isclass):
    if name.endswith('MCPServer'):
        # Создание экземпляра
        server_instance = server_class()
```

### **Проверка включения**
```python
def is_enabled(self) -> bool:
    """Проверяет, включен ли сервер"""
    service_config = config_manager.get_service_config(self.service_name)
    return service_config.get('enabled', False)
```

### **Получение инструментов**
```python
def get_tools(self) -> list:
    """Возвращает список инструментов сервера"""
    return getattr(self, 'tools', [])
```

## 🔄 Миграция с старой системы

### **Что изменилось:**
1. **Удалены хардкодированные методы** `_connect_jira_server()`, `_connect_gitlab_server()` и т.д.
2. **Добавлено автоматическое обнаружение** через `MCPServerDiscovery`
3. **Упрощен MCP клиент** - теперь он не знает о конкретных серверах
4. **Стандартизированы серверы** - все используют `BaseFastMCPServer`

### **Что осталось:**
1. **Конфигурация серверов** в `app_config.json`
2. **Интерфейс серверов** - методы `get_tools()`, `is_enabled()`
3. **Внешние MCP серверы** - поддержка через конфигурацию

## 📈 Производительность

### **Оптимизации:**
- **Ленивая загрузка** - серверы создаются только при необходимости
- **Кэширование** - обнаруженные серверы сохраняются в памяти
- **Фильтрация** - загружаются только включенные серверы

### **Мониторинг:**
- Логирование процесса обнаружения
- Отслеживание ошибок загрузки
- Статистика по серверам

## 🔮 Будущие улучшения

### **Возможные расширения:**
1. **Горячая перезагрузка** - добавление серверов без перезапуска
2. **Плагинная система** - загрузка серверов из внешних пакетов
3. **Автоматическая валидация** - проверка соответствия интерфейсу
4. **Метрики производительности** - мониторинг работы серверов

### **Оптимизации:**
1. **Параллельная загрузка** - одновременное создание экземпляров
2. **Кэширование инструментов** - сохранение схем инструментов
3. **Ленивая инициализация** - создание серверов по требованию

## ✅ Заключение

Новая система автоматического обнаружения MCP серверов обеспечивает:

- **Полную модульность** - добавление сервера = добавление файла
- **Автоматическое обнаружение** - без изменения основного кода
- **Стандартизацию** - единый интерфейс для всех серверов
- **Масштабируемость** - неограниченное количество серверов

**Теперь добавление нового MCP сервера сводится только к созданию файла с классом сервера!** 🚀
