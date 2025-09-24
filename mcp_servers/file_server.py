import os
from typing import Dict, Any, List
from config.config_manager import ConfigManager
from .base_fastmcp_server import BaseFastMCPServer

class FileMCPServer(BaseFastMCPServer):
    """MCP сервер для работы с файлами - чтение, запись и управление файлами"""
    
    def __init__(self):
        super().__init__("file")
        self.description = "Файловая система - чтение, запись и управление файлами"
        
        # Настройки для админ-панели
        self.display_name = "File MCP"
        self.icon = "fas fa-folder"
        self.category = "mcp_servers"
        self.admin_fields = [
            { 'key': 'base_path', 'label': 'Базовый путь', 'type': 'text', 'placeholder': '/path/to/files' },
            { 'key': 'allowed_extensions', 'label': 'Разрешенные расширения', 'type': 'text', 'placeholder': 'txt,md,py,js,html,css' },
            { 'key': 'max_file_size', 'label': 'Максимальный размер файла (MB)', 'type': 'number', 'placeholder': '10' },
            { 'key': 'enabled', 'label': 'Включен', 'type': 'checkbox' }
        ]
        self.tools = [
            {
                "name": "read_file",
                "description": "Читает содержимое файла",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Путь к файлу"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Записывает содержимое в файл",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Путь к файлу"},
                        "content": {"type": "string", "description": "Содержимое файла"}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": "Получает список файлов в директории",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Путь к директории"},
                        "recursive": {"type": "boolean", "description": "Рекурсивный поиск"}
                    },
                    "required": ["directory_path"]
                }
            },
            {
                "name": "create_directory",
                "description": "Создает директорию",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Путь к директории"}
                    },
                    "required": ["directory_path"]
                }
            },
            {
                "name": "delete_file",
                "description": "Удаляет файл или директорию",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к файлу или директории"}
                    },
                    "required": ["path"]
                }
            }
        ]
        
        self.config_manager = ConfigManager()
        self.base_path = self.config_manager.get_service_config('file').get('base_path', '/tmp')
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает инструмент сервера"""
        try:
            if tool_name == "read_file":
                return self._read_file(arguments)
            elif tool_name == "write_file":
                return self._write_file(arguments)
            elif tool_name == "list_directory":
                return self._list_directory(arguments)
            elif tool_name == "create_directory":
                return self._create_directory(arguments)
            elif tool_name == "delete_file":
                return self._delete_file(arguments)
            else:
                return {"error": f"Неизвестный инструмент: {tool_name}"}
        except Exception as e:
            return {"error": f"Ошибка выполнения {tool_name}: {str(e)}"}
    
    def _read_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Читает файл"""
        file_path = arguments.get('file_path')
        full_path = os.path.join(self.base_path, file_path)
        
        if not os.path.exists(full_path):
            return {"error": f"Файл не найден: {file_path}"}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content, "file_path": file_path}
        except Exception as e:
            return {"error": f"Ошибка чтения файла: {str(e)}"}
    
    def _write_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Записывает файл"""
        file_path = arguments.get('file_path')
        content = arguments.get('content')
        full_path = os.path.join(self.base_path, file_path)
        
        try:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "file_path": file_path}
        except Exception as e:
            return {"error": f"Ошибка записи файла: {str(e)}"}
    
    def _list_directory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Список файлов в директории"""
        directory_path = arguments.get('directory_path')
        recursive = arguments.get('recursive', False)
        full_path = os.path.join(self.base_path, directory_path)
        
        if not os.path.exists(full_path):
            return {"error": f"Директория не найдена: {directory_path}"}
        
        try:
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(full_path):
                    for filename in filenames:
                        rel_path = os.path.relpath(os.path.join(root, filename), self.base_path)
                        files.append(rel_path)
            else:
                files = os.listdir(full_path)
            return {"files": files, "directory_path": directory_path}
        except Exception as e:
            return {"error": f"Ошибка чтения директории: {str(e)}"}
    
    def _create_directory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Создает директорию"""
        directory_path = arguments.get('directory_path')
        full_path = os.path.join(self.base_path, directory_path)
        
        try:
            os.makedirs(full_path, exist_ok=True)
            return {"success": True, "directory_path": directory_path}
        except Exception as e:
            return {"error": f"Ошибка создания директории: {str(e)}"}
    
    def _delete_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Удаляет файл или директорию"""
        path = arguments.get('path')
        full_path = os.path.join(self.base_path, path)
        
        if not os.path.exists(full_path):
            return {"error": f"Путь не найден: {path}"}
        
        try:
            if os.path.isdir(full_path):
                os.rmdir(full_path)
            else:
                os.remove(full_path)
            return {"success": True, "path": path}
        except Exception as e:
            return {"error": f"Ошибка удаления: {str(e)}"}
    
    def check_health(self) -> Dict[str, Any]:
        """Проверяет доступность сервера"""
        try:
            if os.path.exists(self.base_path):
                return {
                    'status': 'healthy',
                    'provider': 'file',
                    'base_path': self.base_path
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'file',
                    'error': f'Базовая директория не существует: {self.base_path}'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'file',
                'error': str(e)
            }
