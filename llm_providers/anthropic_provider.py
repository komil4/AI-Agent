#!/usr/bin/env python3
"""
Anthropic Claude провайдер для LLM
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

try:
    import anthropic
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude провайдер"""
    
    def _initialize_client(self):
        """Инициализирует Anthropic клиент"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic библиотека не установлена. Установите: pip install anthropic")
        
        self.client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через Anthropic API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Anthropic
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg['content'])
            
            user_content = "\n\n".join(user_messages)
            
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=params['max_tokens'],
                temperature=params['temperature'],
                system=system_message if system_message else None,
                messages=[{"role": "user", "content": user_content}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Ошибка Anthropic API: {str(e)}")
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Anthropic
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg['content'])
            
            user_content = "\n\n".join(user_messages)
            
            # Форматируем инструменты для Anthropic
            formatted_tools = self._format_tools(tools)
            
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=params['max_tokens'],
                temperature=params['temperature'],
                system=system_message if system_message else None,
                messages=[{"role": "user", "content": user_content}],
                tools=formatted_tools
            )
            
            # Проверяем, есть ли вызов инструмента
            if response.content and response.content[0].type == 'tool_use':
                tool_use = response.content[0]
                return {
                    'action': 'call_tool',
                    'server': tool_use.name.split('.')[0] if '.' in tool_use.name else 'unknown',
                    'tool': tool_use.name.split('.')[1] if '.' in tool_use.name else tool_use.name,
                    'arguments': tool_use.input
                }
            else:
                return {
                    'action': 'respond',
                    'message': response.content[0].text if response.content else "Нет ответа"
                }
                
        except Exception as e:
            raise Exception(f"Ошибка Anthropic API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Anthropic API"""
        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return {
                'status': 'healthy',
                'provider': 'anthropic',
                'model': self.config.model
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'anthropic',
                'error': str(e)
            }
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для Anthropic"""
        formatted_tools = []
        
        for tool in tools:
            server_name = tool.get('server', 'unknown')
            tool_name = tool['name']
            
            formatted_tool = {
                "name": f"{server_name}.{tool_name}",
                "description": tool['description'],
                "input_schema": tool.get('parameters', {})
            }
            formatted_tools.append(formatted_tool)
        
        return formatted_tools
