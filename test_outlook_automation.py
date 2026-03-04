import unittest
from unittest.mock import patch

import outlook_automation as oa


class OutlookAutomationTests(unittest.TestCase):
    def test_normalize_for_alias(self):
        self.assertEqual(oa.normalize_for_alias("John-Doe 123"), "johndoe123")

    def test_slugify_country(self):
        self.assertEqual(oa.slugify_country("United States"), "united-states")

    def test_generate_password_length_and_complexity(self):
        pwd = oa.generate_password(8, 12)
        self.assertGreaterEqual(len(pwd), 8)
        self.assertLessEqual(len(pwd), 12)
        self.assertTrue(any(c.islower() for c in pwd))
        self.assertTrue(any(c.isupper() for c in pwd))
        self.assertTrue(any(c.isdigit() for c in pwd))
        self.assertTrue(any(c in "!@#$%^&*" for c in pwd))

    @patch("outlook_automation.fetch_fantasy_names", return_value=["altname"])
    @patch("outlook_automation.check_outlook_exists", side_effect=[True, False])
    def test_pick_unique_alias_uses_fallback_when_primary_taken(self, _exists, _fantasy):
        alias, attempts = oa.pick_unique_alias("John", "Doe", "japan")
        self.assertEqual(alias, "altname")
        self.assertEqual(len(attempts), 2)
        self.assertIn("johndoe@outlook.com => TAKEN", attempts[0])
        self.assertIn("altname@outlook.com => AVAILABLE", attempts[1])

    def test_pick_unique_alias_skip_check(self):
        alias, attempts = oa.pick_unique_alias("John", "Doe", "japan", skip_check=True)
        self.assertEqual(alias, "johndoe")
        self.assertEqual(len(attempts), 1)
        self.assertIn("SKIPPED (offline mode)", attempts[0])


if __name__ == "__main__":
    unittest.main()
