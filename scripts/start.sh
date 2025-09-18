#!/bin/bash

echo "🤖 MCP AI Ассистент"
echo "==================="

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен"
    echo "💡 Установите Python 3.8+"
    exit 1
fi

echo "✅ Python доступен"

# Проверяем зависимости
if [ ! -f "requirements.txt" ]; then
    echo "❌ Файл requirements.txt не найден"
    exit 1
fi

echo "📦 Устанавливаем зависимости..."
pip3 install -r requirements.txt

# Проверяем конфигурацию
if [ ! -f "config_files/app_config.json" ]; then
    echo "⚠️ Файл конфигурации не найден"
    echo "📋 Копируем пример конфигурации..."
    cp config_files/app_config.json.example config_files/app_config.json
    echo "✏️ Отредактируйте config_files/app_config.json с вашими настройками"
fi

# Запускаем приложение
echo "🚀 Запускаем приложение..."
echo "🌐 Приложение будет доступно по адресу: http://localhost:8000"
echo "📚 API документация: http://localhost:8000/docs"
echo "⚙️ Админ-панель: http://localhost:8000/admin"
echo "⏹️ Для остановки нажмите Ctrl+C"
echo "==================="

python3 main.py
