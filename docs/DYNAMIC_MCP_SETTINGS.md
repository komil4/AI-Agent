# Динамические настройки MCP серверов

## 📋 Обзор

Реализована система динамических настроек MCP серверов, которая автоматически подстраивается под доступные серверы без необходимости изменения кода админ-панели.

## 🔧 Архитектура

### 1. **Базовый класс MCP сервера**
- **`get_admin_settings()`** - метод для получения настроек админ-панели
- **Автоматическое определение** - имя, иконка, описание из класса сервера
- **Динамические поля** - настройки полей формы из `admin_fields`

### 2. **API эндпоинты**
- **`/api/admin/config`** - получение полной конфигурации с динамическими настройками
- **Автоматическое обнаружение** - сканирование доступных MCP серверов
- **Объединение данных** - настройки + текущая конфигурация

### 3. **Frontend интеграция**
- **Динамическая загрузка** - настройки загружаются из API
- **Адаптивный интерфейс** - автоматическое создание форм
- **Интерактивные карточки** - отдельные настройки для каждого сервера

## 🚀 Как это работает

### 1. **Определение настроек в MCP сервере**
```python
class JiraFastMCPServer(BaseFastMCPServer):
    def __init__(self):
        super().__init__("jira")
        
        # Настройки для админ-панели
        self.display_name = "Jira MCP"
        self.icon = "fas fa-tasks"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL Jira', 'type': 'text', 'placeholder': 'https://your-domain.atlassian.net' },
            { 'key': 'username', 'label': 'Имя пользователя', 'type': 'text', 'placeholder': 'your-email@domain.com' },
            { 'key': 'api_token', 'label': 'API Token', 'type': 'password', 'placeholder': 'ваш API токен' },
            { 'key': 'project_key', 'label': 'Ключ проекта', 'type': 'text', 'placeholder': 'PROJ' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
```

### 2. **Получение настроек через API**
```python
@app.get("/api/admin/config")
async def get_admin_config():
    # Получаем динамические настройки MCP серверов
    mcp_servers_config = {}
    
    discovered_servers = get_discovered_servers()
    
    for server_name, server_class in discovered_servers.items():
        server_instance = create_server_instance(server_name)
        admin_settings = server_instance.get_admin_settings()
        server_config = config.get(server_name, {})
        
        mcp_servers_config[server_name] = {
            **admin_settings,
            'config': server_config
        }
    
    return {
        "config": config,
        "mcp_servers": mcp_servers_config
    }
```

### 3. **Frontend обработка**
```javascript
// Загружаем динамические настройки MCP серверов
if (data.mcp_servers) {
    sectionConfigs['mcp_servers'] = [];
    
    for (const [serverName, serverInfo] of Object.entries(data.mcp_servers)) {
        sectionConfigs['mcp_servers'].push({
            key: serverName,
            label: serverInfo.display_name || `${serverName} MCP`,
            type: 'section',
            icon: serverInfo.icon || 'fas fa-server',
            description: serverInfo.description || `MCP сервер для ${serverName}`,
            fields: serverInfo.fields || []
        });
    }
}
```

## 🛠️ Структура настроек

### **Базовые поля сервера:**
```python
{
    'name': 'jira',                    # Имя сервера
    'display_name': 'Jira MCP',        # Отображаемое имя
    'description': 'MCP сервер для Jira', # Описание
    'icon': 'fas fa-tasks',            # Иконка FontAwesome
    'category': 'mcp_servers',         # Категория
    'fields': [...],                   # Поля формы
    'enabled': True                    # Статус включения
}
```

### **Поля формы:**
```python
{
    'key': 'url',                      # Ключ поля
    'label': 'URL Jira',              # Подпись поля
    'type': 'text',                    # Тип поля (text, password, checkbox, number)
    'placeholder': 'https://...'       # Подсказка
}
```

## 📊 Поддерживаемые типы полей

### 1. **Текстовые поля**
```python
{ 'key': 'url', 'label': 'URL', 'type': 'text', 'placeholder': 'https://example.com' }
```

### 2. **Поля паролей**
```python
{ 'key': 'password', 'label': 'Пароль', 'type': 'password', 'placeholder': 'введите пароль' }
```

### 3. **Числовые поля**
```python
{ 'key': 'port', 'label': 'Порт', 'type': 'number', 'placeholder': '8080' }
```

### 4. **Чекбоксы**
```python
{ 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
```

## 🎯 Примеры реализации

### 1. **Jira MCP сервер**
```python
self.admin_fields = [
    { 'key': 'url', 'label': 'URL Jira', 'type': 'text', 'placeholder': 'https://your-domain.atlassian.net' },
    { 'key': 'username', 'label': 'Имя пользователя', 'type': 'text', 'placeholder': 'your-email@domain.com' },
    { 'key': 'api_token', 'label': 'API Token', 'type': 'password', 'placeholder': 'ваш API токен' },
    { 'key': 'project_key', 'label': 'Ключ проекта', 'type': 'text', 'placeholder': 'PROJ' },
    { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
]
```

### 2. **GitLab MCP сервер**
```python
self.admin_fields = [
    { 'key': 'url', 'label': 'URL GitLab', 'type': 'text', 'placeholder': 'https://gitlab.com' },
    { 'key': 'access_token', 'label': 'Access Token', 'type': 'password', 'placeholder': 'ваш access token' },
    { 'key': 'project_id', 'label': 'ID проекта', 'type': 'text', 'placeholder': '12345' },
    { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
]
```

### 3. **LDAP MCP сервер**
```python
self.admin_fields = [
    { 'key': 'ldap_url', 'label': 'URL сервера LDAP', 'type': 'text', 'placeholder': 'ldap://domain.local:389' },
    { 'key': 'domain', 'label': 'Домен', 'type': 'text', 'placeholder': 'domain.local' },
    { 'key': 'base_dn', 'label': 'Base DN', 'type': 'text', 'placeholder': 'CN=Users,DC=domain,DC=local' },
    { 'key': 'ldap_user', 'label': 'LDAP User', 'type': 'text', 'placeholder': 'service_account' },
    { 'key': 'ldap_password', 'label': 'LDAP Password', 'type': 'password', 'placeholder': 'пароль для service account' },
    { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
]
```

## 🔄 Процесс добавления нового MCP сервера

### 1. **Создание файла сервера**
```python
# mcp_servers/new_server.py
class NewFastMCPServer(BaseFastMCPServer):
    def __init__(self):
        super().__init__("new_server")
        
        # Настройки для админ-панели
        self.display_name = "New Server MCP"
        self.icon = "fas fa-rocket"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'url', 'label': 'URL сервера', 'type': 'text', 'placeholder': 'https://new-server.com' },
            { 'key': 'api_key', 'label': 'API ключ', 'type': 'password', 'placeholder': 'ваш API ключ' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
```

### 2. **Автоматическое обнаружение**
- Сервер автоматически обнаруживается системой
- Настройки загружаются в админ-панель
- Форма создается динамически

### 3. **Готово к использованию**
- Настройки доступны в админ-панели
- Конфигурация сохраняется в `app_config.json`
- Сервер готов к работе

## 🎨 Интерфейс админ-панели

### 1. **Главная страница MCP серверов**
- **Карточки серверов** - каждый сервер в отдельной карточке
- **Статус включения** - визуальные индикаторы
- **Кнопки настройки** - переход к индивидуальным настройкам

### 2. **Страница настройки сервера**
- **Динамическая форма** - поля создаются автоматически
- **Валидация** - проверка введенных данных
- **Тест подключения** - проверка работоспособности

### 3. **Навигация**
- **Хлебные крошки** - понятная навигация
- **Кнопка "Назад"** - возврат к списку серверов
- **Сохранение** - автоматическое обновление конфигурации

## 📈 Преимущества динамической системы

### ✅ **Автоматическое обнаружение**
- **Нет ручного кода** - серверы обнаруживаются автоматически
- **Мгновенное обновление** - новые серверы сразу доступны
- **Масштабируемость** - легко добавлять новые серверы

### ✅ **Единообразие**
- **Стандартизированный интерфейс** - все серверы используют одинаковый подход
- **Консистентность** - единый стиль настроек
- **Предсказуемость** - понятная структура

### ✅ **Гибкость**
- **Настраиваемые поля** - каждый сервер определяет свои поля
- **Разные типы** - поддержка различных типов полей
- **Расширяемость** - легко добавлять новые типы полей

### ✅ **Удобство разработки**
- **Минимум кода** - настройки определяются в одном месте
- **Автоматическая генерация** - формы создаются автоматически
- **Отладка** - простое тестирование новых серверов

## 🔧 Технические детали

### **Автоматическое обнаружение:**
```python
def get_discovered_servers() -> Dict[str, Any]:
    servers = {}
    servers_path = os.path.dirname(__file__)
    
    for filename in os.listdir(servers_path):
        if filename.endswith('.py') and filename not in ['__init__.py', 'base_fastmcp_server.py', 'server_discovery.py']:
            module_name = filename[:-3]
            full_module_name = f"mcp_servers.{module_name}"
            
            try:
                module = importlib.import_module(full_module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (name.endswith('MCPServer') or name.endswith('FastMCPServer')) and obj.__module__ == full_module_name:
                        server_key = name.lower().replace('fastmcp', '').replace('mcp', '').replace('server', '')
                        servers[server_key] = obj
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить модуль {full_module_name}: {e}")
    
    return servers
```

### **Получение настроек:**
```python
def get_admin_settings(self) -> Dict[str, Any]:
    server_name = self.__class__.__name__.lower().replace('fastmcp', '').replace('mcp', '').replace('server', '')
    
    settings = {
        'name': server_name,
        'display_name': getattr(self, 'display_name', f'{server_name.title()} MCP'),
        'description': getattr(self, 'description', f'MCP сервер для {server_name}'),
        'icon': getattr(self, 'icon', 'fas fa-server'),
        'category': getattr(self, 'category', 'mcp_servers'),
        'fields': getattr(self, 'admin_fields', []),
        'enabled': self.is_enabled()
    }
    
    return settings
```

## 🚨 Обработка ошибок

### 1. **Ошибки загрузки сервера**
```python
try:
    server_instance = create_server_instance(server_name)
    admin_settings = server_instance.get_admin_settings()
except Exception as e:
    logger.warning(f"⚠️ Не удалось загрузить настройки сервера {server_name}: {e}")
    # Добавляем базовые настройки
    mcp_servers_config[server_name] = {
        'name': server_name,
        'display_name': f'{server_name.title()} MCP',
        'description': f'MCP сервер для {server_name}',
        'icon': 'fas fa-server',
        'category': 'mcp_servers',
        'fields': [],
        'enabled': False,
        'config': {}
    }
```

### 2. **Ошибки API**
```javascript
try {
    const response = await fetch('/api/admin/config');
    const data = await response.json();
    // Обработка данных
} catch (error) {
    console.error('Ошибка загрузки конфигурации:', error);
    // Показываем сообщение об ошибке
}
```

## 🔮 Будущие улучшения

### **Возможные расширения:**
1. **Валидация полей** - проверка корректности введенных данных
2. **Условные поля** - показ полей в зависимости от других значений
3. **Группировка полей** - логическое разделение настроек
4. **Предустановки** - готовые конфигурации для быстрой настройки

### **Оптимизации:**
1. **Кэширование** - сохранение настроек для быстрого доступа
2. **Ленивая загрузка** - загрузка настроек по требованию
3. **Предварительная валидация** - проверка доступности серверов

## ✅ Заключение

Динамическая система настроек MCP серверов обеспечивает:

- **Автоматическое обнаружение** - новые серверы добавляются без изменения кода
- **Единообразный интерфейс** - все серверы используют одинаковый подход
- **Гибкость настройки** - каждый сервер определяет свои поля
- **Удобство разработки** - минимум кода для добавления нового сервера

**Теперь добавление нового MCP сервера сводится только к созданию файла с настройками админ-панели!** 🚀

## 📚 Документация:
- **Основная документация**: `docs/DYNAMIC_MCP_SETTINGS.md`
- **Автоматическое обнаружение**: `docs/AUTOMATIC_MCP_DISCOVERY.md`
- **Примеры серверов**: `examples/new_server_example.py`

**Система готова к использованию с полной поддержкой динамических настроек!** ✨
