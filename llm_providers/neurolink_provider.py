#!/usr/bin/env python3
"""
Neurolink API провайдер для LLM
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig
from llm_providers.base_provider import BaseLLMProvider

class NeurolinkProvider(BaseLLMProvider):
    """Neurolink API провайдер для Gemma-3-27b-it"""
    
    def _initialize_client(self):
        """Инициализирует HTTP клиент для Neurolink API"""
        # Захардкоженные настройки
        self.api_url = "http://neurolink.iek.local:8004/v1/chat/completions"
        self.api_key = "ARjgZphys9tBWYnnJl5UdnOeAubUCwzaAhEpRnFi1yE"
        self.model = "google/gemma-3-27b-it"
        self.temperature = 0.15
        self.max_tokens = 2048
        self.timeout = 30
        
        # Создаем HTTP сессию
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создает HTTP сессию"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def generate_response(self, messages: List[Dict[str, str]], temperature: float = -1, **kwargs) -> str:
        """Генерирует ответ через Neurolink API"""
        try:
            # Используем захардкоженную температуру или переданную
            temp = self.temperature if temperature == -1 else temperature
            
            # Подготавливаем данные для запроса
            payload = {
                "messages": messages,
                "temperature": temp,
                "stream": False,
                "max_tokens": kwargs.get('max_tokens', self.max_tokens)
            }
            
            # Подготавливаем заголовки
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Получаем сессию
            session = await self._get_session()
            
            # Выполняем запрос
            async with session.post(
                self.api_url,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # Извлекаем ответ из структуры API
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    content = response_data['choices'][0]['message']['content']
                    return content
                else:
                    raise Exception("Неожиданная структура ответа API")
            
        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка HTTP клиента: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка Neurolink API: {str(e)}")
    
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        try:
            # Для Neurolink API пока что просто генерируем обычный ответ
            # В будущем можно добавить поддержку function calling если API это поддерживает
            
            # Добавляем информацию об инструментах в системное сообщение
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg['content'])
            
            # Формируем сообщения для API
            api_messages = []
            if system_message:
                api_messages.append({"role": "system", "content": system_message})
            
            for msg in user_messages:
                api_messages.append({"role": "user", "content": msg})
            
            # Генерируем ответ
            response_text = await self.generate_response(api_messages, **kwargs)
            
            return {
                'action': 'respond',
                'message': response_text
            }
                
        except Exception as e:
            raise Exception(f"Ошибка Neurolink API с инструментами: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность Neurolink API"""
        try:
            # Простой тестовый запрос
            test_messages = [{"role": "user", "content": "test"}]
            response_text = await self.generate_response(test_messages, max_tokens=1)
            
            return {
                'status': 'healthy',
                'provider': 'neurolink',
                'model': self.model,
                'api_url': self.api_url
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'neurolink',
                'error': str(e),
                'api_url': self.api_url
            }
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для Neurolink API"""
        # Пока что возвращаем инструменты как есть
        # В будущем можно адаптировать под специфику API
        return tools
    
    async def close(self):
        """Закрывает HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Деструктор для закрытия сессии"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            # В деструкторе нельзя использовать await, поэтому просто закрываем синхронно
            try:
                asyncio.create_task(self.session.close())
            except:
                pass
