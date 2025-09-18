# LLM Провайдеры

Система поддерживает различные LLM провайдеры для генерации ответов и работы с инструментами.

## Поддерживаемые провайдеры

### 1. OpenAI
- **Модели**: GPT-4, GPT-3.5, GPT-4o-mini
- **API**: OpenAI API
- **Требования**: API ключ OpenAI

### 2. Anthropic Claude
- **Модели**: Claude-3.5-Sonnet, Claude-3-Haiku, Claude-3-Opus
- **API**: Anthropic API
- **Требования**: API ключ Anthropic

### 3. Google Gemini
- **Модели**: Gemini-1.5-Flash, Gemini-1.5-Pro
- **API**: Google AI Studio API
- **Требования**: API ключ Google

### 4. Ollama (локальный)
- **Модели**: Llama, Mistral, CodeLlama и другие
- **API**: Локальный Ollama сервер
- **Требования**: Установленный Ollama

### 5. Local (пользовательский)
- **Модели**: Любые совместимые модели
- **API**: Пользовательский API
- **Требования**: Настроенный локальный сервер

## Настройка

### 1. Через файл конфигурации (app_config.json)

```json
{
  "llm": {
    "provider": "ollama",
    "providers": {
      "openai": {
        "api_key": "your-openai-api-key",
        "model": "gpt-4o-mini",
        "base_url": "",
        "temperature": 0.7,
        "max_tokens": 4000,
        "timeout": 30,
        "enabled": true
      },
      "anthropic": {
        "api_key": "your-anthropic-api-key",
        "model": "claude-3-5-sonnet-20241022",
        "base_url": "",
        "temperature": 0.7,
        "max_tokens": 4000,
        "timeout": 30,
        "enabled": false
      },
      "google": {
        "api_key": "your-google-api-key",
        "model": "gemini-1.5-flash",
        "base_url": "",
        "temperature": 0.7,
        "max_tokens": 4000,
        "timeout": 30,
        "enabled": false
      },
      "ollama": {
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "temperature": 0.7,
        "max_tokens": 4000,
        "timeout": 30,
        "enabled": true
      }
    }
  }
}
```

### 2. Через переменные окружения

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_TEMPERATURE="0.7"
export OPENAI_MAX_TOKENS="4000"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
export ANTHROPIC_TEMPERATURE="0.7"
export ANTHROPIC_MAX_TOKENS="4000"

# Google
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_MODEL="gemini-1.5-flash"
export GOOGLE_TEMPERATURE="0.7"
export GOOGLE_MAX_TOKENS="4000"

# Ollama
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.1:8b"
export OLLAMA_TEMPERATURE="0.7"
export OLLAMA_MAX_TOKENS="4000"
```

## API Эндпоинты

### Получение списка провайдеров
```http
GET /api/llm/providers
```

### Переключение провайдера
```http
POST /api/llm/switch-provider
Content-Type: application/json

{
  "provider": "openai"
}
```

### Проверка состояния LLM
```http
GET /api/llm/health
```

### Тестирование провайдера
```http
POST /api/llm/test
Content-Type: application/json

{
  "message": "Привет! Как дела?"
}
```

## Установка зависимостей

```bash
# OpenAI
pip install openai

# Anthropic
pip install anthropic

# Google
pip install google-generativeai

# Ollama (требует aiohttp)
pip install aiohttp
```

## Примеры использования

### Программное переключение провайдера

```python
from llm_client import LLMClient
from config.llm_config import LLMProvider

# Создаем клиент
client = LLMClient()

# Переключаемся на OpenAI
client.switch_provider(LLMProvider.OPENAI)

# Генерируем ответ
response = await client.generate_response("Привет!")
print(response)
```

### Проверка доступности провайдера

```python
# Проверяем здоровье
health = await client.check_health()
if health['status'] == 'healthy':
    print("Провайдер работает")
else:
    print(f"Ошибка: {health['error']}")
```

## Приоритет провайдеров

Система автоматически выбирает провайдер по умолчанию в следующем порядке:

1. OpenAI (если настроен)
2. Anthropic (если настроен)
3. Google (если настроен)
4. Ollama (если настроен)
5. Local (fallback)

## Отладка

### Включение логирования
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Тестирование провайдеров
```bash
python test_llm_providers.py
```

## Рекомендации

1. **Для продакшена**: Используйте OpenAI или Anthropic для лучшего качества
2. **Для разработки**: Используйте Ollama с локальными моделями
3. **Для экономии**: Используйте более дешевые модели (GPT-4o-mini, Claude-3-Haiku)
4. **Для приватности**: Используйте Ollama с локальными моделями

## Устранение неполадок

### Провайдер не инициализируется
- Проверьте API ключи
- Проверьте доступность сервера
- Проверьте логи приложения

### Медленные ответы
- Уменьшите max_tokens
- Используйте более быстрые модели
- Проверьте сетевое соединение

### Ошибки API
- Проверьте лимиты API
- Проверьте правильность API ключей
- Проверьте формат запросов
