"""
Модуль ядра базы данных.
Содержит базовые классы моделей: Column, Row, Table, Database.
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class InvalidDataTypeError(ValueError):
    """Исключение для неподдерживаемого типа данных."""
    pass


class TableAlreadyExistsError(ValueError):
    """Исключение при попытке создать существующую таблицу."""
    pass


class TableNotFoundError(ValueError):
    """Исключение при обращении к несуществующей таблице."""
    pass


# Константы для типов данных
SUPPORTED_TYPES = {"int": int, "str": str, "bool": bool}
DEFAULT_ID_COLUMN_NAME = "ID"
DEFAULT_ID_COLUMN_TYPE = "int"


class Column:
    """Представляет столбец таблицы с типом данных."""

    def __init__(self, name: str, data_type: str):
        """
        Инициализация столбца.

        Args:
            name: Название столбца
            data_type: Тип данных (int, str, bool)
        """
        self.name = name
        self.data_type = data_type
        self._validate()

    def _validate(self) -> None:
        """Проверяет корректность типа данных."""
        if self.data_type not in SUPPORTED_TYPES:
            raise InvalidDataTypeError(
                f"Неподдерживаемый тип: {self.data_type}. "
                f"Допустимые типы: {list(SUPPORTED_TYPES.keys())}"
            )

    def to_dict(self) -> Dict[str, str]:
        """Сериализует столбец в словарь."""
        return {"name": self.name, "type": self.data_type}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Column':
        """Создает столбец из словаря."""
        return cls(data["name"], data["type"])

    def __repr__(self) -> str:
        return f"Column(name='{self.name}', type='{self.data_type}')"

    def __str__(self) -> str:
        return f"{self.name}:{self.data_type}"


class Row:
    """Представляет строку данных в таблице."""

    def __init__(self, data: Dict[str, Any], columns: List[Column]):
        """
        Инициализация строки.

        Args:
            data: Словарь с данными строки
            columns: Список столбцов таблицы для валидации
        """
        self._data = data
        self._columns = {col.name: col for col in columns}
        self._validate()

    def _validate(self) -> None:
        """Проверяет соответствие данных типам столбцов."""
        for col_name, column in self._columns.items():
            if col_name not in self._data:
                raise KeyError(f"Отсутствует значение для столбца '{col_name}'")

            value = self._data[col_name]
            expected_type = SUPPORTED_TYPES[column.data_type]

            # Проверка типа с учетом преобразования из JSON
            if expected_type == bool:
                # В JSON bool приходит как True/False
                if not isinstance(value, bool):
                    raise ValueError(
                        f"Значение '{value}' не является bool для столбца '{col_name}'"
                    )
            elif not isinstance(value, expected_type):
                # Для int и str проверяем точное соответствие
                raise ValueError(
                    f"Ожидался тип {column.data_type} для '{col_name}', "
                    f"получен {type(value).__name__}"
                )

    def __getitem__(self, column_name: str) -> Any:
        """Получает значение по имени столбца."""
        if column_name not in self._columns:
            raise KeyError(f"Столбец '{column_name}' не существует")
        return self._data[column_name]

    def __setitem__(self, column_name: str, value: Any) -> None:
        """Устанавливает значение для столбца."""
        if column_name not in self._columns:
            raise KeyError(f"Столбец '{column_name}' не существует")
        
        column = self._columns[column_name]
        expected_type = SUPPORTED_TYPES[column.data_type]
        
        # Валидация типа
        if expected_type == bool:
            if not isinstance(value, bool):
                raise ValueError(
                    f"Значение '{value}' не является bool для столбца '{column_name}'"
                )
        elif not isinstance(value, expected_type):
            raise ValueError(
                f"Ожидался тип {column.data_type} для '{column_name}', "
                f"получен {type(value).__name__}"
            )
        
        self._data[column_name] = value

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует строку в словарь."""
        return self._data.copy()

    def __repr__(self) -> str:
        return f"Row({self._data})"


class Table:
    """Представляет таблицу базы данных."""

    def __init__(self, name: str, columns: List[Column], next_id: int = 1):
        """
        Инициализация таблицы.

        Args:
            name: Имя таблицы
            columns: Список столбцов
            next_id: Следующий ID для автоинкремента
        """
        self.name = name
        self.columns = columns
        self.next_id = next_id
        self._id_column = DEFAULT_ID_COLUMN_NAME
        
        # Проверяем наличие ID столбца
        if not any(col.name == self._id_column for col in self.columns):
            # Добавляем ID столбец в начало
            self.columns.insert(0, Column(self._id_column, DEFAULT_ID_COLUMN_TYPE))
        
        # Создаем индекс для быстрого доступа к столбцам
        self._column_index = {col.name: col for col in self.columns}
    
    @property
    def column_names(self) -> List[str]:
        """Возвращает список имен столбцов."""
        return [col.name for col in self.columns]
    
    def validate_row_data(self, values: List[Any], skip_id: bool = True) -> Dict[str, Any]:
        """
        Валидирует данные строки и создает словарь.

        Args:
            values: Список значений
            skip_id: Пропустить ID столбец (True для insert)

        Returns:
            Словарь с данными строки
        """
        # Определяем, сколько столбцов нужно заполнить
        columns_to_fill = self.columns[1:] if skip_id else self.columns
        
        if len(values) != len(columns_to_fill):
            raise ValueError(
                f"Ожидалось {len(columns_to_fill)} значений, получено {len(values)}"
            )
        
        # Создаем словарь данных
        row_data = {}
        if skip_id:
            row_data[self._id_column] = self.next_id
        
        for column, value in zip(columns_to_fill, values):
            # Преобразуем значение к нужному типу
            expected_type = SUPPORTED_TYPES[column.data_type]
            
            try:
                if expected_type == bool:
                    # Специальная обработка bool из строки
                    if isinstance(value, str):
                        value_lower = value.lower()
                        if value_lower in ('true', '1', 'yes'):
                            value = True
                        elif value_lower in ('false', '0', 'no'):
                            value = False
                        else:
                            raise ValueError(f"Неверное значение bool: {value}")
                elif expected_type == int:
                    value = int(value)
                elif expected_type == str:
                    value = str(value)
                
                row_data[column.name] = value
                
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Ошибка преобразования '{value}' в тип {column.data_type} "
                    f"для столбца '{column.name}': {e}"
                )
        
        return row_data
    
    def increment_id(self) -> int:
        """Увеличивает next_id и возвращает предыдущее значение."""
        current_id = self.next_id
        self.next_id += 1
        return current_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует таблицу в словарь."""
        return {
            "columns": [col.to_dict() for col in self.columns],
            "next_id": self.next_id
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Table':
        """Создает таблицу из словаря."""
        columns = [Column.from_dict(col_data) for col_data in data["columns"]]
        next_id = data.get("next_id", 1)
        return cls(name, columns, next_id)
    
    def __repr__(self) -> str:
        columns_str = ", ".join(str(col) for col in self.columns)
        return f"Table(name='{self.name}', columns=[{columns_str}], next_id={self.next_id})"


class Database:
    """Основной класс базы данных."""

    def __init__(self, metadata_storage: Any = None, data_storage: Any = None):
        """
        Инициализация базы данных.

        Args:
            metadata_storage: Хранилище метаданных (будет реализовано позже)
            data_storage: Хранилище данных таблиц (будет реализовано позже)
        """
        self.metadata_storage = metadata_storage
        self.data_storage = data_storage
        self.tables: Dict[str, Table] = {}
        self._load_initial_data()
    
    def _load_initial_data(self) -> None:
        """Загружает начальные данные при инициализации."""
        # Временная заглушка - будет заменена при реализации хранилищ
        self.tables = {}
    
    def create_table(self, name: str, columns: List[Column]) -> Table:
        """
        Создает новую таблицу.

        Args:
            name: Имя таблицы
            columns: Список столбцов

        Returns:
            Созданная таблица

        Raises:
            TableAlreadyExistsError: Если таблица уже существует
        """
        if name in self.tables:
            raise TableAlreadyExistsError(f"Таблица '{name}' уже существует")
        
        table = Table(name, columns)
        self.tables[name] = table
        
        # TODO: Сохранение метаданных будет реализовано позже
        if self.metadata_storage:
            self._save_metadata()
        
        return table
    
    def drop_table(self, name: str) -> bool:
        """
        Удаляет таблицу.

        Args:
            name: Имя таблицы

        Returns:
            True если удаление успешно

        Raises:
            TableNotFoundError: Если таблица не существует
        """
        if name not in self.tables:
            raise TableNotFoundError(f"Таблица '{name}' не найдена")
        
        del self.tables[name]
        
        # TODO: Удаление данных таблицы будет реализовано позже
        if self.metadata_storage:
            self._save_metadata()
        
        return True
    
    def get_table(self, name: str) -> Table:
        """
        Получает таблицу по имени.

        Args:
            name: Имя таблицы

        Returns:
            Объект таблицы

        Raises:
            TableNotFoundError: Если таблица не существует
        """
        if name not in self.tables:
            raise TableNotFoundError(f"Таблица '{name}' не найдена")
        return self.tables[name]
    
    def list_tables(self) -> List[str]:
        """Возвращает список имен всех таблиц."""
        return list(self.tables.keys())
    
    def _save_metadata(self) -> None:
        """Сохраняет метаданные базы данных."""
        # TODO: Будет реализовано при интеграции хранилищ
        metadata = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            }
        }
        if self.metadata_storage:
            # Здесь будет вызов метода save хранилища
            pass
    
    def __repr__(self) -> str:
        tables_count = len(self.tables)
        return f"Database(tables={tables_count})"
    