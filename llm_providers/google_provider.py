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
        self.model = genai.GenerativeModel(self.config.model)
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через Google Gemini API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Форматируем сообщения для Gemini
            formatted_messages = self._format_messages(messages)
            
            # Конвертируем в формат Gemini
            prompt = ""
            for msg in formatted_messages:
                if msg['role'] == 'system':
                    prompt += f"System: {msg['content']}\n\n"
                elif msg['role'] == 'user':
                    prompt += f"User: {msg['content']}\n\n"
                elif msg['role'] == 'assistant':
                    prompt += f"Assistant: {msg['content']}\n\n"
            
            # Генерируем ответ
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=params['temperature'],
                    max_output_tokens=params['max_tokens']
                )
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Ошибка Google Gemini API: {str(e)}")
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            # Для Gemini используем простой подход - возвращаем текстовый ответ
            # с описанием доступных инструментов
            response = await self.generate_response(messages, **kwargs)
            
            # Простая логика определения необходимости вызова инструмента
            if any(keyword in user_message.lower() for keyword in ['создать', 'найти', 'поиск', 'список', 'показать', 'получить']):
                # Определяем подходящий инструмент
                if any(keyword in user_message.lower() for keyword in ['jira', 'задача', 'тикет']):
                    return {
                        'action': 'call_tool',
                        'server': 'jira',
                        'tool': 'search_issues',
                        'arguments': {'jql': f'text ~ "{user_message}"', 'max_results': 5}
                    }
                elif any(keyword in user_message.lower() for keyword in ['gitlab', 'проект', 'коммит']):
                    return {
                        'action': 'call_tool',
                        'server': 'gitlab',
                        'tool': 'list_projects',
                        'arguments': {'search': user_message, 'per_page': 5}
                    }
                elif any(keyword in user_message.lower() for keyword in ['confluence', 'страница', 'документ']):
                    return {
                        'action': 'call_tool',
                        'server': 'confluence',
                        'tool': 'search_pages',
                        'arguments': {'query': user_message, 'limit': 5}
                    }
            
            return {
                'action': 'respond',
                'message': response
            }
                
        except Exception as e:
            raise Exception(f"Ошибка Google Gemini API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Google Gemini API"""
        try:
            # Простая проверка доступности
            response = await asyncio.to_thread(
                self.model.generate_content,
                "test",
                generation_config=genai.types.GenerationConfig(max_output_tokens=1)
            )
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
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Форматирует сообщения для Gemini"""
        # Gemini использует стандартный формат сообщений
        return messages