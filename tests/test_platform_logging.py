import unittest
from unittest.mock import patch

from utils import platform as platform_utils


class TestPlatformLogging(unittest.TestCase):
    def setUp(self):
        platform_utils._find_steam_path_windows.cache_clear()

    def tearDown(self):
        platform_utils._find_steam_path_windows.cache_clear()

    def test_windows_registry_lookup_logs_once_when_cached(self):
        mock_key = object()

        with patch("utils.platform.sys.platform", "win32"), \
             patch("utils.platform.os.path.isdir", return_value=True), \
             patch("utils.platform.logger.info") as log_info, \
             patch("winreg.OpenKey", return_value=mock_key), \
             patch("winreg.QueryValueEx", return_value=(r"E:\Steam", None)), \
             patch("winreg.CloseKey") as close_key:
            first = platform_utils._find_steam_path_windows()
            second = platform_utils._find_steam_path_windows()

        self.assertEqual(first, r"E:\Steam\steamapps\common")
        self.assertEqual(second, first)
        log_info.assert_called_once_with(r"Found Steam from registry: E:\Steam")
        close_key.assert_called_once_with(mock_key)


if __name__ == "__main__":
    unittest.main()
