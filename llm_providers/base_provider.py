#!/usr/bin/env python3
"""
Базовый класс для LLM провайдеров
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from config.llm_config import LLMConfig

class BaseLLMProvider(ABC):
    """Базовый класс для всех LLM провайдеров"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Инициализирует клиент для конкретного провайдера"""
        pass
    
    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], temperature:float = -1, **kwargs) -> str:
        """Генерирует ответ на основе сообщений"""
        pass
    
    @abstractmethod
    async def generate_with_tools(self, user_message: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        pass
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность провайдера"""
        pass
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Форматирует сообщения для конкретного провайдера"""
        return messages
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Форматирует инструменты для конкретного провайдера"""
        return tools
    
    def _get_model_params(self, **kwargs) -> Dict[str, Any]:
        """Получает параметры модели"""
        params = {
            'temperature': kwargs.get('temperature', self.config.temperature),
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
            'timeout': kwargs.get('timeout', self.config.timeout)
        }
        
        # Добавляем дополнительные параметры из конфигурации
        if self.config.additional_params:
            params.update(self.config.additional_params)
        
        # Добавляем параметры из kwargs
        params.update(kwargs)
        
        return params
