import unittest


class PackageTest(unittest.TestCase):
    def test_package_imports(self):
        import omaworks

        self.assertTrue(hasattr(omaworks, "__path__"))


if __name__ == "__main__":
    unittest.main()
