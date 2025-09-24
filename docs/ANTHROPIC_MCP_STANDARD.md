# Стандарт Anthropic для MCP серверов

## Обзор

Данный документ описывает приведение MCP серверов проекта к стандарту Anthropic с использованием библиотеки FastMCP и улучшенных схем описания инструментов.

## Принципы стандарта Anthropic

### 1. Структура описания инструментов

Каждый инструмент должен иметь четкую структуру:

```python
{
    "name": "название_инструмента",
    "description": "Подробное описание функциональности инструмента",
    "inputSchema": {
        "type": "object",
        "properties": {
            "параметр1": {
                "type": "string",
                "description": "Описание параметра",
                "enum": ["значение1", "значение2"]  # если применимо
            },
            "параметр2": {
                "type": "integer",
                "description": "Описание числового параметра",
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["параметр1"]  # обязательные параметры
    }
}
```

### 2. Стандартизированные типы параметров

#### Строковые параметры
```python
{
    "type": "string",
    "description": "Четкое описание назначения параметра",
    "minLength": 1,  # если применимо
    "maxLength": 255,  # если применимо
    "pattern": "^[a-zA-Z0-9_-]+$"  # если применимо
}
```

#### Числовые параметры
```python
{
    "type": "integer",
    "description": "Описание числового параметра",
    "minimum": 1,
    "maximum": 1000,
    "default": 20  # если применимо
}
```

#### Перечисления
```python
{
    "type": "string",
    "description": "Описание параметра с ограниченным набором значений",
    "enum": ["значение1", "значение2", "значение3"]
}
```

#### Массивы
```python
{
    "type": "array",
    "items": {"type": "string"},
    "description": "Описание массива",
    "minItems": 1,
    "maxItems": 10
}
```

### 3. Стандартизированные описания

#### Общие параметры
- `id` - "Уникальный идентификатор"
- `name` - "Название"
- `description` - "Описание"
- `status` - "Статус"
- `priority` - "Приоритет"
- `assignee` - "Исполнитель"
- `project` - "Проект"
- `created_at` - "Дата создания"
- `updated_at` - "Дата обновления"
- `url` - "URL адрес"
- `token` - "Токен доступа"
- `username` - "Имя пользователя"
- `password` - "Пароль"

#### Статусы
- `opened` - "Открыт"
- `closed` - "Закрыт"
- `merged` - "Объединен"
- `in_progress` - "В работе"
- `pending` - "Ожидает"
- `completed` - "Завершен"

#### Приоритеты
- `highest` - "Наивысший"
- `high` - "Высокий"
- `medium` - "Средний"
- `low` - "Низкий"
- `lowest` - "Наименьший"

## Структура MCP сервера

### 1. Базовый класс

```python
from mcp_servers.base_fastmcp_server import BaseFastMCPServer

class MyMCPServer(BaseFastMCPServer):
    def __init__(self):
        super().__init__("service_name")
        self.tools = [
            create_tool_schema(
                name="tool_name",
                description="Описание инструмента",
                parameters={
                    "properties": {...},
                    "required": [...]
                }
            )
        ]
    
    def _get_description(self) -> str:
        return "Описание сервера"
    
    def _load_config(self):
        # Загрузка конфигурации
        pass
    
    def _connect(self):
        # Подключение к сервису
        pass
    
    def _test_connection(self) -> bool:
        # Тестирование подключения
        return True
```

### 2. Структура инструментов

Каждый инструмент должен:

1. **Иметь четкое название** - отражающее функциональность
2. **Содержать подробное описание** - что делает инструмент
3. **Иметь валидированные параметры** - с типами и ограничениями
4. **Возвращать стандартизированный ответ** - с использованием `format_tool_response`

### 3. Стандартизированные ответы

```python
def my_tool(self, param1: str, param2: int) -> Dict[str, Any]:
    try:
        # Логика инструмента
        result = perform_action(param1, param2)
        
        return format_tool_response(
            success=True,
            message="Операция выполнена успешно",
            data={
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в инструменте: {e}")
        return format_tool_response(
            success=False,
            message=f"Ошибка выполнения: {str(e)}"
        )
```

## Примеры реализации

### 1. Jira сервер

```python
class JiraFastMCPServer(BaseFastMCPServer):
    def create_issue(self, summary: str, project_key: str, 
                     description: str = None, issue_type: str = "Task",
                     priority: str = None, assignee: str = None,
                     labels: List[str] = None) -> Dict[str, Any]:
        """Создает новую задачу в Jira с указанными параметрами"""
        # Реализация...
```

**Схема инструмента:**
```python
create_tool_schema(
    name="create_issue",
    description="Создает новую задачу в Jira с указанными параметрами",
    parameters={
        "properties": {
            "summary": {
                "type": "string",
                "description": "Краткое описание задачи (обязательно)"
            },
            "project_key": {
                "type": "string",
                "description": "Ключ проекта (например, TEST)"
            },
            "issue_type": {
                "type": "string",
                "description": "Тип задачи",
                "enum": ["Task", "Bug", "Story", "Epic"]
            },
            "priority": {
                "type": "string",
                "description": "Приоритет задачи",
                "enum": ["Highest", "High", "Medium", "Low", "Lowest"]
            }
        },
        "required": ["summary", "project_key"]
    }
)
```

### 2. GitLab сервер

```python
class GitLabFastMCPServer(BaseFastMCPServer):
    def create_merge_request(self, project_id: str, title: str, source_branch: str,
                            description: str = None, target_branch: str = None,
                            assignee_id: int = None, reviewer_ids: List[int] = None,
                            labels: List[str] = None) -> Dict[str, Any]:
        """Создает новый merge request в GitLab"""
        # Реализация...
```

## Преимущества стандарта Anthropic

### 1. Улучшенная совместимость
- Стандартизированные схемы инструментов
- Совместимость с различными MCP клиентами
- Улучшенная интеграция с AI моделями

### 2. Лучшая документация
- Автоматическая генерация документации
- Четкие описания параметров
- Валидация входных данных

### 3. Упрощенная разработка
- Переиспользуемые компоненты
- Стандартизированные паттерны
- Упрощенное тестирование

### 4. Профессиональный вид
- Консистентный API
- Стандартизированные ответы
- Улучшенная обработка ошибок

## Миграция существующих серверов

### 1. Этапы миграции

1. **Создание базового класса** - `BaseFastMCPServer`
2. **Рефакторинг схем инструментов** - приведение к стандарту Anthropic
3. **Обновление методов** - использование `format_tool_response`
4. **Тестирование** - проверка совместимости
5. **Документирование** - обновление документации

### 2. Пример миграции

**Было:**
```python
{
    "name": "create_issue",
    "description": "Создает новую задачу в Jira",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Краткое описание задачи"},
            "project_key": {"type": "string", "description": "Ключ проекта"}
        },
        "required": ["summary", "project_key"]
    }
}
```

**Стало:**
```python
create_tool_schema(
    name="create_issue",
    description="Создает новую задачу в Jira с указанными параметрами",
    parameters={
        "properties": {
            "summary": {
                "type": "string",
                "description": "Краткое описание задачи (обязательно)"
            },
            "project_key": {
                "type": "string",
                "description": "Ключ проекта (например, TEST)"
            },
            "issue_type": {
                "type": "string",
                "description": "Тип задачи",
                "enum": ["Task", "Bug", "Story", "Epic"]
            }
        },
        "required": ["summary", "project_key"]
    }
)
```

## Рекомендации

### 1. Для разработчиков
- Используйте стандартизированные схемы
- Следуйте принципам именования
- Документируйте все параметры
- Обрабатывайте ошибки корректно

### 2. Для интеграции
- Проверяйте совместимость схем
- Тестируйте с различными клиентами
- Валидируйте входные данные
- Логируйте операции

### 3. Для поддержки
- Поддерживайте обратную совместимость
- Версионируйте изменения
- Документируйте миграции
- Предоставляйте примеры использования

## Заключение

Стандарт Anthropic для MCP серверов обеспечивает:

- **Совместимость** с различными MCP клиентами
- **Стандартизацию** схем инструментов
- **Улучшенную документацию** и валидацию
- **Профессиональный вид** API

Следование этому стандарту делает MCP серверы более надежными, совместимыми и готовыми к интеграции с современными AI системами.
