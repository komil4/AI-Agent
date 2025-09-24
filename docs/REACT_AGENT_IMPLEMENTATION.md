# Реализация ReAct агента с LangGraph

## 📋 Обзор

Реализован ReAct (Reasoning and Acting) агент с использованием LangGraph для последовательного выполнения инструментов MCP серверов до получения конечного результата.

## 🔧 Архитектура

### 1. **ReAct агент**
- **Reasoning** - анализ задачи и планирование действий
- **Acting** - выполнение инструментов для получения данных
- **Iterative** - повторение цикла до достижения цели

### 2. **LangGraph интеграция**
- **StateGraph** - управление состоянием агента
- **Conditional edges** - условные переходы между узлами
- **Tool execution** - выполнение инструментов MCP серверов

### 3. **Модульная структура**
```
├── react_agent.py              # Основной ReAct агент
├── mcp_client.py              # Интеграция с MCP клиентом
├── app.py                     # Поддержка в API
├── models.py                  # Модель ChatMessage с флагом use_react
└── docs/REACT_AGENT_IMPLEMENTATION.md
```

## 🚀 Как это работает

### 1. **Инициализация агента**
```python
class ReActAgent:
    def __init__(self, mcp_client, llm_client, max_iterations: int = 10):
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.tools = []
        self.graph = None
        self._initialize_graph()
```

### 2. **Создание графа состояний**
```python
def _initialize_graph(self):
    # Создаем граф состояний
    workflow = StateGraph(AgentState)
    
    # Добавляем узлы
    workflow.add_node("agent", self._agent_node)
    workflow.add_node("tools", self._tools_node)
    
    # Добавляем условные переходы
    workflow.add_conditional_edges(
        "agent",
        self._should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "agent")
    workflow.set_entry_point("agent")
    self.graph = workflow.compile()
```

### 3. **Состояние агента**
```python
class AgentState(TypedDict):
    messages: Annotated[List[Any], "Список сообщений в диалоге"]
    user_context: Dict[str, Any]
    max_iterations: int
    current_iteration: int
    final_result: Optional[str]
```

## 🔄 Цикл ReAct

### 1. **Reasoning (Рассуждение)**
```python
def _agent_node(self, state: AgentState) -> AgentState:
    # Создаем LLM с инструментами
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    llm_with_tools = llm.bind_tools(self.tools)
    
    # Получаем ответ от LLM
    response = llm_with_tools.invoke(llm_messages)
    
    # Создаем сообщение агента
    agent_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
    state["messages"].append(agent_message)
    
    return state
```

### 2. **Acting (Действие)**
```python
def _tools_node(self, state: AgentState) -> AgentState:
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Находим инструмент
            tool = next((t for t in self.tools if t.name == tool_name), None)
            
            if tool:
                # Выполняем инструмент
                result = tool._run(**tool_args)
                
                # Создаем сообщение с результатом
                tool_message = ToolMessage(content=result, tool_call_id=tool_call.id)
                tool_results.append(tool_message)
    
    state["messages"].extend(tool_results)
    return state
```

### 3. **Условные переходы**
```python
def _should_continue(self, state: AgentState) -> str:
    # Проверяем лимит итераций
    if current_iteration >= state["max_iterations"]:
        return "end"
    
    # Если есть вызовы инструментов, продолжаем
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "continue"
    
    # Если агент дал финальный ответ, заканчиваем
    if "финальный ответ" in content.lower():
        return "end"
    
    return "continue"
```

## 🛠️ Интеграция с MCP

### 1. **Создание инструментов**
```python
def _create_tools_from_mcp(self) -> List[BaseTool]:
    tools = []
    all_tools = self.mcp_client.get_all_tools()
    
    for tool_info in all_tools:
        tool = MCPTool(
            name=f"{tool_info['server']}.{tool_info['name']}",
            description=tool_info['description'],
            parameters=tool_info['parameters'],
            mcp_client=self.mcp_client,
            server_name=tool_info['server']
        )
        tools.append(tool)
    
    return tools
```

### 2. **Обертка MCP инструментов**
```python
class MCPTool(BaseTool):
    def _run(self, **kwargs) -> str:
        # Вызываем инструмент через MCP клиент
        result = self.mcp_client.call_tool_builtin(
            self.server_name,
            self.name,
            kwargs
        )
        
        if result.get('success', False):
            return json.dumps(result.get('data', {}), ensure_ascii=False, indent=2)
        else:
            return f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"
```

## 📡 API интеграция

### 1. **Обновленная модель**
```python
class ChatMessage(BaseModel):
    message: str
    use_react: bool = False  # Флаг для использования ReAct агента
```

### 2. **Обработка в эндпоинте**
```python
# Определяем, нужно ли использовать ReAct агента
use_react = chat_message.use_react if hasattr(chat_message, 'use_react') else False

# Добавляем флаг в контекст
user_context = {
    'user': {...},
    'session_id': active_session.id,
    'chat_history': session_history,
    'use_react': use_react
}
```

### 3. **Выбор метода обработки**
```python
async def process_message_with_llm(self, message: str, user_context: dict = None) -> str:
    use_react = user_context.get('use_react', False) if user_context else False
    
    if use_react:
        return await self._process_with_react(message, user_context)
    else:
        return await self._process_with_simple_llm(message, user_context)
```

## 🎯 Примеры использования

### 1. **Простой запрос (без ReAct)**
```json
{
  "message": "Создай задачу в Jira",
  "use_react": false
}
```

### 2. **Сложный запрос (с ReAct)**
```json
{
  "message": "Найди все задачи проекта ABC, создай отчет и отправь его по email",
  "use_react": true
}
```

### 3. **Многошаговая задача**
```json
{
  "message": "Получи список пользователей из LDAP, создай для них задачи в Jira и добавь комментарии к существующим задачам",
  "use_react": true
}
```

## 📊 Преимущества ReAct

### ✅ **Последовательное выполнение**
- Агент может выполнять несколько инструментов подряд
- Каждый шаг строится на результатах предыдущего
- Автоматическое планирование последовательности действий

### ✅ **Интеллектуальное рассуждение**
- LLM анализирует результаты каждого инструмента
- Принимает решения о следующих действиях
- Адаптируется к изменяющимся условиям

### ✅ **Ограничения безопасности**
- Максимальное количество итераций
- Контроль времени выполнения
- Обработка ошибок на каждом шаге

### ✅ **Прозрачность**
- Полная история выполнения
- Логирование каждого шага
- Возможность отладки процесса

## 🔧 Конфигурация

### 1. **Параметры агента**
```python
react_agent = ReActAgent(
    mcp_client=mcp_client,
    llm_client=llm_client,
    max_iterations=10  # Максимум итераций
)
```

### 2. **Настройки LLM**
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,  # Низкая температура для стабильности
    api_key=api_key
)
```

### 3. **Системный промпт**
```python
system_message = """
Ты - полезный AI ассистент, который может выполнять инструменты для решения задач пользователя.

Инструкции:
1. Анализируй задачу пользователя
2. Выбери подходящий инструмент для выполнения
3. Если результат инструмента требует дополнительных действий, используй другие инструменты
4. Продолжай до тех пор, пока не получишь полный ответ на вопрос пользователя
5. Максимум итераций: {max_iterations}

Отвечай на русском языке.
"""
```

## 🚨 Обработка ошибок

### 1. **Ошибки инструментов**
```python
try:
    result = tool._run(**tool_args)
except Exception as e:
    error_message = ToolMessage(
        content=f"Ошибка выполнения инструмента: {str(e)}",
        tool_call_id=tool_call.id
    )
    tool_results.append(error_message)
```

### 2. **Ошибки агента**
```python
try:
    response = llm_with_tools.invoke(llm_messages)
except Exception as e:
    logger.error(f"❌ Ошибка в узле агента: {e}")
    state["final_result"] = f"Ошибка агента: {str(e)}"
    return state
```

### 3. **Fallback механизм**
```python
if not react_agent or not react_agent.is_available():
    logger.warning("⚠️ ReAct агент недоступен, используем простую обработку")
    return await self._process_with_simple_llm(message, user_context)
```

## 📈 Мониторинг и логирование

### 1. **Метрики выполнения**
```python
return {
    "success": True,
    "result": final_result,
    "iterations": final_state["current_iteration"],
    "messages": len(messages),
    "tools_used": len([msg for msg in messages if isinstance(msg, ToolMessage)])
}
```

### 2. **Логирование**
```python
logger.info(f"🚀 Запуск ReAct агента для запроса: {query[:100]}...")
logger.info(f"✅ ReAct агент выполнил {result['iterations']} итераций, использовал {result['tools_used']} инструментов")
```

## 🔮 Будущие улучшения

### **Возможные расширения:**
1. **Параллельное выполнение** - одновременное выполнение независимых инструментов
2. **Кэширование результатов** - сохранение результатов для повторного использования
3. **Адаптивные лимиты** - динамическое изменение количества итераций
4. **Пользовательские промпты** - настройка поведения агента

### **Оптимизации:**
1. **Предварительная валидация** - проверка доступности инструментов
2. **Оптимизация последовательности** - выбор наиболее эффективного порядка выполнения
3. **Сжатие контекста** - уменьшение размера передаваемых данных

## ✅ Заключение

ReAct агент с LangGraph обеспечивает:

- **Интеллектуальное выполнение** - LLM принимает решения о следующих действиях
- **Последовательность** - инструменты выполняются в логическом порядке
- **Гибкость** - адаптация к различным типам задач
- **Безопасность** - ограничения и контроль выполнения
- **Прозрачность** - полная история выполнения

**Теперь система может выполнять сложные многошаговые задачи, используя несколько инструментов подряд!** 🚀
