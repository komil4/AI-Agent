#!/usr/bin/env python3
"""
Главный файл запуска MCP AI Ассистента
"""

import uvicorn
import os
from app import app

if __name__ == "__main__":
    # Получаем настройки из переменных окружения
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print("🚀 Запуск MCP AI Ассистента...")
    print(f"📍 Адрес: http://{host}:{port}")
    print(f"🔧 Режим отладки: {'включен' if debug else 'выключен'}")
    print("📚 Документация API: http://localhost:8000/docs")
    print("⚙️ Админ-панель: http://localhost:8000/admin")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )
