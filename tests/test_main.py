import os
import sys
import unittest
from glob import glob
from tempfile import NamedTemporaryFile, gettempdir

from pylint.lint import Run

from pylint_odoo import misc

EXPECTED_ERRORS = {
    "attribute-deprecated": 3,
    "attribute-string-redundant": 31,
    "class-camelcase": 1,
    "consider-merging-classes-inherited": 2,
    "context-overridden": 3,
    "development-status-allowed": 1,
    "eval-referenced": 5,
    "except-pass": 3,
    "external-request-timeout": 51,
    "invalid-commit": 4,
    "license-allowed": 1,
    "manifest-author-string": 1,
    "manifest-data-duplicated": 1,
    "manifest-deprecated-key": 1,
    "manifest-maintainers-list": 1,
    "manifest-required-author": 1,
    "manifest-required-key": 1,
    "manifest-version-format": 3,
    "method-compute": 1,
    "method-inverse": 1,
    "method-required-super": 8,
    "method-search": 1,
    "missing-return": 1,
    "odoo-addons-relative-import": 4,
    "openerp-exception-warning": 3,
    "print-used": 1,
    "renamed-field-parameter": 2,
    "resource-not-exist": 4,
    "sql-injection": 21,
    "test-folder-imported": 3,
    "translation-contains-variable": 10,
    "translation-field": 2,
    "translation-positional-used": 7,
    "translation-required": 15,
    "use-vim-comment": 1,
    "website-manifest-key-not-valid-uri": 1,
}


class MainTest(unittest.TestCase):
    def setUp(self):
        dummy_cfg = os.path.join(gettempdir(), "nousedft.cfg")
        with open(dummy_cfg, "w", encoding="UTF-8") as f_dummy:
            f_dummy.write("")
        self.default_options = [
            "--load-plugins=pylint_odoo",
            "--reports=no",
            "--msg-template=" '"{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"',
            "--output-format=colorized",
            "--rcfile=%s" % os.devnull,
        ]
        path_modules = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "testing", "resources", "test_repo"
        )
        # Similar to pre-commit way
        self.paths_modules = glob(os.path.join(path_modules, "**", "*.py"), recursive=True)
        self.odoo_namespace_addons_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "testing",
            "resources",
            "test_repo_odoo_namespace",
            "odoo",
        )
        self.default_extra_params = [
            "--disable=all",
            "--enable=odoolint,pointless-statement,trailing-newlines",
        ]
        self.sys_path_origin = list(sys.path)
        self.maxDiff = None
        self.expected_errors = EXPECTED_ERRORS.copy()

    def tearDown(self):
        sys.path = list(self.sys_path_origin)

    def run_pylint(self, paths, extra_params=None):
        for path in paths:
            if not os.path.exists(path):
                raise OSError('Path "{path}" not found.'.format(path=path))
        if extra_params is None:
            extra_params = self.default_extra_params
        sys.path.extend(paths)
        cmd = self.default_options + extra_params + paths
        res = Run(cmd, exit=False)
        return res

    def test_10_path_dont_exist(self):
        """test if path don't exist"""
        path_unexist = "/tmp/____unexist______"
        with self.assertRaisesRegex(OSError, r'Path "{path}" not found.$'.format(path=path_unexist)):
            self.run_pylint([path_unexist])

    def test_20_expected_errors(self):
        """Expected vs found errors"""
        pylint_res = self.run_pylint(self.paths_modules)
        real_errors = pylint_res.linter.stats.by_msg
        self.assertEqual(self.expected_errors, real_errors)

    def test_25_checks_without_coverage(self):
        """All odoolint errors vs found"""
        # Some messages can be excluded as they are only applied on certain
        # Odoo versions (not necessarily 8.0).
        excluded_msgs = {
            "unnecessary-utf8-coding-comment",
            "xml-deprecated-qweb-directive",
        }
        extra_params = ["--valid_odoo_versions=8.0"]
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        msgs_found = pylint_res.linter.stats.by_msg.keys()
        plugin_msgs = set(misc.get_plugin_msgs(pylint_res)) - excluded_msgs
        test_missed_msgs = sorted(list(plugin_msgs - set(msgs_found)))
        self.assertFalse(
            test_missed_msgs, "Checks without test case: {test_missed_msgs}".format(test_missed_msgs=test_missed_msgs)
        )

    def test_85_valid_odoo_version_format(self):
        """Test --manifest_version_format parameter"""
        # First, run Pylint for version 8.0
        extra_params = [
            r'--manifest_version_format="8\.0\.\d+\.\d+.\d+$"' '--valid_odoo_versions=""',
            "--disable=all",
            "--enable=manifest-version-format",
        ]
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "manifest-version-format": 6,
        }
        self.assertDictEqual(real_errors, expected_errors)

        # Now for version 11.0
        extra_params[0] = r'--manifest_version_format="11\.0\.\d+\.\d+.\d+$"'
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "manifest-version-format": 5,
        }
        self.assertDictEqual(real_errors, expected_errors)

    def test_90_valid_odoo_versions(self):
        """Test --valid_odoo_versions parameter when it's '8.0' & '11.0'"""
        # First, run Pylint for version 8.0
        extra_params = [
            "--valid_odoo_versions=8.0",
            "--disable=all",
            "--enable=manifest-version-format",
        ]
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "manifest-version-format": 6,
        }
        self.assertDictEqual(real_errors, expected_errors)

        # Now for version 11.0
        extra_params[0] = "--valid_odoo_versions=11.0"
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "manifest-version-format": 5,
        }
        self.assertDictEqual(real_errors, expected_errors)

    def test_110_manifest_required_authors(self):
        """Test --manifest_required_authors using a different author and
        multiple authors separated by commas
        """
        # First, run Pylint using a different author
        extra_params = [
            "--manifest_required_authors=Vauxoo",
            "--disable=all",
            "--enable=manifest-required-author",
        ]
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "manifest-required-author": 4,
        }
        self.assertDictEqual(real_errors, expected_errors)

        # Then, run it using multiple authors
        extra_params[0] = "--manifest_required_authors=Vauxoo,Other"
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors["manifest-required-author"] = 3
        self.assertDictEqual(real_errors, expected_errors)

        # Testing deprecated attribute
        extra_params[0] = "--manifest_required_author=" "Odoo Community Association (OCA)"
        pylint_res = self.run_pylint(self.paths_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors_deprecated = {
            "manifest-required-author": (EXPECTED_ERRORS["manifest-required-author"]),
        }
        self.assertDictEqual(real_errors, expected_errors_deprecated)

    def test_140_check_suppress_migrations(self):
        """Test migrations path supress checks"""
        extra_params = [
            "--disable=all",
            "--enable=invalid-name,unused-argument",
        ]
        path_modules = [
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                "testing",
                "resources",
                "test_repo",
                "test_module",
                "migrations",
                "10.0.1.0.0",
                "pre-migration.py",
            )
        ]

        # Messages suppressed with plugin for migration
        pylint_res = self.run_pylint(path_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "invalid-name": 1,
            "unused-argument": 1,
        }
        self.assertDictEqual(real_errors, expected_errors)

        # Messages raised without plugin
        self.default_options.remove("--load-plugins=pylint_odoo")
        pylint_res = self.run_pylint(path_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {
            "invalid-name": 3,
            "unused-argument": 2,
        }
        self.assertDictEqual(real_errors, expected_errors)

    def test_140_check_migrations_is_not_odoo_module(self):
        """Checking that migrations folder is not considered a odoo module
        Related to https://github.com/OCA/pylint-odoo/issues/357"""
        extra_params = [
            "--disable=all",
            "--enable=missing-readme",
        ]
        test_module = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "testing",
            "resources",
            "test_repo",
            "test_module",
        )
        path_modules = [
            os.path.join(test_module, "__init__.py"),
            os.path.join(test_module, "migrations", "10.0.1.0.0", "pre-migration.py"),
        ]
        pylint_res = self.run_pylint(path_modules, extra_params)
        real_errors = pylint_res.linter.stats.by_msg
        expected_errors = {}
        self.assertDictEqual(real_errors, expected_errors)

    @unittest.skipUnless(not sys.platform.startswith("win"), "TOOD: Fix with windows")  # TODO: Fix it
    def test_145_check_fstring_sqli(self):
        """Verify the linter is capable of finding SQL Injection vulnerabilities
        when using fstrings.
        Related to https://github.com/OCA/pylint-odoo/issues/363"""
        extra_params = ["--disable=all", "--enable=sql-injection"]
        queries = """
def fstring_sqli(self):
   self.env.cr.execute(f"SELECT * FROM TABLE WHERE SQLI = {self.table}")
   self.env.cr.execute(
       f"SELECT * FROM TABLE WHERE SQLI = {'hello' + self.name}"
   )
   self.env.cr.execute(f"SELECT * FROM {self.name} WHERE SQLI = {'hello'}")
   death_wish = f"SELECT * FROM TABLE WHERE SQLI = {self.name}"
   self.env.cr.execute(death_wish)
def fstring_no_sqli(self):
   self.env.cr.execute(f"SELECT * FROM TABLE WHERE SQLI = {'hello'}")
   self.env.cr.execute(
       f"CREATE VIEW {self._table} AS (SELECT * FROM res_partner)"
   )
   self.env.cr.execute(f"SELECT NAME FROM res_partner LIMIT 10")
           """
        with NamedTemporaryFile(mode="w") as tmp_f:
            tmp_f.write(queries)
            tmp_f.flush()
            pylint_res = self.run_pylint([tmp_f.name], extra_params)

        real_errors = pylint_res.linter.stats.by_msg
        self.assertDictEqual(real_errors, {"sql-injection": 4})

    def test_150_check_only_enabled_one_check(self):
        """Checking -d all -e ONLY-ONE-CHECK"""
        disable = "--disable=all"
        for expected_error_name, expected_error_value in EXPECTED_ERRORS.items():
            enable = "--enable=%s" % expected_error_name
            pylint_res = self.run_pylint(self.paths_modules, [disable, enable])
            real_errors = pylint_res.linter.stats.by_msg
            expected_errors = {expected_error_name: expected_error_value}
            self.assertDictEqual(real_errors, expected_errors)

    def test_160_check_only_disabled_one_check(self):
        """Checking -d all -e odoolint -d ONLY-ONE-CHECK"""
        for disable_error in EXPECTED_ERRORS:
            expected_errors = self.expected_errors.copy()
            enable = "--disable=%s" % disable_error
            pylint_res = self.run_pylint(self.paths_modules, self.default_extra_params + [enable])
            real_errors = pylint_res.linter.stats.by_msg
            expected_errors.pop(disable_error)
            self.assertDictEqual(real_errors, expected_errors)


if __name__ == "__main__":
    unittest.main()