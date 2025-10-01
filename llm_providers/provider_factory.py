#!/usr/bin/env python3
"""
Фабрика для создания LLM провайдеров
"""

from typing import Optional, List
from config.llm_config import LLMConfig, LLMProvider, llm_config_manager
from llm_providers.base_provider import BaseLLMProvider
from llm_providers.openai_provider import OpenAIProvider
from llm_providers.anthropic_provider import AnthropicProvider
from llm_providers.google_provider import GoogleProvider
from llm_providers.ollama_provider import OllamaProvider
from llm_providers.neurolink_provider import NeurolinkProvider

class LLMProviderFactory:
    """Фабрика для создания LLM провайдеров"""
    
    _providers = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider,
        LLMProvider.GOOGLE: GoogleProvider,
        LLMProvider.OLLAMA: OllamaProvider,
        LLMProvider.NEUROLINK: NeurolinkProvider,
    }
    
    @classmethod
    def create_provider(cls, provider: LLMProvider, config: Optional[LLMConfig] = None) -> BaseLLMProvider:
        """Создает провайдер для указанного типа"""
        if provider not in cls._providers:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")
        
        if config is None:
            config = llm_config_manager.get_config(provider)
            if config is None:
                raise ValueError(f"Конфигурация для провайдера {provider} не найдена")
        
        provider_class = cls._providers[provider]
        return provider_class(config)
    
    @classmethod
    def create_default_provider(cls) -> BaseLLMProvider:
        """Создает провайдер по умолчанию"""
        default_provider = llm_config_manager.get_default_provider()
        return cls.create_provider(default_provider)
    
    @classmethod
    def get_available_providers(cls) -> List[LLMProvider]:
        """Возвращает список доступных провайдеров"""
        return llm_config_manager.get_available_providers()
    
    @classmethod
    def register_provider(cls, provider_type: LLMProvider, provider_class: type):
        """Регистрирует новый провайдер"""
        cls._providers[provider_type] = provider_class
