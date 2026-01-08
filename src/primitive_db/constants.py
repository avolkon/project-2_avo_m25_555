"""project-2_avo_m25_555_src_primitive_db_constants.py
Primitive DB - Константы и конфигурация проекта."""

import os
from typing import Final

# Базовые пути проекта
BASE_DIR: Final[str] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR: Final[str] = os.path.join(BASE_DIR, "data")
TABLES_DIR: Final[str] = os.path.join(DATA_DIR, "tables")
META_FILE: Final[str] = os.path.join(DATA_DIR, "db_meta.json")

# Поддерживаемые типы данных для столбцов
VALID_TYPES: Final[set[str]] = {"int", "str", "bool"}

# Определение столбца ID (автоматически добавляется ко всем таблицам)
ID_COLUMN: Final[str] = "ID"
ID_TYPE: Final[str] = "int"
ID_COLUMN_DEF: Final[str] = f"{ID_COLUMN}:{ID_TYPE}"

# Сообщения об ошибках (используются в функциях валидации)
ERROR_TABLE_EXISTS: Final[str] = "Ошибка: Таблица '{}' уже существует."
ERROR_TABLE_NOT_FOUND: Final[str] = "Ошибка: Таблица '{}' не существует."
ERROR_INVALID_TYPE: Final[str] = (
    "Ошибка: Неподдерживаемый тип '{}'. Поддерживаемые типы: {}"
)
ERROR_INVALID_COLUMN_FORMAT: Final[str] = (
    "Ошибка: Неверный формат столбца '{}'. Используйте формат 'имя:тип'"
)

# Сообщения об успешном выполнении операций
SUCCESS_TABLE_CREATED: Final[str] = "Таблица '{}' успешно создана со столбцами: {}"
SUCCESS_TABLE_DROPPED: Final[str] = "Таблица '{}' успешно удалена."

# Основные команды CLI (используются в парсинге и диспетчеризации)
COMMAND_CREATE_TABLE: Final[str] = "create_table"
COMMAND_DROP_TABLE: Final[str] = "drop_table"
COMMAND_LIST_TABLES: Final[str] = "list_tables"
COMMAND_HELP: Final[str] = "help"
COMMAND_EXIT: Final[str] = "exit"

__all__ = [
    "META_FILE",
    "DATA_DIR",
    "TABLES_DIR",
    "VALID_TYPES",
    "ID_COLUMN",
    "ID_TYPE",
    "ID_COLUMN_DEF",
    "ERROR_TABLE_EXISTS",
    "ERROR_TABLE_NOT_FOUND",
    "ERROR_INVALID_TYPE",
    "ERROR_INVALID_COLUMN_FORMAT",
    "SUCCESS_TABLE_CREATED",
    "SUCCESS_TABLE_DROPPED",
    "COMMAND_CREATE_TABLE",
    "COMMAND_DROP_TABLE",
    "COMMAND_LIST_TABLES",
    "COMMAND_HELP",
    "COMMAND_EXIT",
]
