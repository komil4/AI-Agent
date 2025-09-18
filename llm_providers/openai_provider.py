#!/usr/bin/env python3
"""
OpenAI провайдер для LLM
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

try:
    from openai import OpenAI
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class OpenAIProvider(BaseLLMProvider):
    """OpenAI провайдер"""
    
    def _initialize_client(self):
        """Инициализирует OpenAI клиент"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI библиотека не установлена. Установите: pip install openai")
        
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через OpenAI API"""
        try:
            params = self._get_model_params(**kwargs)
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=self._format_messages(messages),
                temperature=params['temperature'],
                max_tokens=params['max_tokens']
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Ошибка OpenAI API: {str(e)}")
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Форматируем инструменты для OpenAI
            formatted_tools = self._format_tools(tools)
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=self._format_messages(messages),
                tools=formatted_tools,
                tool_choice="auto",
                temperature=params['temperature'],
                max_tokens=params['max_tokens']
            )
            
            message = response.choices[0].message
            
            # Проверяем, есть ли вызов инструмента
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                return {
                    'action': 'call_tool',
                    'server': tool_call.function.name.split('.')[0] if '.' in tool_call.function.name else 'unknown',
                    'tool': tool_call.function.name.split('.')[1] if '.' in tool_call.function.name else tool_call.function.name,
                    'arguments': json.loads(tool_call.function.arguments)
                }
            else:
                return {
                    'action': 'respond',
                    'message': message.content
                }
                
        except Exception as e:
            raise Exception(f"Ошибка OpenAI API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return {
                'status': 'healthy',
                'provider': 'openai',
                'model': self.config.model
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'openai',
                'error': str(e)
            }
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для OpenAI"""
        formatted_tools = []
        
        for tool in tools:
            # Группируем инструменты по серверам
            server_name = tool.get('server', 'unknown')
            tool_name = tool['name']
            
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": f"{server_name}.{tool_name}",
                    "description": tool['description'],
                    "parameters": tool.get('parameters', {})
                }
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
