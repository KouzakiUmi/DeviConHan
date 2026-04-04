# -*- coding: utf-8 -*-

import os
from configparser import ConfigParser

from utils.paths import get_resource_path

class AppConfig:
    def __init__(self, config_file=None):
        if config_file is None:
            self.config_file = get_resource_path("config.ini")
        else:
            self.config_file = config_file
        
        self.config = ConfigParser()
        self.config.read(self.config_file, encoding="utf-8")

    def get(self, section, key, **kwargs):
        return self.config.get(section, key, **kwargs)

    def get_list(self, section, key):
        value = self.get(section, key, fallback=None)
        if value is not None:
            return [line.strip() for line in str(value).split("\n") if line.strip()]
        return []

# Global config instance
config = AppConfig()
