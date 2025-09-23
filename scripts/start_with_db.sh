#!/bin/bash

echo "Запуск MCP Chat с PostgreSQL..."

# Проверяем, установлен ли Docker
if ! command -v docker &> /dev/null; then
    echo "Ошибка: Docker не установлен"
    exit 1
fi

# Запускаем контейнеры
echo "Запуск контейнеров..."
docker-compose up -d

# Ждем запуска PostgreSQL
echo "Ожидание запуска PostgreSQL..."
sleep 10

# Проверяем подключение к базе данных
echo "Проверка подключения к базе данных..."
if ! docker exec postgres-server pg_isready -U mcp_user -d mcp_chat; then
    echo "Ошибка: PostgreSQL не готов к подключению"
    exit 1
fi

echo "PostgreSQL запущен успешно!"

# Устанавливаем зависимости Python
echo "Установка зависимостей Python..."
pip install -r requirements.txt

# Запускаем приложение
echo "Запуск приложения..."
python app.py
