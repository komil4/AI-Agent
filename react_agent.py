#!/usr/bin/env python3
"""
ReAct агент с использованием LangGraph для последовательного выполнения инструментов
"""

import json
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

# LangGraph импорты
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_core.tools import BaseTool
    from langchain_openai import ChatOpenAI
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Заглушки для типов
    StateGraph = Any
    END = Any
    ToolNode = Any
    HumanMessage = Any
    AIMessage = Any
    ToolMessage = Any
    BaseTool = Any
    ChatOpenAI = Any

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """Состояние ReAct агента"""
    messages: Annotated[List[Any], "Список сообщений в диалоге"]
    user_context: Dict[str, Any]
    max_iterations: int
    current_iteration: int
    final_result: Optional[str]

class MCPTool(BaseTool):
    """Обертка для MCP инструментов в LangChain формат"""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], 
                 mcp_client, server_name: str):
        super().__init__()
        self.name = name
        self.description = description
        self.parameters = parameters
        self.mcp_client = mcp_client
        self.server_name = server_name
    
    def _run(self, **kwargs) -> str:
        """Синхронный вызов инструмента"""
        try:
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
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения инструмента {self.name}: {e}")
            return f"Ошибка выполнения инструмента: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Асинхронный вызов инструмента"""
        try:
            # Вызываем инструмент через MCP клиент
            result = await self.mcp_client.call_tool_builtin(
                self.server_name,
                self.name,
                kwargs
            )
            
            if result.get('success', False):
                return json.dumps(result.get('data', {}), ensure_ascii=False, indent=2)
            else:
                return f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения инструмента {self.name}: {e}")
            return f"Ошибка выполнения инструмента: {str(e)}"

class ReActAgent:
    """ReAct агент для последовательного выполнения инструментов"""
    
    def __init__(self, mcp_client, llm_client, max_iterations: int = 10):
        """
        Инициализирует ReAct агента
        
        Args:
            mcp_client: MCP клиент для вызова инструментов
            llm_client: LLM клиент для принятия решений
            max_iterations: Максимальное количество итераций
        """
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.tools = []
        self.graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._initialize_graph()
        else:
            logger.warning("⚠️ LangGraph недоступен, ReAct агент отключен")
    
    def _initialize_graph(self):
        """Инициализирует граф LangGraph"""
        try:
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
            
            # Устанавливаем точку входа
            workflow.set_entry_point("agent")
            
            # Компилируем граф
            self.graph = workflow.compile()
            
            logger.info("✅ ReAct граф инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ReAct графа: {e}")
            self.graph = None
    
    def _create_tools_from_mcp(self) -> List[BaseTool]:
        """Создает LangChain инструменты из MCP серверов"""
        tools = []
        
        try:
            # Получаем все доступные инструменты
            all_tools = self.mcp_client.get_all_tools()
            
            for tool_info in all_tools:
                try:
                    # Создаем LangChain инструмент
                    tool = MCPTool(
                        name=f"{tool_info['server']}.{tool_info['name']}",
                        description=tool_info['description'],
                        parameters=tool_info['parameters'],
                        mcp_client=self.mcp_client,
                        server_name=tool_info['server']
                    )
                    tools.append(tool)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось создать инструмент {tool_info.get('name', 'unknown')}: {e}")
            
            logger.info(f"✅ Создано {len(tools)} LangChain инструментов")
            return tools
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания инструментов: {e}")
            return []
    
    def _agent_node(self, state: AgentState) -> AgentState:
        """Узел агента - принимает решения о следующих действиях"""
        try:
            messages = state["messages"]
            current_iteration = state["current_iteration"]
            
            # Проверяем лимит итераций
            if current_iteration >= state["max_iterations"]:
                state["final_result"] = "Достигнут лимит итераций. Задача не выполнена."
                return state
            
            # Создаем LLM с инструментами
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                api_key=self.llm_client.config_manager.get_service_config('openai').get('api_key')
            )
            
            # Привязываем инструменты к LLM
            llm_with_tools = llm.bind_tools(self.tools)
            
            # Формируем системное сообщение
            system_message = f"""
Ты - полезный AI ассистент, который может выполнять инструменты для решения задач пользователя.

Инструкции:
1. Анализируй задачу пользователя
2. Выбери подходящий инструмент для выполнения
3. Если результат инструмента требует дополнительных действий, используй другие инструменты
4. Продолжай до тех пор, пока не получишь полный ответ на вопрос пользователя
5. Максимум итераций: {state["max_iterations"]}

Текущая итерация: {current_iteration + 1}

Отвечай на русском языке.
"""
            
            # Создаем сообщения для LLM
            llm_messages = [{"role": "system", "content": system_message}]
            
            # Добавляем историю диалога
            for msg in messages:
                if hasattr(msg, 'content'):
                    llm_messages.append({"role": msg.type, "content": msg.content})
            
            # Получаем ответ от LLM
            response = llm_with_tools.invoke(llm_messages)
            
            # Создаем сообщение агента
            agent_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
            state["messages"].append(agent_message)
            state["current_iteration"] += 1
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Ошибка в узле агента: {e}")
            state["final_result"] = f"Ошибка агента: {str(e)}"
            return state
    
    def _tools_node(self, state: AgentState) -> AgentState:
        """Узел инструментов - выполняет выбранные инструменты"""
        try:
            messages = state["messages"]
            last_message = messages[-1]
            
            # Проверяем, есть ли вызовы инструментов
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                tool_results = []
                
                for tool_call in last_message.tool_calls:
                    try:
                        # Извлекаем информацию о вызове
                        tool_name = tool_call.name
                        tool_args = tool_call.args
                        
                        # Находим соответствующий инструмент
                        tool = next((t for t in self.tools if t.name == tool_name), None)
                        
                        if tool:
                            # Выполняем инструмент
                            result = tool._run(**tool_args)
                            
                            # Создаем сообщение с результатом
                            tool_message = ToolMessage(
                                content=result,
                                tool_call_id=tool_call.id
                            )
                            tool_results.append(tool_message)
                            
                        else:
                            error_message = ToolMessage(
                                content=f"Инструмент {tool_name} не найден",
                                tool_call_id=tool_call.id
                            )
                            tool_results.append(error_message)
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка выполнения инструмента: {e}")
                        error_message = ToolMessage(
                            content=f"Ошибка выполнения инструмента: {str(e)}",
                            tool_call_id=tool_call.id
                        )
                        tool_results.append(error_message)
                
                # Добавляем результаты в состояние
                state["messages"].extend(tool_results)
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Ошибка в узле инструментов: {e}")
            return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Определяет, следует ли продолжить выполнение"""
        try:
            messages = state["messages"]
            current_iteration = state["current_iteration"]
            
            # Проверяем лимит итераций
            if current_iteration >= state["max_iterations"]:
                return "end"
            
            # Проверяем последнее сообщение агента
            last_message = messages[-1]
            
            # Если есть вызовы инструментов, продолжаем
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "continue"
            
            # Если агент дал финальный ответ, заканчиваем
            if hasattr(last_message, 'content'):
                content = last_message.content.lower()
                if any(phrase in content for phrase in ["финальный ответ", "задача выполнена", "готово", "завершено"]):
                    return "end"
            
            # По умолчанию продолжаем
            return "continue"
            
        except Exception as e:
            logger.error(f"❌ Ошибка определения продолжения: {e}")
            return "end"
    
    def _format_tools_for_prompt(self) -> str:
        """Форматирует инструменты для промпта"""
        tools_text = []
        
        for tool in self.tools:
            tools_text.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(tools_text)
    
    async def process_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Обрабатывает запрос пользователя с использованием ReAct
        
        Args:
            query: Запрос пользователя
            user_context: Контекст пользователя
            
        Returns:
            Результат обработки
        """
        try:
            if not LANGGRAPH_AVAILABLE:
                return {
                    "success": False,
                    "error": "LangGraph недоступен",
                    "result": "ReAct агент отключен"
                }
            
            if not self.graph:
                return {
                    "success": False,
                    "error": "ReAct граф не инициализирован",
                    "result": "Агент не готов к работе"
                }
            
            # Создаем инструменты из MCP серверов
            self.tools = self._create_tools_from_mcp()
            
            if not self.tools:
                return {
                    "success": False,
                    "error": "Нет доступных инструментов",
                    "result": "Не удалось создать инструменты"
                }
            
            # Создаем начальное состояние
            initial_state = AgentState(
                messages=[HumanMessage(content=query)],
                user_context=user_context or {},
                max_iterations=self.max_iterations,
                current_iteration=0,
                final_result=None
            )
            
            # Запускаем граф
            logger.info(f"🚀 Запуск ReAct агента для запроса: {query[:100]}...")
            
            final_state = await self.graph.ainvoke(initial_state)
            
            # Извлекаем результат
            messages = final_state["messages"]
            final_result = final_state.get("final_result")
            
            if not final_result:
                # Берем последнее сообщение агента
                agent_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
                if agent_messages:
                    final_result = agent_messages[-1].content
                else:
                    final_result = "Не удалось получить результат"
            
            logger.info(f"✅ ReAct агент завершил работу")
            
            return {
                "success": True,
                "result": final_result,
                "iterations": final_state["current_iteration"],
                "messages": len(messages),
                "tools_used": len([msg for msg in messages if isinstance(msg, ToolMessage)])
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка ReAct агента: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": f"Ошибка обработки запроса: {str(e)}"
            }
    
    def is_available(self) -> bool:
        """Проверяет, доступен ли ReAct агент"""
        return LANGGRAPH_AVAILABLE and self.graph is not None

# Глобальный экземпляр ReAct агента
react_agent = None

def get_react_agent(mcp_client=None, llm_client=None) -> Optional[ReActAgent]:
    """Получает глобальный экземпляр ReAct агента"""
    global react_agent
    
    if react_agent is None and mcp_client and llm_client:
        react_agent = ReActAgent(mcp_client, llm_client)
    
    return react_agent
