#!/usr/bin/env python3
"""
Конфигурация для различных LLM провайдеров
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

class LLMProvider(Enum):
    """Доступные LLM провайдеры"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    LOCAL = "local"
    NEUROLINK = "neurolink"

@dataclass
class LLMConfig:
    """Конфигурация для LLM провайдера"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30
    additional_params: Dict[str, Any] = None

class LLMConfigManager:
    """Менеджер конфигурации LLM"""
    
    def __init__(self):
        self.configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """Загружает конфигурации из переменных окружения и файла конфигурации"""
        from config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        llm_config = config_manager.get_service_config('llm')
        
        # Загружаем конфигурации провайдеров из файла
        providers_config = llm_config.get('providers', {})
        
        # OpenAI конфигурация
        openai_config = providers_config.get('openai', {})
        if openai_config.get('enabled', False) and (openai_config.get('api_key') or os.getenv('OPENAI_API_KEY')):
            self.configs[LLMProvider.OPENAI] = LLMConfig(
                provider=LLMProvider.OPENAI,
                model=openai_config.get('model', os.getenv('OPENAI_MODEL', 'gpt-4o-mini')),
                api_key=openai_config.get('api_key') or os.getenv('OPENAI_API_KEY'),
                base_url=openai_config.get('base_url') or os.getenv('OPENAI_BASE_URL'),
                temperature=float(openai_config.get('temperature', os.getenv('OPENAI_TEMPERATURE', '0.7'))),
                max_tokens=int(openai_config.get('max_tokens', os.getenv('OPENAI_MAX_TOKENS', '4000'))),
                timeout=int(openai_config.get('timeout', os.getenv('OPENAI_TIMEOUT', '30')))
            )
        
        # Anthropic конфигурация
        anthropic_config = providers_config.get('anthropic', {})
        if anthropic_config.get('enabled', False) and (anthropic_config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')):
            self.configs[LLMProvider.ANTHROPIC] = LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model=anthropic_config.get('model', os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')),
                api_key=anthropic_config.get('api_key') or os.getenv('ANTHROPIC_API_KEY'),
                base_url=anthropic_config.get('base_url') or os.getenv('ANTHROPIC_BASE_URL'),
                temperature=float(anthropic_config.get('temperature', os.getenv('ANTHROPIC_TEMPERATURE', '0.7'))),
                max_tokens=int(anthropic_config.get('max_tokens', os.getenv('ANTHROPIC_MAX_TOKENS', '4000'))),
                timeout=int(anthropic_config.get('timeout', os.getenv('ANTHROPIC_TIMEOUT', '30')))
            )
        
        # Google конфигурация
        google_config = providers_config.get('google', {})
        if google_config.get('enabled', False) and (google_config.get('api_key') or os.getenv('GOOGLE_API_KEY')):
            self.configs[LLMProvider.GOOGLE] = LLMConfig(
                provider=LLMProvider.GOOGLE,
                model=google_config.get('model', os.getenv('GOOGLE_MODEL', 'gemini-1.5-flash')),
                api_key=google_config.get('api_key') or os.getenv('GOOGLE_API_KEY'),
                base_url=google_config.get('base_url') or os.getenv('GOOGLE_BASE_URL'),
                temperature=float(google_config.get('temperature', os.getenv('GOOGLE_TEMPERATURE', '0.7'))),
                max_tokens=int(google_config.get('max_tokens', os.getenv('GOOGLE_MAX_TOKENS', '4000'))),
                timeout=int(google_config.get('timeout', os.getenv('GOOGLE_TIMEOUT', '30')))
            )
        
        # Ollama конфигурация - всегда включаем по умолчанию
        ollama_config = providers_config.get('ollama', {})
        # Ollama включен по умолчанию, если не отключен явно
        if ollama_config.get('enabled', True):
            self.configs[LLMProvider.OLLAMA] = LLMConfig(
                provider=LLMProvider.OLLAMA,
                model=ollama_config.get('model', os.getenv('OLLAMA_MODEL', 'llama3.1:8b')),
                base_url=ollama_config.get('base_url', os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')),
                temperature=float(ollama_config.get('temperature', os.getenv('OLLAMA_TEMPERATURE', '0.7'))),
                max_tokens=int(ollama_config.get('max_tokens', os.getenv('OLLAMA_MAX_TOKENS', '4000'))),
                timeout=int(ollama_config.get('timeout', os.getenv('OLLAMA_TIMEOUT', '30')))
            )
            print(f"[OK] Ollama провайдер загружен: {ollama_config.get('model', 'llama3.1:8b')}")
        else:
            print("[WARN] Ollama провайдер отключен в конфигурации")
        
        # Локальная конфигурация
        local_config = providers_config.get('local', {})
        if local_config.get('enabled', False):
            self.configs[LLMProvider.LOCAL] = LLMConfig(
                provider=LLMProvider.LOCAL,
                model=local_config.get('model', os.getenv('LOCAL_MODEL', 'local')),
                base_url=local_config.get('base_url', os.getenv('LOCAL_BASE_URL', 'http://localhost:8000')),
                temperature=float(local_config.get('temperature', os.getenv('LOCAL_TEMPERATURE', '0.7'))),
                max_tokens=int(local_config.get('max_tokens', os.getenv('LOCAL_MAX_TOKENS', '4000'))),
                timeout=int(local_config.get('timeout', os.getenv('LOCAL_TIMEOUT', '30')))
            )
        
        # Neurolink конфигурация - всегда включаем по умолчанию
        neurolink_config = providers_config.get('neurolink', {})
        # Neurolink включен по умолчанию, если не отключен явно
        if neurolink_config.get('enabled', True):
            self.configs[LLMProvider.NEUROLINK] = LLMConfig(
                provider=LLMProvider.NEUROLINK,
                model=neurolink_config.get('model', 'google/gemma-3-27b-it'),
                api_key=neurolink_config.get('api_key', 'ARjgZphys9tBWYnnJl5UdnOeAubUCwzaAhEpRnFi1yE'),
                base_url=neurolink_config.get('base_url', 'http://neurolink.iek.local:8004/v1/chat/completions'),
                temperature=float(neurolink_config.get('temperature', '0.15')),
                max_tokens=int(neurolink_config.get('max_tokens', '2048')),
                timeout=int(neurolink_config.get('timeout', '30'))
            )
            print(f"[OK] Neurolink провайдер загружен: {neurolink_config.get('model', 'google/gemma-3-27b-it')}")
        else:
            print("[WARN] Neurolink провайдер отключен в конфигурации")
    
    def get_config(self, provider: LLMProvider) -> Optional[LLMConfig]:
        """Получает конфигурацию для провайдера"""
        return self.configs.get(provider)
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Возвращает список доступных провайдеров"""
        return list(self.configs.keys())
    
    def get_default_provider(self) -> LLMProvider:
        """Возвращает провайдера по умолчанию"""
        from config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        llm_config = config_manager.get_service_config('llm')
        
        # Получаем провайдера по умолчанию из конфигурации
        default_provider_name = llm_config.get('provider', 'ollama')
        
        try:
            # Пытаемся получить провайдера из конфигурации
            default_provider = LLMProvider(default_provider_name)
            
            # Проверяем, что провайдер доступен и включен
            if default_provider in self.configs:
                return default_provider
            else:
                # Если провайдер не доступен, используем приоритетный порядок
                priority_order = [
                    LLMProvider.NEUROLINK,
                    LLMProvider.OPENAI,
                    LLMProvider.ANTHROPIC,
                    LLMProvider.GOOGLE,
                    LLMProvider.OLLAMA,
                    LLMProvider.LOCAL
                ]
                
                for provider in priority_order:
                    if provider in self.configs:
                        return provider
                
                return LLMProvider.OLLAMA  # Fallback
                
        except ValueError:
            # Если провайдер не найден, используем приоритетный порядок
            priority_order = [
                LLMProvider.NEUROLINK,
                LLMProvider.OPENAI,
                LLMProvider.ANTHROPIC,
                LLMProvider.GOOGLE,
                LLMProvider.OLLAMA,
                LLMProvider.LOCAL
            ]
            
            for provider in priority_order:
                if provider in self.configs:
                    return provider
            
            return LLMProvider.OLLAMA  # Fallback
    
    def update_config(self, provider: LLMProvider, **kwargs):
        """Обновляет конфигурацию провайдера"""
        if provider in self.configs:
            config = self.configs[provider]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def add_custom_config(self, provider: LLMProvider, config: LLMConfig):
        """Добавляет пользовательскую конфигурацию"""
        self.configs[provider] = config

# Глобальный экземпляр менеджера конфигурации
llm_config_manager = LLMConfigManager()
