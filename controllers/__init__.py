"""
控制器模块

包含业务逻辑控制器，解耦GUI代码。
"""

from controllers.patch_controller import PatchController
from controllers.save_manager_controller import SaveManagerController

__all__ = ["SaveManagerController", "PatchController"]
