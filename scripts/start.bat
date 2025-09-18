@echo off
echo 🤖 MCP AI Ассистент
echo ===================

echo 🔍 Проверяем Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не установлен
    echo 💡 Установите Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python доступен

echo 📦 Устанавливаем зависимости...
pip install -r requirements.txt

echo 🔍 Проверяем конфигурацию...
if not exist "config_files\app_config.json" (
    echo ⚠️ Файл конфигурации не найден
    echo 📋 Копируем пример конфигурации...
    copy "config_files\app_config.json.example" "config_files\app_config.json"
    echo ✏️ Отредактируйте config_files\app_config.json с вашими настройками
)

echo 🚀 Запускаем приложение...
echo 🌐 Приложение будет доступно по адресу: http://localhost:8000
echo 📚 API документация: http://localhost:8000/docs
echo ⚙️ Админ-панель: http://localhost:8000/admin
echo ⏹️ Для остановки нажмите Ctrl+C
echo ===================

python main.py

pause
