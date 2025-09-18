# Диаграмма структуры проекта MCP AI Ассистент

## 🏗️ Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP AI Ассистент                        │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Веб-интерфейс (templates/, static/)                        │
│  ├── index.html (Главная страница)                             │
│  ├── login.html (Страница входа)                               │
│  └── admin.html (Админ-панель)                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Приложение (app.py)                 │
│  ├── API эндпоинты                                             │
│  ├── Аутентификация (auth/)                                    │
│  └── Управление сессиями                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│    LLM Клиент           │    │    MCP Клиент           │
│   (llm_client.py)       │    │   (mcp_client.py)       │
└─────────────────────────┘    └─────────────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   LLM Провайдеры        │    │    MCP Серверы          │
│  (llm_providers/)       │    │   (mcp_servers/)        │
│  ├── OpenAI             │    │  ├── Jira               │
│  ├── Anthropic          │    │  ├── GitLab             │
│  ├── Google             │    │  ├── Confluence         │
│  ├── Ollama             │    │  └── LDAP               │
│  └── Local              │    │                         │
└─────────────────────────┘    └─────────────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Внешние сервисы                              │
│  ├── OpenAI API                                                 │
│  ├── Anthropic API                                              │
│  ├── Google API                                                 │
│  ├── Ollama (локально)                                          │
│  ├── Jira API                                                   │
│  ├── GitLab API                                                 │
│  ├── Confluence API                                             │
│  └── Active Directory                                           │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Структура директорий

```
MCP/
├── 🚀 main.py                    # Точка входа
├── 🌐 app.py                     # FastAPI приложение
├── 📋 models.py                  # Pydantic модели
├── 🤖 llm_client.py              # LLM клиент
├── 🔌 mcp_client.py              # MCP клиент
├── 📦 requirements.txt           # Зависимости
├── 🐳 Dockerfile                 # Docker
├── 🐳 docker-compose.yml         # Docker Compose
├── 🚫 .gitignore                 # Git ignore
├── 📖 README.md                  # Документация
│
├── 🔐 auth/                      # Аутентификация
│   ├── ad_auth.py               # Active Directory
│   ├── admin_auth.py            # Админ аутентификация
│   ├── middleware.py            # Middleware
│   └── session_manager.py       # Управление сессиями
│
├── ⚙️ config/                    # Конфигурация
│   ├── config_manager.py        # Менеджер конфигурации
│   └── llm_config.py            # LLM конфигурация
│
├── 🤖 llm_providers/             # LLM провайдеры
│   ├── base_provider.py         # Базовый класс
│   ├── openai_provider.py       # OpenAI
│   ├── anthropic_provider.py    # Anthropic
│   ├── google_provider.py       # Google
│   ├── ollama_provider.py       # Ollama
│   └── provider_factory.py      # Фабрика
│
├── 🔌 mcp_servers/               # MCP серверы
│   ├── jira_server.py           # Jira
│   ├── gitlab_server.py         # GitLab
│   ├── atlassian_server.py      # Confluence
│   └── ldap_server.py           # LDAP
│
├── 🔍 analyzers/                 # Анализаторы
│   └── code_analyzer.py         # Анализатор кода
│
├── 🌐 templates/                 # HTML шаблоны
│   ├── index.html               # Главная
│   ├── login.html               # Вход
│   └── admin.html               # Админ-панель
│
├── 📁 static/                    # Статические файлы
│
├── 🧪 tests/                     # Тесты
│   ├── test_ldap_toggle.py
│   ├── test_llm_admin.py
│   ├── test_llm_interaction.py
│   └── test_llm_providers.py
│
├── 📚 docs/                      # Документация
│   ├── README.md
│   ├── LLM_PROVIDERS.md
│   ├── MCP_SETUP.md
│   ├── PROJECT_STRUCTURE.md
│   ├── REORGANIZATION.md
│   └── STRUCTURE_DIAGRAM.md
│
├── 🚀 scripts/                   # Скрипты
│   ├── start.bat                # Windows
│   └── start.sh                 # Linux/Mac
│
└── ⚙️ config_files/              # Конфигурация
    ├── app_config.json          # Основная конфигурация
    ├── app_config.json.example  # Пример конфигурации
    ├── admin_config.json        # Админ конфигурация
    └── python_ldap-*.whl        # LDAP пакет
```

## 🔄 Потоки данных

### 1. Пользовательский запрос
```
Пользователь → templates/ → app.py → llm_client.py → llm_providers/ → LLM API
```

### 2. Обработка с инструментами
```
LLM → mcp_client.py → mcp_servers/ → Внешние API (Jira, GitLab, etc.)
```

### 3. Аутентификация
```
Запрос → auth/middleware.py → auth/ad_auth.py → Active Directory
```

### 4. Админ-панель
```
Админ → templates/admin.html → app.py → config/ → config_files/
```

## 🏗️ Принципы архитектуры

### 1. Разделение ответственности
- **app.py** - API и маршрутизация
- **llm_client.py** - работа с LLM
- **mcp_client.py** - работа с MCP серверами
- **auth/** - аутентификация и авторизация
- **config/** - управление конфигурацией

### 2. Модульность
- Каждый компонент в отдельной директории
- Четкие интерфейсы между модулями
- Минимальные зависимости

### 3. Конфигурируемость
- Все настройки в `config_files/`
- Возможность отключения компонентов
- Гибкая настройка провайдеров

### 4. Расширяемость
- Легко добавлять новые LLM провайдеры
- Простое добавление MCP серверов
- Модульная архитектура

## 🚀 Развертывание

### Локальная разработка
```bash
python main.py
```

### Docker
```bash
docker-compose up -d
```

### Продакшн
```bash
# Настройка
cp config_files/app_config.json.example config_files/app_config.json
# Редактирование настроек
# Запуск
python main.py
```

## 📊 Мониторинг

- Health check эндпоинты
- Логирование через Python logging
- Метрики в админ-панели
- Отслеживание ошибок

## 🔒 Безопасность

- JWT токены
- Middleware авторизации
- Шифрование паролей
- Валидация данных
- CORS настройки
