# -*- coding: utf-8 -*-
"""
统一错误处理模块

提供标准化的错误处理、用户友好的错误消息和日志记录功能。
"""

import logging
import traceback
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    CORRUPTED_DATA = "corrupted_data"
    NETWORK_ERROR = "network_error"
    CONFIG_ERROR = "config_error"
    UNKNOWN_ERROR = "unknown_error"


class PatcherError(Exception):
    """基础补丁工具异常类"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR, 
                 severity: ErrorSeverity = ErrorSeverity.ERROR, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'details': self.details
        }


class PatcherFileNotFoundError(PatcherError):
    """文件未找到异常"""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        details = {'file_path': file_path} if file_path else {}
        super().__init__(message, ErrorCategory.FILE_NOT_FOUND, ErrorSeverity.ERROR, details)
        self.file_path = file_path


class PatcherPermissionError(PatcherError):
    """权限异常"""
    
    def __init__(self, message: str, path: Optional[str] = None, operation: Optional[str] = None):
        details = {'path': path, 'operation': operation} if path or operation else {}
        super().__init__(message, ErrorCategory.PERMISSION_DENIED, ErrorSeverity.ERROR, details)
        self.path = path
        self.operation = operation


class AsarCorruptedError(PatcherError):
    """ASAR文件损坏异常"""

    def __init__(self, message: str, asar_path: Optional[str] = None):
        details = {'asar_path': asar_path} if asar_path else {}
        super().__init__(message, ErrorCategory.CORRUPTED_DATA, ErrorSeverity.ERROR, details)
        self.asar_path = asar_path


class NodeNotFoundError(PatcherError):
    """Node.js未找到异常"""

    def __init__(self, message: str, node_path: Optional[str] = None):
        details = {'node_path': node_path} if node_path else {}
        super().__init__(message, ErrorCategory.UNKNOWN_ERROR, ErrorSeverity.ERROR, details)
        self.node_path = node_path


class ConfigError(PatcherError):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {'config_key': config_key} if config_key else {}
        super().__init__(message, ErrorCategory.CONFIG_ERROR, ErrorSeverity.ERROR, details)
        self.config_key = config_key


class ErrorHandler:
    """统一错误处理器"""
    
    # 错误消息模板
    MESSAGE_TEMPLATES = {
        ErrorCategory.FILE_NOT_FOUND: {
            'cn': "文件未找到: {file_path}",
            'en': "File not found: {file_path}",
            'jp': "ファイルが見つかりません: {file_path}"
        },
        ErrorCategory.PERMISSION_DENIED: {
            'cn': "权限不足，无法{operation}: {path}",
            'en': "Permission denied for {operation}: {path}",
            'jp': "権限が不足しているため、{operation} できません: {path}"
        },
        ErrorCategory.CORRUPTED_DATA: {
            'cn': "数据损坏: {detail}",
            'en': "Data corrupted: {detail}",
            'jp': "データが破損しています: {detail}"
        },
        ErrorCategory.CONFIG_ERROR: {
            'cn': "配置错误: {detail}",
            'en': "Configuration error: {detail}",
            'jp': "設定エラー: {detail}"
        },
        ErrorCategory.NETWORK_ERROR: {
            'cn': "网络错误: {detail}",
            'en': "Network error: {detail}",
            'jp': "ネットワークエラー: {detail}"
        }
    }
    
    def __init__(self, current_lang: str = 'cn'):
        self.current_lang = current_lang
    
    def set_language(self, lang: str):
        """设置当前语言"""
        if lang in ['cn', 'en', 'jp']:
            self.current_lang = lang
    
    def get_user_message(self, error: Exception) -> str:
        """
        获取用户友好的错误消息
        
        Args:
            error: 异常对象
            
        Returns:
            str: 用户友好的错误消息
        """
        if isinstance(error, PatcherError):
            return self._format_patcher_error(error)
        else:
            return str(error)
    
    def _format_patcher_error(self, error: PatcherError) -> str:
        """格式化PatcherError为用户消息"""
        template = self.MESSAGE_TEMPLATES.get(error.category, {}).get(self.current_lang, error.message)
        
        try:
            if error.details:
                return template.format(**error.details)
        except (KeyError, ValueError):
            pass
        
        return error.message
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """
        记录错误日志
        
        Args:
            error: 异常对象
            context: 错误上下文信息
        """
        error_msg = f"{context}: {error}" if context else str(error)
        
        if isinstance(error, PatcherError):
            if error.severity == ErrorSeverity.CRITICAL:
                logger.critical(error_msg)
            elif error.severity == ErrorSeverity.ERROR:
                logger.error(error_msg)
            elif error.severity == ErrorSeverity.WARNING:
                logger.warning(error_msg)
            else:
                logger.info(error_msg)
            
            # 记录详细信息
            if error.details:
                logger.debug(f"Error details: {error.details}")
        else:
            logger.exception(error_msg)
    
    def handle_error(self, error: Exception, context: str = "") -> str:
        """
        处理错误并返回用户友好的消息
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            str: 用户友好的错误消息
        """
        self.log_error(error, context)
        return self.get_user_message(error)
    
    @staticmethod
    def format_traceback(error: Exception) -> str:
        """格式化异常堆栈跟踪"""
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))


# 全局错误处理器实例
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return _error_handler


def set_error_language(lang: str) -> None:
    """设置错误处理器的语言"""
    _error_handler.set_language(lang)


def handle_patcher_error(error: Exception, context: str = "") -> str:
    """
    处理补丁工具错误的便捷函数
    
    Args:
        error: 异常对象
        context: 错误上下文
        
    Returns:
        str: 用户友好的错误消息
    """
    return _error_handler.handle_error(error, context)