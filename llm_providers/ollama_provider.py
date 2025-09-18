#!/usr/bin/env python3
"""
Ollama провайдер для LLM
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """Ollama провайдер"""
    
    def _initialize_client(self):
        """Инициализирует Ollama клиент"""
        self.base_url = self.config.base_url or "http://localhost:11434"
        self.model = self.config.model or "llama3.1:8b"
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через Ollama API"""
        try:
            params = self._get_model_params(**kwargs)
            
            # Форматируем сообщения для Ollama
            formatted_messages = self._format_messages(messages)
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "temperature": params['temperature'],
                        "num_predict": params['max_tokens']
                    }
                }
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=params['timeout'])
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['message']['content']
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            raise Exception(f"Ошибка Ollama API: {str(e)}")
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            # Для Ollama используем простой подход - возвращаем текстовый ответ
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
            raise Exception(f"Ошибка Ollama API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Ollama API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return {
                            'status': 'healthy',
                            'provider': 'ollama',
                            'model': self.model
                        }
                    else:
                        return {
                            'status': 'unhealthy',
                            'provider': 'ollama',
                            'error': f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'ollama',
                'error': str(e)
            }
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Форматирует сообщения для Ollama"""
        # Ollama использует стандартный формат сообщений
        return messages