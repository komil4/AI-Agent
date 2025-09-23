# MCP Servers package

class BaseMCPServer:
    """Базовый класс для MCP серверов"""
    
    def get_description(self) -> str:
        """Возвращает описание сервера"""
        return getattr(self, 'description', 'MCP сервер')
    
    def get_tools(self) -> list:
        """Возвращает список инструментов сервера"""
        return getattr(self, 'tools', [])
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервер"""
        try:
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Получаем имя сервера из класса
            server_name = self.__class__.__name__.lower().replace('mcp', '').replace('server', '')
            
            # Проверяем конфигурацию
            service_config = config_manager.get_service_config(server_name)
            return service_config.get('enabled', False)
        except Exception:
            return False