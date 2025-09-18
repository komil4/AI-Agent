# MCP AI Ассистент

Интеллектуальный ассистент для работы с MCP серверами (Jira, GitLab, Confluence, LDAP) с поддержкой различных LLM провайдеров.

## 📁 Структура проекта

```
MCP/
├── main.py                    # Главный файл запуска
├── app.py                     # FastAPI приложение
├── models.py                  # Pydantic модели
├── requirements.txt           # Зависимости Python
├── Dockerfile                 # Docker конфигурация
├── docker-compose.yml         # Docker Compose
├── docker-compose-full.yml    # Полная Docker конфигурация
│
├── auth/                      # Модули аутентификации
│   ├── __init__.py
│   ├── ad_auth.py            # Active Directory аутентификация
│   ├── admin_auth.py         # Админ аутентификация
│   ├── middleware.py         # Middleware для авторизации
│   └── session_manager.py    # Управление сессиями
│
├── config/                    # Конфигурация
│   ├── __init__.py
│   ├── config_manager.py     # Менеджер конфигурации
│   └── llm_config.py         # Конфигурация LLM провайдеров
│
├── llm_providers/             # LLM провайдеры
│   ├── __init__.py
│   ├── base_provider.py      # Базовый класс провайдера
│   ├── openai_provider.py    # OpenAI провайдер
│   ├── anthropic_provider.py # Anthropic Claude провайдер
│   ├── google_provider.py    # Google Gemini провайдер
│   ├── ollama_provider.py    # Ollama провайдер
│   └── provider_factory.py   # Фабрика провайдеров
│
├── mcp_servers/               # MCP серверы
│   ├── __init__.py
│   ├── jira_server.py        # Jira MCP сервер
│   ├── gitlab_server.py      # GitLab MCP сервер
│   ├── atlassian_server.py   # Confluence MCP сервер
│   └── ldap_server.py        # LDAP MCP сервер
│
├── analyzers/                 # Анализаторы
│   ├── __init__.py
│   └── code_analyzer.py      # Анализатор кода
│
├── templates/                 # HTML шаблоны
│   ├── index.html            # Главная страница
│   ├── login.html            # Страница входа
│   └── admin.html            # Админ-панель
│
├── static/                    # Статические файлы
│
├── tests/                     # Тесты
│   ├── test_ldap_toggle.py
│   ├── test_llm_admin.py
│   ├── test_llm_interaction.py
│   ├── test_llm_providers.py
│   └── test_simple_architecture.py
│
├── docs/                      # Документация
│   ├── README.md             # Основная документация
│   ├── LLM_PROVIDERS.md      # Документация по LLM провайдерам
│   └── MCP_SETUP.md          # Настройка MCP
│
├── scripts/                   # Скрипты
│   ├── start.bat             # Запуск на Windows
│   └── start.sh              # Запуск на Linux/Mac
│
└── config_files/              # Файлы конфигурации
    ├── app_config.json       # Основная конфигурация
    ├── admin_config.json     # Конфигурация админа
    └── python_ldap-*.whl     # Python LDAP пакет
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка конфигурации

Скопируйте файл конфигурации и настройте его:

```bash
cp config_files/app_config.json.example config_files/app_config.json
```

Отредактируйте `config_files/app_config.json` с вашими настройками.

### 3. Запуск приложения

```bash
# Прямой запуск
python main.py

# Или через скрипт
scripts/start.sh    # Linux/Mac
scripts/start.bat   # Windows
```

### 4. Доступ к приложению

- **Главная страница**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **Админ-панель**: http://localhost:8000/admin

## 🔧 Конфигурация

### Основные настройки

Все настройки находятся в `config_files/app_config.json`:

```json
{
  "llm": {
    "provider": "ollama",
    "providers": {
      "openai": {
        "enabled": false,
        "api_key": "your-key",
        "model": "gpt-4o-mini"
      },
      "ollama": {
        "enabled": true,
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b"
      }
    }
  },
  "active_directory": {
    "enabled": true,
    "server": "ldap://domain.local:389"
  }
}
```

### LLM Провайдеры

Поддерживаемые провайдеры:
- **OpenAI**: GPT-4, GPT-3.5, GPT-4o-mini
- **Anthropic**: Claude-3.5-Sonnet, Claude-3-Haiku
- **Google**: Gemini-1.5-Flash, Gemini-1.5-Pro
- **Ollama**: Локальные модели (Llama, Mistral, CodeLlama)
- **Local**: Пользовательские API

Подробнее см. [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md)

## 🧪 Тестирование

Запустите тесты для проверки функциональности:

```bash
# Все тесты
python -m pytest tests/

# Конкретный тест
python tests/test_llm_providers.py
python tests/test_llm_admin.py
```

## 🐳 Docker

### Запуск с Docker Compose

```bash
# Базовая конфигурация
docker-compose up -d

# Полная конфигурация с Redis
docker-compose -f docker-compose-full.yml up -d
```

## 📚 Документация

- [docs/README.md](docs/README.md) - Подробная документация
- [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) - LLM провайдеры
- [docs/MCP_SETUP.md](docs/MCP_SETUP.md) - Настройка MCP

## 🔐 Безопасность

- 🔐 **Аутентификация через Active Directory**
- 🔒 **JWT токены** для сессий
- 🍪 **Redis** для управления сессиями
- 🛡️ **Middleware авторизации**
- 👥 **Проверка групп AD**

## ⚙️ Админ-панель

Управление через веб-интерфейс:
- Настройка LLM провайдеров
- Конфигурация MCP серверов
- Тестирование подключений
- Управление пользователями

## 🛠️ Разработка

### Структура кода

- **app.py** - FastAPI приложение и API эндпоинты
- **models.py** - Pydantic модели данных
- **llm_client.py** - Клиент для работы с LLM
- **mcp_client.py** - Клиент для работы с MCP серверами
- **auth/** - Модули аутентификации и авторизации
- **llm_providers/** - Реализации LLM провайдеров
- **mcp_servers/** - Реализации MCP серверов

### Добавление нового LLM провайдера

1. Создайте класс в `llm_providers/`
2. Наследуйтесь от `BaseLLMProvider`
3. Реализуйте методы `generate_response` и `generate_with_tools`
4. Добавьте в `provider_factory.py`

### Добавление нового MCP сервера

1. Создайте класс в `mcp_servers/`
2. Реализуйте методы `get_tools()` и `call_tool()`
3. Добавьте в `mcp_client.py`

## 📄 Лицензия

MIT License

## 🤝 Поддержка

Для вопросов и поддержки создайте issue в репозитории.
