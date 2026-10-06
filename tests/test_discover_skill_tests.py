import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "ci" / "discover_skill_tests.py"
)
SPEC = importlib.util.spec_from_file_location("discover_skill_tests", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DiscoverSkillTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.skills_dir = Path(self.temporary_directory.name) / "skills"
        self.skills_dir.mkdir()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def create_skill(self, name, python=False, tests=False, requirements=False):
        skill_dir = self.skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

        if python:
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "run.py").write_text("VALUE = 1\n", encoding="utf-8")

        if tests:
            tests_dir = skill_dir / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_run.py").write_text(
                "import unittest\n", encoding="utf-8"
            )

        if requirements:
            tests_dir = skill_dir / "tests"
            tests_dir.mkdir(exist_ok=True)
            (tests_dir / "requirements.txt").write_text("pyyaml\n", encoding="utf-8")

        return skill_dir

    def test_ignores_markdown_only_skill(self):
        self.create_skill("markdown-only")

        self.assertEqual(MODULE.discover_suites(self.skills_dir), [])

    def test_discovers_unit_tests(self):
        self.create_skill("with-tests", python=True, tests=True)

        suites = MODULE.discover_suites(self.skills_dir)

        self.assertEqual(suites[0]["name"], "with-tests")
        self.assertEqual(suites[0]["mode"], "unit")
        self.assertIn("unittest discover", suites[0]["command"])

    def test_uses_syntax_smoke_test_when_suite_is_missing(self):
        self.create_skill("without-tests", python=True)

        suites = MODULE.discover_suites(self.skills_dir)

        self.assertEqual(suites[0]["name"], "without-tests")
        self.assertEqual(suites[0]["mode"], "syntax")
        self.assertIn("compileall", suites[0]["command"])

    def test_reports_requirements_file_declared_by_the_skill(self):
        self.create_skill("needs-deps", python=True, tests=True, requirements=True)
        self.create_skill("plain", python=True, tests=True)

        suites = {suite["name"]: suite for suite in MODULE.discover_suites(self.skills_dir)}

        self.assertEqual(
            suites["needs-deps"]["requirements_file"],
            (self.skills_dir / "needs-deps" / "tests" / "requirements.txt").as_posix(),
        )
        self.assertEqual(suites["plain"]["requirements_file"], "")

    def test_requirements_file_is_reported_in_syntax_mode_too(self):
        self.create_skill("no-suite", python=True, requirements=True)

        (suite,) = MODULE.discover_suites(self.skills_dir)

        self.assertEqual(suite["mode"], "syntax")
        self.assertTrue(suite["requirements_file"].endswith("tests/requirements.txt"))

    def test_returns_suites_in_name_order(self):
        self.create_skill("zeta", python=True)
        self.create_skill("alpha", python=True)

        suites = MODULE.discover_suites(self.skills_dir)

        self.assertEqual([suite["name"] for suite in suites], ["alpha", "zeta"])


if __name__ == "__main__":
    unittest.main()
