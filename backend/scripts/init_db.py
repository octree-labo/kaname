"""db/schema.sql を DATABASE_URL に対して実行する。

SQLAlchemyモデルはあくまで既存テーブル/ビューへのマッピングであり、
テーブル定義そのものは schema.sql を正とする（VIEWはORMのmetadata.create_allでは
作成できないため）。
"""
from __future__ import annotations

import pathlib
import sys

import psycopg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.config import settings  # noqa: E402

SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def _to_psycopg_dsn(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    dsn = _to_psycopg_dsn(settings.database_url)
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print(f"applied {SCHEMA_PATH} to {settings.database_url}")


if __name__ == "__main__":
    main()
