"""Fixtures partagées. Les tests utilisent les données locales nycflights13 : aucun secret nécessaire (CI)."""

import importlib.util
from pathlib import Path

import pytest

APP_FILE = Path(__file__).resolve().parents[1] / "app" / "app.py"


@pytest.fixture(scope="session")
def cache_dir(tmp_path_factory):
    """Cache dans un dossier temporaire, pour ne jamais toucher app/cache/."""
    import data_source

    path = tmp_path_factory.mktemp("cache")
    data_source.CACHE_DIR = path
    return path


@pytest.fixture(scope="session")
def app_data(cache_dir):
    from data_source import load_app_data

    return load_app_data(source="local", refresh=True)


@pytest.fixture(scope="session")
def shiny_app(app_data):
    """L'objet App de app/app.py, chargé comme le ferait `shiny run` (données locales, cache déjà construit)."""
    mp = pytest.MonkeyPatch()
    mp.setenv("DATA_SOURCE", "local")       # prioritaire sur un éventuel .env local (load_dotenv n'écrase pas)
    mp.setenv("REFRESH_CACHE", "false")
    spec = importlib.util.spec_from_file_location("shiny_app_under_test", APP_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module.app
    mp.undo()
