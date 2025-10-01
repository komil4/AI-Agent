# Neurolink LLM Provider

## Описание

Новый LLM провайдер для работы с Neurolink API, который предоставляет доступ к модели Google Gemma-3-27b-it.

## Конфигурация

Все настройки захардкожены в провайдере:

- **API URL**: `http://neurolink.iek.local:8004/v1/chat/completions`
- **API Key**: `ARjgZphys9tBWYnnJl5UdnOeAubUCwzaAhEpRnFi1yE`
- **Model**: `google/gemma-3-27b-it`
- **Temperature**: `0.15`
- **Max Tokens**: `2048`
- **Timeout**: `30` секунд

## Использование

### Через фабрику провайдеров:

```python
from llm_providers.provider_factory import LLMProviderFactory
from config.llm_config import LLMProvider

# Создание провайдера
provider = LLMProviderFactory.create_provider(LLMProvider.NEUROLINK)

# Генерация ответа
messages = [{"role": "user", "content": "Привет!"}]
response = await provider.generate_response(messages)
```

### Через конфигурацию по умолчанию:

```python
# Neurolink настроен как провайдер по умолчанию в app_config.json
provider = LLMProviderFactory.create_default_provider()
```

## API Формат

Провайдер использует стандартный OpenAI-совместимый API формат:

### Запрос:
```json
{
    "messages": [
        {"role": "user", "content": "Докажи теорему Пифагора, в 3 предложения."}
    ],
    "temperature": 0.15,
    "stream": false
}
```

### Ответ:
```json
{
    "id": "chatcmpl-b9e0a412caa44dfbb86ded7e1e98626c",
    "object": "chat.completion",
    "created": 1759325352,
    "model": "google/gemma-3-27b-it",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Теорема Пифагора утверждает..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 24,
        "total_tokens": 156,
        "completion_tokens": 132
    }
}
```

## Тестирование

Запустите тестовый скрипт для проверки работы провайдера:

```bash
python test_neurolink_provider.py
```

## Особенности

1. **HTTP клиент**: Использует `aiohttp` для асинхронных HTTP запросов
2. **Автоматическое управление сессиями**: Создает и переиспользует HTTP сессии
3. **Обработка ошибок**: Полная обработка HTTP ошибок и таймаутов
4. **Поддержка инструментов**: Базовая поддержка function calling (пока что возвращает обычный ответ)
5. **Health check**: Проверка доступности API

## Приоритет

Neurolink провайдер имеет наивысший приоритет в системе и будет использоваться по умолчанию, если доступен.
