import unittest
from unittest.mock import patch

from utils.platform import find_game_in_steam


class TestPlatformDetection(unittest.TestCase):
    def test_find_game_in_steam_reuses_supplied_search_paths_for_appid_lookup(self):
        search_paths = [r"D:\SteamLibrary\steamapps"]

        with patch("utils.platform.find_game_by_appid", return_value=r"D:\Games\Target") as by_appid, \
             patch("utils.platform.scan_steam_apps") as scan_apps, \
             patch("utils.platform.get_steam_library_paths") as get_paths:
            result = find_game_in_steam("123456", search_paths=search_paths)

        self.assertEqual(result, r"D:\Games\Target")
        by_appid.assert_called_once_with("123456", search_paths)
        scan_apps.assert_not_called()
        get_paths.assert_not_called()

    def test_find_game_in_steam_reuses_supplied_search_paths_for_name_scan(self):
        search_paths = [r"D:\SteamLibrary\steamapps"]

        with patch("utils.platform.find_game_by_appid", return_value=None) as by_appid, \
             patch("utils.platform.scan_steam_apps", return_value=[]) as scan_apps, \
             patch("utils.platform._find_game_by_directory_scan", return_value=None) as fallback_scan, \
             patch("utils.platform.get_steam_library_paths") as get_paths:
            result = find_game_in_steam("Devil Connection", search_paths=search_paths)

        self.assertIsNone(result)
        by_appid.assert_not_called()
        scan_apps.assert_called_once_with(search_paths)
        fallback_scan.assert_called_once()
        get_paths.assert_not_called()


if __name__ == "__main__":
    unittest.main()
