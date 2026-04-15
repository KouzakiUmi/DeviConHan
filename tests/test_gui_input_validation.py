import unittest

from utils.validators import ValidationError, sanitize_text_input, sanitize_user_path


class TestGuiInputValidation(unittest.TestCase):
    def test_rejects_control_characters_in_text_input(self):
        with self.assertRaises(ValidationError):
            sanitize_text_input("bad\ninput", allow_empty=False)

    def test_rejects_overlong_text_input(self):
        with self.assertRaises(ValidationError):
            sanitize_text_input("a" * 20, max_length=10, allow_empty=False)

    def test_normalizes_user_path(self):
        path = sanitize_user_path(".\\tests\\..\\tests", allow_empty=False)
        self.assertTrue(path.lower().endswith("tests"))


if __name__ == "__main__":
    unittest.main()
