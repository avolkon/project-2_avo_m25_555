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
    Database,
    Table,
    Column,
    Row,
    InvalidDataTypeError,
    TableAlreadyExistsError,
    TableNotFoundError
)

__all__ = [
    'Database',
    'Table',
    'Column',
    'Row',
    'InvalidDataTypeError',
    'TableAlreadyExistsError',
    'TableNotFoundError'
]

__version__ = '0.1.0'
__author__ = 'Primitive DB Team'

