@echo off
echo 🚀 Запуск MCP Chat с pgAdmin...
echo.

echo 📦 Запуск Docker контейнеров...
docker-compose up -d

echo.
echo ⏳ Ожидание запуска сервисов...
timeout /t 10 /nobreak > nul

echo.
echo 🔍 Проверка статуса сервисов...
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ✅ Сервисы запущены!
echo.
echo 🌐 Доступные сервисы:
echo    MCP Chat App:    http://localhost:8000
echo    pgAdmin:         http://localhost:8080
echo    Ollama LLM:      http://localhost:11434
echo.
echo 📊 pgAdmin настройки:
echo    Email:    admin@mcp.local
echo    Пароль:   admin123
echo.
echo 🗄️ PostgreSQL настройки для pgAdmin:
echo    Host:     postgres-server
echo    Port:     5432
echo    Database: mcp_chat
echo    Username: mcp_user
echo    Password: mcp_password
echo.

echo 🐍 Запуск Python приложения...
python app.py
