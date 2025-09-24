#!/usr/bin/env python3
"""
Пример использования ReAct агента
Демонстрирует возможности последовательного выполнения инструментов
"""

import asyncio
import json
from typing import Dict, Any

# Примеры запросов для ReAct агента
REACT_EXAMPLES = {
    "simple_task": {
        "message": "Создай задачу в Jira с названием 'Тестовая задача'",
        "use_react": True,
        "description": "Простая задача - создание одной задачи в Jira"
    },
    
    "multi_step_task": {
        "message": "Найди все задачи проекта ABC в Jira, создай отчет и добавь комментарий к первой задаче",
        "use_react": True,
        "description": "Многошаговая задача - поиск, создание отчета, добавление комментария"
    },
    
    "complex_workflow": {
        "message": "Получи список пользователей из LDAP, создай для каждого задачу в Jira, затем получи детали всех созданных задач",
        "use_react": True,
        "description": "Сложный workflow - LDAP -> Jira -> детали задач"
    },
    
    "cross_service_task": {
        "message": "Создай задачу в Jira, затем создай merge request в GitLab для проекта, связанного с этой задачей",
        "use_react": True,
        "description": "Межсервисная задача - Jira + GitLab"
    },
    
    "data_analysis": {
        "message": "Получи все задачи из Jira, проанализируй их статусы, создай диаграмму и сохрани в Confluence",
        "use_react": True,
        "description": "Анализ данных - Jira -> анализ -> Confluence"
    }
}

# Примеры без ReAct (для сравнения)
SIMPLE_EXAMPLES = {
    "single_tool": {
        "message": "Создай задачу в Jira с названием 'Простая задача'",
        "use_react": False,
        "description": "Одиночный инструмент без ReAct"
    },
    
    "direct_query": {
        "message": "Покажи список проектов в Jira",
        "use_react": False,
        "description": "Прямой запрос без ReAct"
    }
}

async def demonstrate_react_agent():
    """Демонстрирует работу ReAct агента"""
    print("🚀 Демонстрация ReAct агента")
    print("=" * 50)
    
    # Здесь должен быть реальный код для демонстрации
    # В реальном приложении это будет выглядеть так:
    
    for example_name, example in REACT_EXAMPLES.items():
        print(f"\n📋 Пример: {example_name}")
        print(f"Описание: {example['description']}")
        print(f"Запрос: {example['message']}")
        print(f"ReAct: {'Да' if example['use_react'] else 'Нет'}")
        
        # В реальном коде здесь был бы вызов API:
        # response = await chat_api(example['message'], use_react=example['use_react'])
        # print(f"Результат: {response}")
        
        print("✅ Пример готов к выполнению")

def create_api_request_examples():
    """Создает примеры API запросов для тестирования"""
    
    print("\n🌐 Примеры API запросов")
    print("=" * 50)
    
    for example_name, example in REACT_EXAMPLES.items():
        print(f"\n📡 {example_name.upper()}")
        print("POST /api/chat")
        print("Content-Type: application/json")
        print()
        print(json.dumps({
            "message": example["message"],
            "use_react": example["use_react"]
        }, ensure_ascii=False, indent=2))
        print()

def create_curl_examples():
    """Создает примеры curl команд"""
    
    print("\n🔧 Примеры curl команд")
    print("=" * 50)
    
    for example_name, example in REACT_EXAMPLES.items():
        print(f"\n📡 {example_name.upper()}")
        
        curl_command = f"""curl -X POST "http://localhost:8000/api/chat" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{json.dumps({
            "message": example["message"],
            "use_react": example["use_react"]
        }, ensure_ascii=False)}'"""
        
        print(curl_command)
        print()

def create_javascript_examples():
    """Создает примеры JavaScript кода"""
    
    print("\n💻 Примеры JavaScript кода")
    print("=" * 50)
    
    js_code = """
// Пример использования ReAct агента через JavaScript

async function sendChatMessage(message, useReact = false) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify({
            message: message,
            use_react: useReact
        })
    });
    
    const result = await response.json();
    return result;
}

// Примеры использования
"""
    
    print(js_code)
    
    for example_name, example in REACT_EXAMPLES.items():
        js_example = f"""
// {example_name.upper()}
// {example['description']}
const {example_name} = await sendChatMessage(
    "{example['message']}", 
    {str(example['use_react']).lower()}
);
console.log('Результат:', {example_name}.response);
"""
        print(js_example)

def create_python_examples():
    """Создает примеры Python кода"""
    
    print("\n🐍 Примеры Python кода")
    print("=" * 50)
    
    python_code = """
import requests
import json

class ChatClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
    
    def send_message(self, message, use_react=False):
        headers = {
            'Content-Type': 'application/json'
        }
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        data = {
            'message': message,
            'use_react': use_react
        }
        
        response = requests.post(
            f'{self.base_url}/api/chat',
            headers=headers,
            json=data
        )
        
        return response.json()

# Создаем клиент
client = ChatClient(token="YOUR_TOKEN")
"""
    
    print(python_code)
    
    for example_name, example in REACT_EXAMPLES.items():
        python_example = f"""
# {example_name.upper()}
# {example['description']}
result = client.send_message(
    "{example['message']}", 
    use_react={example['use_react']}
)
print(f"Результат: {{result['response']}}")
"""
        print(python_example)

def create_workflow_diagram():
    """Создает диаграмму workflow ReAct агента"""
    
    print("\n📊 Диаграмма workflow ReAct агента")
    print("=" * 50)
    
    diagram = """
┌─────────────────┐
│   Пользователь  │
│   отправляет    │
│   запрос        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   API Endpoint  │
│   /api/chat     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  use_react =    │
│     true?       │
└─────┬─────┬─────┘
      │     │
      ▼     ▼
┌─────────┐ ┌─────────────┐
│ Simple  │ │   ReAct     │
│   LLM   │ │   Agent     │
└─────────┘ └─────┬───────┘
                  │
                  ▼
         ┌─────────────────┐
         │   LangGraph     │
         │   StateGraph    │
         └─────┬───────┬───┘
               │       │
               ▼       ▼
    ┌─────────────┐ ┌─────────────┐
    │   Agent     │ │   Tools     │
    │   Node      │ │   Node      │
    │ (Reasoning) │ │ (Acting)    │
    └─────┬───────┘ └─────┬───────┘
          │               │
          │               ▼
          │    ┌─────────────────┐
          │    │   MCP Tools     │
          │    │   Execution     │
          │    └─────────────────┘
          │               │
          │               ▼
          │    ┌─────────────────┐
          │    │   Tool Results  │
          │    └─────────────────┘
          │               │
          └───────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   Continue?     │
         │   Decision      │
         └─────┬─────┬─────┘
               │     │
               ▼     ▼
         ┌─────────┐ ┌─────────────┐
         │   End   │ │  Continue   │
         │         │ │             │
         └─────────┘ └─────────────┘
"""
    
    print(diagram)

def main():
    """Главная функция демонстрации"""
    print("🎯 ReAct Agent - Примеры использования")
    print("=" * 60)
    
    # Демонстрация агента
    asyncio.run(demonstrate_react_agent())
    
    # Примеры API запросов
    create_api_request_examples()
    
    # Примеры curl команд
    create_curl_examples()
    
    # Примеры JavaScript кода
    create_javascript_examples()
    
    # Примеры Python кода
    create_python_examples()
    
    # Диаграмма workflow
    create_workflow_diagram()
    
    print("\n✅ Все примеры готовы!")
    print("\n📚 Дополнительная информация:")
    print("- Документация: docs/REACT_AGENT_IMPLEMENTATION.md")
    print("- API документация: http://localhost:8000/docs")
    print("- Тестирование: используйте примеры выше")

if __name__ == "__main__":
    main()
