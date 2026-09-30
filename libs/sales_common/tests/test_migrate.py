from pathlib import Path

import pytest

from sales_common import migrate

REPO_DB = Path(__file__).resolve().parents[3] / "db"


def test_db_dir_found_from_cwd_outside_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert migrate.find_db_dir() == REPO_DB


def test_cwd_db_dir_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_DIR", raising=False)
    (tmp_path / "db" / "migrations").mkdir(parents=True)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert migrate.find_db_dir() == tmp_path / "db"


def test_db_dir_env_override(tmp_path, monkeypatch):
    (tmp_path / "migrations").mkdir()
    monkeypatch.setenv("DB_DIR", str(tmp_path))
    assert migrate.find_db_dir() == tmp_path
    monkeypatch.setenv("DB_DIR", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError):
        migrate.find_db_dir()


def test_not_found_outside_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(migrate, "__file__", str(tmp_path / "site" / "sales_common" / "migrate.py"))
    if Path("/app/db/migrations").is_dir():
        pytest.skip("/app/db exists on this machine")
    with pytest.raises(FileNotFoundError):
        migrate.find_db_dir()
