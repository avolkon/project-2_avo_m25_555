"""
Primitive Database - простая база данных на Python.

Основные классы:
- Database: Основной класс базы данных
- Table: Представление таблицы
- Column: Столбец таблицы с типом данных
- Row: Строка данных таблицы

Исключения:
- InvalidDataTypeError: Неподдерживаемый тип данных
- TableAlreadyExistsError: Таблица уже существует
- TableNotFoundError: Таблица не найдена
"""

from .core import (
    CachedJsonTableStorage,
    Column,
    Command,
    CommandResult,
    CreateTableCommand,
    Database,
    DropTableCommand,
    InfoTableCommand,
    InvalidDataTypeError,
    JsonMetadataStorage,
    ListTablesCommand,
    MetadataStorage,
    ParseError,
    Row,
    StorageError,
    Table,
    TableAlreadyExistsError,
    TableDataStorage,
    TableNotFoundError,
)
from .decorators import confirm_action, create_cacher, handle_db_errors, log_time
from .parser import (
    CommandParser,
    ConditionParser,
    DeleteCommand,
    ExitCommand,
    HelpCommand,
    InsertCommand,
    SelectCommand,
    UpdateCommand,
    ValueParser,
)

__all__ = [
    "Database",
    "Table",
    "Column",
    "Row",
    "InvalidDataTypeError",
    "TableAlreadyExistsError",
    "TableNotFoundError",
    "StorageError",
    "MetadataStorage",
    "TableDataStorage",
    "JsonMetadataStorage",
    "CachedJsonTableStorage",
    "ParseError",
    "CommandResult",
    "Command",
    "CreateTableCommand",
    "DropTableCommand",
    "ListTablesCommand",
    "InfoTableCommand",
    "CommandParser",
    "ValueParser",
    "ConditionParser",
    "InsertCommand",  # Должен быть импортирован
    "SelectCommand",  # Должен быть импортирован
    "UpdateCommand",  # Должен быть импортирован
    "DeleteCommand",  # Должен быть импортирован
    "HelpCommand",  # Должен быть импортирован
    "ExitCommand",  # Должен быть импортирован
    "handle_db_errors",
    "confirm_action",
    "log_time",
    "create_cacher",
]

__version__ = "0.1.0"
__author__ = "Primitive DB Team"
