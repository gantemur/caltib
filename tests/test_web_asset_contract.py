"""Offline checks for the locally shipped browser dependencies."""

import ast
from html.parser import HTMLParser
from pathlib import Path
import re
from zipfile import ZipFile, is_zipfile


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WHEEL = "caltib-0.3.2-py3-none-any.whl"


class BrowserMarkup(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.scripts = []
        self.config = []
        self.inline_scripts = []
        self._tag = None
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        if tag in ("py-config", "script"):
            self._tag = tag
        if tag == "script":
            self.scripts.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == self._tag:
            self._tag = None

    def handle_data(self, data):
        if self._tag == "py-config":
            self.config.append(data)
        elif self._tag == "script":
            self.inline_scripts.append(data)


def test_browser_pages_install_the_checked_in_wheel():
    app = BrowserMarkup(DOCS / "app.html")
    diag = BrowserMarkup(DOCS / "diag.html")
    packages = re.search(r"\bpackages\s*=\s*(\[[^\]]*\])", "".join(app.config))
    install = re.search(
        r"\bmicropip\.install\s*\(\s*(\[[^\]]*\])",
        "".join(diag.inline_scripts),
    )
    assert packages is not None, "Calendar must configure its local package"
    assert install is not None, "Diagnostics must install its local package"
    for package_list in (packages.group(1), install.group(1)):
        paths = ast.literal_eval(package_list)
        assert any(path in (WHEEL, "./" + WHEEL) for path in paths)
    assert (DOCS / WHEEL).is_file()


def test_browser_wheel_contains_required_modules():
    path = DOCS / WHEEL
    assert is_zipfile(path)
    required = {
        "caltib/__init__.py",
        "caltib/api.py",
        "caltib/i18n.py",
        "caltib/core/types.py",
        "caltib/engines/specs.py",
        "caltib/web_diag/api.py",
        "caltib/reference/solar.py",
        "caltib/reference/lunar.py",
    }
    with ZipFile(path) as wheel:
        assert wheel.testzip() is None
        assert required <= set(wheel.namelist())


def test_browser_python_entry_points_remain_available():
    app = BrowserMarkup(DOCS / "app.html")
    assert any(
        script.get("type") == "py"
        and script.get("src") in ("app_logic.py", "./app_logic.py")
        for script in app.scripts
    )
    assert (DOCS / "app_logic.py").is_file()
    assert (ROOT / "src/caltib/web_diag/api.py").is_file()
    diag = BrowserMarkup(DOCS / "diag.html")
    assert re.search(
        r"from\s+caltib\.web_diag\.api\s+import\s+handle_request\b",
        "".join(diag.inline_scripts),
    )


def test_mkdocs_navigation_keeps_both_browser_pages():
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav = re.search(r"(?ms)^nav:\s*\n((?:[ \t]+[^\n]*(?:\n|$))*)", config)
    assert nav is not None
    entries = re.findall(
        r"(?m)^\s*-\s+[^\n]+?:\s*['\"]?((?:app|diag)\.html)['\"]?\s*$",
        nav.group(1),
    )
    assert {"app.html", "diag.html"} <= set(entries)
