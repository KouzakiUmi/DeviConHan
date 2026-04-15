import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.bootstrap as bootstrap


class TestBootstrapRuntimePath(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
