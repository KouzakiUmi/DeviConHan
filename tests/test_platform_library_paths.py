import unittest
from unittest.mock import mock_open, patch

from utils.platform import get_steam_library_paths


class TestPlatformLibraryPaths(unittest.TestCase):
    def test_windows_fallback_scans_all_drive_letters_for_steamlibrary(self):
        def normalize(path):
            return path.lower().replace("/", "\\").rstrip("\\")

        def isdir_side_effect(path):
            normalized = normalize(path)
            return normalized in {
                r"c:\steam",
                r"c:\steam\steamapps",
                r"f:",
                r"f:\steamlibrary\steamapps",
            }

        def isfile_side_effect(path):
            return False

        def listdir_side_effect(path):
            if path.startswith("F:"):
                return ["SteamLibrary"]
            return []

        with patch("utils.platform.get_platform_info") as info, \
             patch("utils.platform._get_steam_install_path", return_value=r"C:\Steam"), \
             patch("utils.platform.os.path.isdir", side_effect=isdir_side_effect), \
             patch("utils.platform.os.path.isfile", side_effect=isfile_side_effect), \
             patch("utils.platform.os.listdir", side_effect=listdir_side_effect), \
             patch("builtins.open", mock_open(read_data="")):
            info.return_value.system = "windows"
            info.return_value.arch = "x86_64"
            info.return_value.steam_common_path = r"C:\Steam\steamapps\common"
            paths = get_steam_library_paths()

        self.assertIn(r"C:\Steam\steamapps", paths)
        self.assertIn(r"F:\SteamLibrary\steamapps", paths)


if __name__ == "__main__":
    unittest.main()
