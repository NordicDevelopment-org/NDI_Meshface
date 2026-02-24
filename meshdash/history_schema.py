from typing import Any

from .history_schema_indexes import (
    INDEX_SCHEMA_STATEMENTS as _INDEX_SCHEMA_STATEMENTS,
)
from .history_schema_tables import (
    TABLE_SCHEMA_STATEMENTS as _TABLE_SCHEMA_STATEMENTS,
)


SCHEMA_STATEMENTS = _TABLE_SCHEMA_STATEMENTS + _INDEX_SCHEMA_STATEMENTS


def initialize_history_schema(conn: Any) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
