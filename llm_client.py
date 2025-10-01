#!/usr/bin/env python3
"""
LLM клиент для работы с различными провайдерами
"""

import logging
from typing import Dict, Any, List, Optional
from llm_providers.provider_factory import LLMProviderFactory
from llm_providers.base_provider import BaseLLMProvider
from config.llm_config import LLMProvider, llm_config_manager
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class LLMClient:
    """Клиент для работы с LLM провайдерами"""
    
    def __init__(self):
        """Инициализирует LLM клиент"""
        self.config_manager = ConfigManager()
        self.provider = None
        self.llm_provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Инициализирует провайдер по умолчанию"""
        try:
            # Получаем провайдера по умолчанию
            default_provider = llm_config_manager.get_default_provider()
            logger.info(f"[INIT] Инициализация LLM провайдера: {default_provider.value}")
            
            # Создаем провайдер
            self.llm_provider = LLMProviderFactory.create_provider(default_provider)
            self.provider = default_provider
            
            logger.info(f"[OK] LLM провайдер инициализирован: {self.provider.value}")
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка инициализации LLM провайдера: {e}")
            self.provider = None
            self.llm_provider = None
    
    def is_connected(self) -> bool:
        """Проверяет подключение к LLM провайдеру"""
        if not self.llm_provider:
            return False
        
        try:
            # Проверяем здоровье провайдера
            import asyncio
            health = asyncio.run(self.llm_provider.check_health())
            return health.get('status') == 'healthy'
        except Exception as e:
            logger.error(f"[ERROR] Ошибка проверки подключения: {e}")
            return False
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Генерирует ответ через LLM провайдер"""
        if not self.llm_provider:
            raise Exception("LLM провайдер не инициализирован")
        
        try:
            return await self.llm_provider.generate_response(messages, **kwargs)
        except Exception as e:
            logger.error(f"[ERROR] Ошибка генерации ответа: {e}")
            raise
    
    async def generate_with_tools(
        self, 
        user_message: str, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]], 
        **kwargs
    ) -> Dict[str, Any]:
        """Генерирует ответ с поддержкой инструментов"""
        if not self.llm_provider:
            raise Exception("LLM провайдер не инициализирован")
        
        try:
            return await self.llm_provider.generate_with_tools(
                user_message, messages, tools, **kwargs
            )
        except Exception as e:
            logger.error(f"[ERROR] Ошибка генерации ответа с инструментами: {e}")
            raise
    
    def switch_provider(self, provider: LLMProvider):
        """Переключает на другой провайдер"""
        try:
            logger.info(f"[SWITCH] Переключение на провайдер: {provider.value}")
            
            # Создаем новый провайдер
            new_provider = LLMProviderFactory.create_provider(provider)
            
            # Закрываем старый провайдер
            if self.llm_provider and hasattr(self.llm_provider, 'close'):
                import asyncio
                asyncio.run(self.llm_provider.close())
            
            # Устанавливаем новый
            self.llm_provider = new_provider
            self.provider = provider
            
            logger.info(f"[OK] Переключение на провайдер {provider.value} завершено")
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка переключения провайдера: {e}")
            raise
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Возвращает список доступных провайдеров"""
        return llm_config_manager.get_available_providers()
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """Возвращает текущий провайдер"""
        return self.provider
    
    async def test_provider(self, provider: LLMProvider) -> Dict[str, Any]:
        """Тестирует указанный провайдер"""
        try:
            test_provider = LLMProviderFactory.create_provider(provider)
            health = await test_provider.check_health()
            
            # Закрываем тестовый провайдер
            if hasattr(test_provider, 'close'):
                await test_provider.close()
            
            return health
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка тестирования провайдера {provider.value}: {e}")
            return {
                'status': 'unhealthy',
                'provider': provider.value,
                'error': str(e)
            }
    
    async def close(self):
        """Закрывает соединения"""
        if self.llm_provider and hasattr(self.llm_provider, 'close'):
            await self.llm_provider.close()
    
    def __del__(self):
        """Деструктор для закрытия соединений"""
        if hasattr(self, 'llm_provider') and self.llm_provider and hasattr(self.llm_provider, 'close'):
            try:
                import asyncio
                asyncio.create_task(self.llm_provider.close())
            except:
                pass
