"""
Модуль ядра базы данных.
Содержит базовые классы моделей: Column, Row, Table, Database.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

# Импортируем декораторы из нового модуля
try:
    from .decorators import confirm_action, handle_db_errors, log_time
except ImportError:
    # Fallback для случаев когда decorators.py еще не создан

    def handle_db_errors(func):
        return func

    def confirm_action(action_name):
        def decorator(func):
            return func
        return decorator

    def log_time(func):
        return func


class InvalidDataTypeError(ValueError):
    """Исключение для неподдерживаемого типа данных."""

    pass


class TableAlreadyExistsError(ValueError):
    """Исключение при попытке создать существующую таблицу."""

    pass


class TableNotFoundError(ValueError):
    """Исключение при обращении к несуществующей таблице."""

    pass


class StorageError(Exception):
    """Базовое исключение для ошибок хранилища."""

    pass


class MetadataStorage(ABC):
    """Абстрактное хранилище метаданных БД."""

    @abstractmethod
    def save(self, metadata: dict) -> bool:
        """Сохраняет метаданные."""
        pass

    @abstractmethod
    def load(self) -> dict:
        """Загружает метаданные."""
        pass


class TableDataStorage(ABC):
    """Абстрактное хранилище данных таблиц."""

    @abstractmethod
    def save(self, table_name: str, data: list) -> bool:
        """Сохраняет данные таблицы."""
        pass

    @abstractmethod
    def load(self, table_name: str) -> list:
        """Загружает данные таблицы."""
        pass

    @abstractmethod
    def exists(self, table_name: str) -> bool:
        """Проверяет существование данных таблицы."""
        pass


class JsonMetadataStorage(MetadataStorage):
    """JSON-хранилище метаданных с атомарными операциями."""

    def __init__(self, filepath: str = "db_meta.json"):
        """
        Инициализация JSON хранилища метаданных.

        Args:
            filepath: Путь к файлу метаданных
        """
        self.filepath = Path(filepath)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Создает директорию для файла если её нет."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def save(self, metadata: dict) -> bool:
        """Атомарно сохраняет метаданные."""
        temp_file = self.filepath.with_suffix(".tmp")

        try:
            # Создаем временный файл с данными
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Атомарная замена старого файла новым
            temp_file.replace(self.filepath)
            return True

        except Exception as e:
            # Удаляем временный файл при ошибке
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass  # Игнорируем ошибки удаления
            raise StorageError(f"Ошибка сохранения метаданных: {e}")

    def load(self) -> dict:
        """Загружает метаданные, возвращает {} если файла нет."""
        if not self.filepath.exists():
            return {}

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Логируем ошибку но возвращаем пустой словарь
            print(f"⚠️ Предупреждение: Ошибка чтения JSON {self.filepath}: {e}")
            return {}
        except Exception as e:
            raise StorageError(f"Ошибка загрузки метаданных: {e}")


class CachedJsonTableStorage(TableDataStorage):
    """JSON-хранилище данных таблиц с кэшированием."""

    def __init__(self, tables_dir: str = "data/tables", cache_ttl: int = 300):
        """
        Инициализация кэширующего хранилища таблиц.

        Args:
            tables_dir: Директория для файлов таблиц
            cache_ttl: Время жизни кэша в секундах
        """
        self.tables_dir = Path(tables_dir)
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple] = {}
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Создает директорию для таблиц если её нет."""
        self.tables_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, table_name: str) -> str:
        """Генерирует ключ кэша для таблицы."""
        return f"table_{table_name}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Проверяет валидность кэша по времени.

        Returns:
            True если кэш валиден, False если устарел или отсутствует
        """
        if cache_key not in self._cache:
            return False

        _, timestamp = self._cache[cache_key]
        return time.time() - timestamp < self.cache_ttl

    def load(self, table_name: str) -> list:
        """Загружает данные таблицы с использованием кэша."""
        cache_key = self._get_cache_key(table_name)

        # Проверяем валидный кэш
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            data, _ = self._cache[cache_key]
            return data.copy()  # Возвращаем копию для безопасности

        # Загрузка из файла
        filepath = self.tables_dir / f"{table_name}.json"
        if not filepath.exists():
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ Предупреждение: Ошибка чтения таблицы {table_name}: {e}")
            data = []
        except Exception as e:
            raise StorageError(f"Ошибка загрузки таблицы {table_name}: {e}")

        # Сохраняем в кэш
        self._cache[cache_key] = (data.copy(), time.time())
        return data

    def save(self, table_name: str, data: list) -> bool:
        """Сохраняет данные таблицы и инвалидирует кэш."""
        filepath = self.tables_dir / f"{table_name}.json"
        temp_file = filepath.with_suffix(".tmp")

        # Инициализируем backup_data перед блоком try
        backup_data = None

        try:
            # Создаем резервную копию существующих данных
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        backup_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    backup_data = []  # Если файл поврежден

            # Сохраняем во временный файл
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Атомарная замена файла
            temp_file.replace(filepath)

            # Инвалидируем кэш
            cache_key = self._get_cache_key(table_name)
            if cache_key in self._cache:
                del self._cache[cache_key]

            return True

        except Exception as e:
            # Восстанавливаем из резервной копии при ошибке
            if backup_data is not None and filepath.exists():
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(backup_data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass  # Игнорируем ошибки восстановления

            # Удаляем временный файл
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

            raise StorageError(f"Ошибка сохранения таблицы {table_name}: {e}")

    def exists(self, table_name: str) -> bool:
        """Проверяет существование файла таблицы."""
        filepath = self.tables_dir / f"{table_name}.json"
        return filepath.exists()

    def clear_cache(self) -> None:
        """Очищает весь кэш."""
        self._cache.clear()


# Исключения для парсера
class ParseError(ValueError):
    """Исключение при ошибке парсинга команд."""

    pass


# Классы системы команд
class CommandResult:
    """Результат выполнения команды."""

    def __init__(
        self,
        success: bool,
        message: str,
        data: Optional[dict] = None,
        execution_time: float = 0.0,
        requires_confirmation: bool = False,
    ):
        """
        Инициализация результата команды.

        Args:
            success: Успешность выполнения
            message: Сообщение для пользователя
            data: Данные для кэширования (опционально)
            execution_time: Время выполнения в секундах
            requires_confirmation: Требуется ли подтверждение
        """
        self.success = success
        self.message = message
        self.data = data or {}
        self.execution_time = execution_time
        self.requires_confirmation = requires_confirmation

    def __str__(self) -> str:
        """Строковое представление результата."""
        status = "✅ Успешно" if self.success else "❌ Ошибка"
        time_str = f" ({self.execution_time:.3f}с)" if self.execution_time > 0 else ""
        return f"{status}: {self.message}{time_str}"


class Command(ABC):
    """Абстрактный класс команды."""

    def __init__(self, database: "Database"):
        """
        Инициализация команды.

        Args:
            database: Экземпляр базы данных
        """
        self.database = database
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    @abstractmethod
    def execute(self) -> CommandResult:
        """Выполняет команду и возвращает результат."""
        pass

    def _start_timer(self) -> None:
        """Начинает замер времени выполнения."""
        self.start_time = time.monotonic()

    def _stop_timer(self) -> float:
        """Останавливает таймер и возвращает время выполнения."""
        if self.start_time is None:
            return 0.0
        self.end_time = time.monotonic()
        return self.end_time - self.start_time


# Конкретные реализации команд
class CreateTableCommand(Command):
    """Команда создания таблицы."""

    def __init__(self, database: Database, table_name: str, columns_def: List[str]):
        """
        Инициализация команды создания таблицы.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
            columns_def: Список определений столбцов в формате "имя:тип"
        """
        super().__init__(database)
        self.table_name = table_name
        self.columns_def = columns_def

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет создание таблицы."""
        # Создаем столбцы из определений
        columns = []
        for col_def in self.columns_def:
            if ":" not in col_def:
                raise ParseError(f"Некорректное определение столбца: {col_def}")

            name, col_type = col_def.split(":", 1)
            columns.append(Column(name.strip(), col_type.strip()))

        # Создаем таблицу
        table = self.database.create_table(self.table_name, columns)

        return CommandResult(
            success=True,
            message=f'Таблица "{self.table_name}" успешно создана со столбцами: '
            f'{", ".join(str(c) for c in table.columns)}',
            data={"table_name": self.table_name, "columns": columns},
        )


class DropTableCommand(Command):
    """Команда удаления таблицы."""

    def __init__(self, database: Database, table_name: str):
        """
        Инициализация команды удаления таблицы.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы для удаления
        """
        super().__init__(database)
        self.table_name = table_name

    @confirm_action("удаление таблицы")
    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет удаление таблицы."""
        success = self.database.drop_table(self.table_name)

        return CommandResult(
            success=success,
            message=f'Таблица "{self.table_name}" успешно удалена.',
            data={"table_name": self.table_name},
        )


class ListTablesCommand(Command):
    """Команда вывода списка таблиц."""

    def __init__(self, database: Database):
        """
        Инициализация команды вывода списка таблиц.

        Args:
            database: Экземпляр базы данных
        """
        super().__init__(database)

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет вывод списка таблиц."""
        tables = self.database.list_tables()

        if not tables:
            message = "В базе данных нет таблиц."
        else:
            table_list = "\n- " + "\n- ".join(tables)
            message = f"Список таблиц:{table_list}"

        return CommandResult(
            success=True, message=message, data={"tables": tables, "count": len(tables)}
        )


class InfoTableCommand(Command):
    """Команда вывода информации о таблице."""

    def __init__(self, database: Database, table_name: str):
        """
        Инициализация команды вывода информации о таблице.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
        """
        super().__init__(database)
        self.table_name = table_name

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет вывод информации о таблице."""
        table = self.database.get_table(self.table_name)

        # Загружаем данные таблицы для подсчета записей
        data = self.database.data_storage.load(self.table_name)
        record_count = len(data)

        columns_str = ", ".join(str(col) for col in table.columns)

        return CommandResult(
            success=True,
            message=f"Таблица: {self.table_name}\n"
            f"Столбцы: {columns_str}\n"
            f"Количество записей: {record_count}",
            data={
                "table_name": self.table_name,
                "columns": table.columns,
                "record_count": record_count,
            },
        )


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
    def from_dict(cls, data: Dict[str, str]) -> "Column":
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

        # Ссылка на хранилище данных (будет установлена Database)
        self._data_storage: Optional[CachedJsonTableStorage] = None
        # Ссылка на родительскую базу данных для сохранения метаданных
        self._database_ref: Optional[Database] = None

    @property
    def column_names(self) -> List[str]:
        """Возвращает список имен столбцов."""
        return [col.name for col in self.columns]

    def validate_row_data(
        self, values: List[Any], skip_id: bool = True
    ) -> Dict[str, Any]:
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
                        if value_lower in ("true", "1", "yes"):
                            value = True
                        elif value_lower in ("false", "0", "no"):
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
            "next_id": self.next_id,
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "Table":
        """Создает таблицу из словаря."""
        columns = [Column.from_dict(col_data) for col_data in data["columns"]]
        next_id = data.get("next_id", 1)
        return cls(name, columns, next_id)
    
    def __repr__(self) -> str:
        columns_str = ", ".join(str(col) for col in self.columns)
        return (
            f"Table(name='{self.name}', columns=[{columns_str}], "
            f"next_id={self.next_id})"
        )

    def set_data_storage(self, data_storage: CachedJsonTableStorage, 
                        database_ref: Optional[Database] = None) -> None:
        """
        Устанавливает хранилище данных для таблицы.
        Args:
            data_storage: Экземпляр хранилища данных
            database_ref: Ссылка на родительскую базу данных
        """
        self._data_storage = data_storage
        self._database_ref = database_ref

    def insert(self, values: List[Any]) -> int:
        """
        Вставляет новую запись в таблицу.
        
        Args:
            values: Список значений для вставки (без ID)
            
        Returns:
            ID вставленной записи
            
        Raises:
            ValueError: При ошибке валидации данных
            RuntimeError: Если хранилище данных не установлено
        """
        # Проверяем наличие хранилища данных
        if not self._data_storage:
            raise RuntimeError("Хранилище данных не установлено для таблицы")
        
        # Валидируем данные и создаем словарь строки
        row_data = self.validate_row_data(values)
        row_id = row_data[self._id_column]
        
        # Загружаем текущие данные таблицы
        current_data = self._data_storage.load(self.name)
        
        # Добавляем новую запись
        current_data.append(row_data)
        
        # Сохраняем обновленные данные
        self._data_storage.save(self.name, current_data)
        
        # Увеличиваем next_id для следующей вставки
        self.next_id += 1
        
        # Сохраняем метаданные таблицы
        self._save_metadata()
        
        return row_id

    def select(self, conditions: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Row]:
        """
        Выбирает записи по условиям.
        
        Args:
            conditions: Словарь условий в формате 
                       {"column": {"operator": "=", "value": value}}
            
        Returns:
            Список объектов Row, удовлетворяющих условиям
        """
        # Проверяем наличие хранилища данных
        if not self._data_storage:
            raise RuntimeError("Хранилище данных не установлено для таблицы")
        
        # Загружаем данные таблицы
        data = self._data_storage.load(self.name)
        
        # Фильтруем данные по условиям
        if conditions:
            filtered_data = []
            for record in data:
                if self._matches_conditions(record, conditions):
                    filtered_data.append(record)
            data = filtered_data
        
        # Преобразуем данные в объекты Row
        rows = []
        for record in data:
            rows.append(Row(record, self.columns))
            
        return rows

    def update(self, set_clause: Dict[str, Any], 
               where_clause: Optional[Dict[str, Dict[str, Any]]] = None) -> int:
        """
        Обновляет записи в таблице.
        
        Args:
            set_clause: Словарь с данными для обновления {"column": new_value}
            where_clause: Условия для фильтрации записей
            
        Returns:
            Количество обновленных записей
        """
        # Проверяем наличие хранилища данных
        if not self._data_storage:
            raise RuntimeError("Хранилище данных не установлено для таблицы")
        
        # Загружаем данные таблицы
        data = self._data_storage.load(self.name)
        updated_count = 0
        
        # Обновляем записи
        for i, record in enumerate(data):
            # Проверяем условия WHERE
            if where_clause and not self._matches_conditions(record, where_clause):
                continue
                
            # Обновляем поля согласно SET
            for column_name, new_value in set_clause.items():
                # Валидируем тип данных
                if column_name in self._column_index:
                    column = self._column_index[column_name]
                    expected_type = SUPPORTED_TYPES[column.data_type]
                    
                    # Преобразуем значение к нужному типу
                    try:
                        if expected_type == bool and isinstance(new_value, str):
                            new_value = new_value.lower() in ("true", "1", "yes")
                        elif expected_type == int and isinstance(new_value, str):
                            new_value = int(new_value)
                        elif expected_type == str:
                            new_value = str(new_value)
                            
                        record[column_name] = new_value
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Ошибка преобразования '{new_value}' в тип "
                            f"{column.data_type} для столбца '{column_name}': {e}"
                        )
            
            updated_count += 1
            data[i] = record  # Обновляем запись в списке
        
        # Сохраняем обновленные данные, если были изменения
        if updated_count > 0:
            self._data_storage.save(self.name, data)
            
        return updated_count

    def delete(self, where_clause: Optional[Dict[str, Dict[str, Any]]] = None) -> int:
        """
        Удаляет записи из таблицы.
        
        Args:
            where_clause: Условия для фильтрации записей
            
        Returns:
            Количество удаленных записей
        """
        # Проверяем наличие хранилища данных
        if not self._data_storage:
            raise RuntimeError("Хранилище данных не установлено для таблицы")
        
        # Загружаем данные таблицы
        data = self._data_storage.load(self.name)
        
        # Фильтруем записи для удаления
        if where_clause:
            filtered_data = [
                record for record in data 
                if not self._matches_conditions(record, where_clause)
            ]
        else:
            # Если условия нет, удаляем все записи
            filtered_data = []
        
        # Подсчитываем количество удаленных записей
        deleted_count = len(data) - len(filtered_data)
        
        # Сохраняем отфильтрованные данные, если были удаления
        if deleted_count > 0:
            self._data_storage.save(self.name, filtered_data)
            
        return deleted_count

    def _matches_conditions(self, record: Dict[str, Any], 
                           conditions: Dict[str, Dict[str, Any]]) -> bool:
        """
        Проверяет, удовлетворяет ли запись всем условиям.
        
        Args:
            record: Словарь с данными записи
            conditions: Словарь условий
            
        Returns:
            True если запись удовлетворяет всем условиям
        """
        for column_name, condition in conditions.items():
            operator = condition.get("operator", "=")
            expected_value = condition.get("value")
            
            # Проверяем наличие столбца в записи
            if column_name not in record:
                return False
                
            actual_value = record[column_name]
            
            # Сравниваем значения по оператору
            if not self._compare_values(actual_value, operator, expected_value):
                return False
                
        return True

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """
        Сравнивает значения по заданному оператору.
        
        Args:
            actual: Фактическое значение
            operator: Оператор сравнения (=, !=, <, >, <=, >=)
            expected: Ожидаемое значение
            
        Returns:
            Результат сравнения
        """
        operators = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
        }
        
        if operator not in operators:
            raise ValueError(f"Неподдерживаемый оператор: {operator}")
            
        return operators[operator](actual, expected)
    
    def _save_metadata(self) -> None:
        """
        Сохраняет метаданные таблицы.
        Обновляет next_id в родительской базе данных.
        """
        if self._database_ref:
            try:
                # Обновляем метаданные таблицы в базе данных
                self._database_ref.tables[self.name] = self
                # Вызываем сохранение метаданных
                if hasattr(self._database_ref, '_save_metadata'):
                    self._database_ref._save_metadata()
            except (AttributeError, KeyError):
                # Если не удалось сохранить, игнорируем
                pass

    def _save_table_metadata(self) -> None:
        """
        Сохраняет метаданные таблицы (next_id).
        Вызывается после изменения таблицы (insert, update, delete).
        """
        if self._database_ref and hasattr(self._database_ref, '_save_metadata'):
            # Вызываем сохранение метаданных через базу данных
            self._database_ref._save_metadata()
        else:
            # Если ссылки на базу данных нет, просто увеличиваем next_id
            # Метаданные будут сохранены при следующем вызове из Database
            pass


class Database:
    """Основной класс базы данных."""

    def __init__(self, metadata_storage: Any = None, data_storage: Any = None):
        """
        Инициализация базы данных.

        Args:
            metadata_storage: Хранилище метаданных (по умолчанию JsonMetadataStorage)
            data_storage: Хранилище данных таблиц (по умолчанию CachedJsonTableStorage)
        """
        self.metadata_storage = metadata_storage or JsonMetadataStorage()
        self.data_storage = data_storage or CachedJsonTableStorage()
        self.tables: Dict[str, Table] = {}
        self._load_metadata()
                # Устанавливаем хранилища данных для загруженных таблиц
        for table_name, table in self.tables.items():
            if self.data_storage:
                table.set_data_storage(self.data_storage, self)

    def _load_metadata(self) -> None:
        """Загружает метаданные из хранилища."""
        try:
            metadata = self.metadata_storage.load()

            if "tables" in metadata:
                for table_name, table_data in metadata["tables"].items():
                    try:
                        table = Table.from_dict(table_name, table_data)
                        self.tables[table_name] = table
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки таблицы {table_name}: {e}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки метаданных: {e}")

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
        # Устанавливаем хранилище данных и ссылку на базу данных
        if self.data_storage:
            table.set_data_storage(self.data_storage, self)

        # Сохраняем метаданные
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

    def _save_metadata(self) -> bool:
        """
        Сохраняет метаданные в хранилище.
        Returns:
            True если успешно, False если ошибка
        """
        try:
            metadata = {
                "tables": {name: table.to_dict() for name, table in self.tables.items()}
            }
            return self.metadata_storage.save(metadata)
        except Exception as e:
            print(f"❌ Ошибка сохранения метаданных: {e}")
            return False

    def update_table_metadata(self, table_name: str) -> bool:
        """
        Обновляет метаданные таблицы в хранилище.
        
        Args:
            table_name: Имя таблицы для обновления
            
        Returns:
            True если успешно
            
        Raises:
            TableNotFoundError: Если таблица не существует
        """
        if table_name not in self.tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена")
            
        return self._save_metadata()        

    def __repr__(self) -> str:
        tables_count = len(self.tables)
        return f"Database(tables={tables_count})"
class InsertCommand(Command):
    """Команда вставки данных в таблицу."""

    def __init__(self, database: Database, table_name: str, values: List[Any]):
        """
        Инициализация команды вставки.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
            values: Список значений для вставки
        """
        super().__init__(database)
        self.table_name = table_name
        self.values = values

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет вставку данных в таблицу."""
        # Получаем таблицу
        table = self.database.get_table(self.table_name)
        
        # Вставляем данные
        inserted_id = table.insert(self.values)
        
        return CommandResult(
            success=True,
            message=f'Запись с ID={inserted_id} успешно добавлена '
                    f'в таблицу "{self.table_name}".',
            data={
                "table_name": self.table_name,
                "inserted_id": inserted_id,
                "values": self.values,
            },
        )


class SelectCommand(Command):
    """Команда выборки данных из таблицы."""

    def __init__(self, database: Database, table_name: str, 
                 conditions: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Инициализация команды выборки.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
            conditions: Условия выборки
        """
        super().__init__(database)
        self.table_name = table_name
        self.conditions = conditions

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет выборку данных из таблицы."""
        # Получаем таблицу
        table = self.database.get_table(self.table_name)
        
        # Выполняем выборку
        rows = table.select(self.conditions)
        
        # Подготавливаем данные для вывода
        if rows:
            # Преобразуем строки в список словарей
            data = [row.to_dict() for row in rows]
            message = f"Найдено {len(rows)} записей в таблице '{self.table_name}'"
        else:
            data = []
            message = f"В таблице '{self.table_name}' не найдено записей"
            
        return CommandResult(
            success=True,
            message=message,
            data={
                "table_name": self.table_name,
                "rows": data,
                "count": len(rows),
                "conditions": self.conditions,
            },
        )


class UpdateCommand(Command):
    """Команда обновления данных в таблице."""

    def __init__(self, database: Database, table_name: str, 
                 set_clause: Dict[str, Any], 
                 where_clause: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Инициализация команды обновления.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
            set_clause: Данные для обновления
            where_clause: Условия обновления
        """
        super().__init__(database)
        self.table_name = table_name
        self.set_clause = set_clause
        self.where_clause = where_clause

    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет обновление данных в таблице."""
        # Получаем таблицу
        table = self.database.get_table(self.table_name)
        
        # Обновляем данные
        updated_count = table.update(self.set_clause, self.where_clause)
        
        return CommandResult(
            success=True,
            message=f'Обновлено {updated_count} записей в таблице "{self.table_name}".',
            data={
                "table_name": self.table_name,
                "updated_count": updated_count,
                "set_clause": self.set_clause,
                "where_clause": self.where_clause,
            },
        )


class DeleteCommand(Command):
    """Команда удаления данных из таблицы."""

    def __init__(self, database: Database, table_name: str, 
                 where_clause: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Инициализация команды удаления.

        Args:
            database: Экземпляр базы данных
            table_name: Имя таблицы
            where_clause: Условия удаления
        """
        super().__init__(database)
        self.table_name = table_name
        self.where_clause = where_clause

    @confirm_action("удаление данных")
    @handle_db_errors
    @log_time
    def execute(self) -> CommandResult:
        """Выполняет удаление данных из таблицы."""
        # Получаем таблицу
        table = self.database.get_table(self.table_name)
        
        # Удаляем данные
        deleted_count = table.delete(self.where_clause)
        
        return CommandResult(
            success=True,
            message=f'Удалено {deleted_count} записей из таблицы "{self.table_name}".',
            data={
                "table_name": self.table_name,
                "deleted_count": deleted_count,
                "where_clause": self.where_clause,
            },
        )
    
