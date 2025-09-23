@echo off
echo Запуск MCP Chat с PostgreSQL...

REM Проверяем, установлен ли Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка: Docker не установлен или не запущен
    pause
    exit /b 1
)

REM Запускаем контейнеры
echo Запуск контейнеров...
docker-compose up -d

REM Ждем запуска PostgreSQL
echo Ожидание запуска PostgreSQL...
timeout /t 10 /nobreak >nul

REM Проверяем подключение к базе данных
echo Проверка подключения к базе данных...
docker exec postgres-server pg_isready -U mcp_user -d mcp_chat
if %errorlevel% neq 0 (
    echo Ошибка: PostgreSQL не готов к подключению
    pause
    exit /b 1
)

echo PostgreSQL запущен успешно!

REM Устанавливаем зависимости Python
echo Установка зависимостей Python...
pip install -r requirements.txt

REM Запускаем приложение
echo Запуск приложения...
python app.py

pause
