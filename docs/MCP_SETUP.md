# Настройка MCP серверов

## Установка Node.js и MCP серверов

### 1. Установка Node.js
```bash
# Скачайте и установите Node.js с официального сайта
# https://nodejs.org/

# Проверьте установку
node --version
npm --version
```

### 2. Установка MCP серверов

#### Jira MCP сервер
```bash
npm install -g @modelcontextprotocol/server-jira
```

#### GitLab MCP сервер
```bash
npm install -g @modelcontextprotocol/server-gitlab
```

#### Confluence MCP сервер
```bash
npm install -g @modelcontextprotocol/server-confluence
```

### 3. Настройка в админ панели

1. Откройте админ панель приложения
2. Перейдите в раздел "MCP Серверы"
3. Настройте каждый сервер:

#### Jira MCP
- **URL**: `https://yourcompany.atlassian.net`
- **Username**: ваш email
- **API Token**: токен из Jira

#### GitLab MCP
- **URL**: `https://gitlab.com` (или ваш GitLab)
- **Token**: Personal Access Token

#### Confluence MCP
- **URL**: `https://yourcompany.atlassian.net`
- **Username**: ваш email
- **API Token**: токен из Confluence

### 4. Проверка работы

После настройки MCP серверов в админ панели:

1. Перезапустите приложение
2. Откройте чат
3. Попробуйте команды:
   - "показать задачи jira"
   - "показать проекты gitlab"
   - "найти страницы confluence"

## Преимущества MCP

- ✅ **Стандартизированный протокол** - использует официальный MCP протокол
- ✅ **Штатные серверы** - серверы от разработчиков MCP
- ✅ **Автоматическое обновление** - серверы обновляются через npm
- ✅ **Лучшая интеграция** - полная поддержка всех функций сервисов
- ✅ **Безопасность** - токены передаются через переменные окружения

## Устранение неполадок

### Ошибка "command not found: npx"
- Убедитесь, что Node.js установлен
- Перезапустите терминал

### Ошибка подключения к MCP серверу
- Проверьте правильность URL и токенов
- Убедитесь, что сервисы доступны из сети

### Таймауты
- Увеличьте таймаут в настройках LLM
- Проверьте скорость интернет-соединения
