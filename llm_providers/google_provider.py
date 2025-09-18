#!/usr/bin/env python3
"""
Google Gemini провайдер для LLM
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

class GoogleProvider(BaseLLMProvider):
    """Google Gemini провайдер"""
    
    def _initialize_client(self):
        """Инициализирует Google Gemini клиент"""
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Generative AI библиотека не установлена. Установите: pip install google-generativeai")
        
        genai.configure(api_key=self.config.api_key)
        self.client = genai.GenerativeModel(self.config.model)
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через Google Gemini API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Конвертируем сообщения в формат Gemini
            prompt = self._format_messages_for_gemini(messages)
            
            response = await self.client.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=params['temperature'],
                    max_output_tokens=params['max_tokens']
                )
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Ошибка Google Gemini API: {str(e)}")
    
    async def generate_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Форматируем инструменты для Gemini
            formatted_tools = self._format_tools(tools)
            
            # Создаем промпт с инструментами
            prompt = self._format_messages_for_gemini(messages)
            tools_prompt = self._format_tools_prompt(formatted_tools)
            
            full_prompt = f"{prompt}\n\nДоступные инструменты:\n{tools_prompt}\n\nОтветь в формате JSON с полями: action (call_tool или respond), server, tool, arguments (если call_tool), message (если respond)."
            
            response = await self.client.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=params['temperature'],
                    max_output_tokens=params['max_tokens']
                )
            )
            
            # Парсим JSON ответ
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                return {
                    'action': 'respond',
                    'message': response.text
                }
                
        except Exception as e:
            raise Exception(f"Ошибка Google Gemini API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Google Gemini API"""
        try:
            response = await self.client.generate_content_async("test")
            return {
                'status': 'healthy',
                'provider': 'google',
                'model': self.config.model
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'google',
                'error': str(e)
            }
    
    def _format_messages_for_gemini(self, messages: List[Dict[str, str]]) -> str:
        """Форматирует сообщения для Gemini"""
        formatted = []
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                formatted.append(f"System: {content}")
            elif role == 'user':
                formatted.append(f"User: {content}")
            elif role == 'assistant':
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def _format_tools_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Форматирует инструменты в текстовый промпт для Gemini"""
        formatted = []
        
        for tool in tools:
            server_name = tool.get('server', 'unknown')
            tool_name = tool['name']
            description = tool['description']
            parameters = tool.get('parameters', {})
            
            tool_desc = f"- {server_name}.{tool_name}: {description}"
            if parameters.get('properties'):
                tool_desc += f"\n  Параметры: {list(parameters['properties'].keys())}"
            
            formatted.append(tool_desc)
        
        return "\n".join(formatted)
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для Gemini (возвращает как есть для текстового промпта)"""
        return tools
