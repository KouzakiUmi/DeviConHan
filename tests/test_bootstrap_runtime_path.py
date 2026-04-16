import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.bootstrap as bootstrap
from controllers.save_manager_controller import SaveManagerController
from core.state_validator import SystemState


class TestBootstrapRuntimePath(unittest.TestCase):
    def tearDown(self):
        bootstrap._detected_game_path = None

    def test_get_runtime_game_path_redetects_when_cached_path_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "Game"
            resources = game_dir / "resources"
            resources.mkdir(parents=True)
            (resources / "app.asar").write_bytes(b"x" * 2048)

            bootstrap._detected_game_path = str(root / "not-a-game")

            with patch("core.bootstrap.find_game_directory", return_value=str(game_dir)):
                resolved = bootstrap.get_runtime_game_path()

            self.assertEqual(resolved, str(game_dir))

    def test_bootstrap_prefers_steam_detected_game_over_current_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cwd_game = root / "CurrentGame"
            steam_game = root / "SteamGame"
            for game_dir in (cwd_game, steam_game):
                resources = game_dir / "resources"
                resources.mkdir(parents=True)
                (resources / "app.asar").write_bytes(b"x" * 2048)

            config = type(
                "Config",
                (),
                {
                    "auto_detect_game": True,
                    "validate_config": staticmethod(lambda: (True, [], [])),
                    "target_asar_name": "app.asar",
                },
            )()

            with patch("core.bootstrap.get_config", return_value=config), \
                 patch("core.bootstrap.os.path.abspath", return_value=str(cwd_game)), \
                 patch("core.bootstrap.find_game_directory", return_value=str(steam_game)), \
                 patch(
                     "core.bootstrap.validate_system_state",
                     return_value=(SystemState.PATCHED, []),
                 ), \
                 patch("core.bootstrap.get_disk_free_space", return_value=400 * 1024**3), \
                 patch("core.bootstrap.get_operation_lock"), \
                 patch("core.bootstrap.logger"):
                ok, messages = bootstrap.bootstrap_system()

            self.assertTrue(ok)
            self.assertIn(f"Auto-detected game directory: {steam_game}", messages)
            self.assertEqual(bootstrap.get_detected_game_path(), str(steam_game))

    def test_scan_save_directory_does_not_fallback_to_cwd_when_runtime_path_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_game = root / "RuntimeGame"
            runtime_game.mkdir()
            (root / "_storage").mkdir()

            controller = SaveManagerController(save_service=None)

            with patch("core.bootstrap.get_runtime_game_path", return_value=str(runtime_game)):
                found = controller.scan_save_directory()

            self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
