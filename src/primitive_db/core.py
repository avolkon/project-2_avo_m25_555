"""project-2_avo_m25_555_src_primitive_db_core.py
Основная бизнес-логика управления таблицами базы данных."""

from typing import Dict, List

from .constants import (
    ERROR_INVALID_COLUMN_FORMAT,
    ERROR_INVALID_TYPE,
    ERROR_TABLE_EXISTS,
    ERROR_TABLE_NOT_FOUND,
    ID_COLUMN_DEF,
    VALID_TYPES,
)


def create_table(
    metadata: Dict[str, List[str]], table_name: str, columns: List[str]
) -> Dict[str, List[str]]:
    """Создает новую таблицу в метаданных базы данных.
    Args:
        metadata: Текущие метаданные БД (словарь имя_таблицы -> список_столбцов)
        table_name: Имя создаваемой таблицы (должно быть уникальным)
        columns: Список определений столбцов в формате 'имя:тип'
    Returns:
        Dict[str, List[str]]: Обновленные метаданные с добавленной таблицей
    Raises:
        ValueError: Если таблица уже существует или данные некорректны
    Notes:
        - Автоматически добавляет столбец ID:int в начало списка столбцов
        - Проверяет уникальность имени таблицы
        - Валидирует формат и типы данных столбцов
        - Поддерживаемые типы: int, str, bool
    """
    # Проверяем, не существует ли уже таблица с таким именем
    if table_name in metadata:
        raise ValueError(ERROR_TABLE_EXISTS.format(table_name))

    # Начинаем список столбцов с автоматического ID столбца
    validated_columns: List[str] = [ID_COLUMN_DEF]

    # Валидируем каждый предоставленный столбец
    for column_def in columns:
        # Проверяем формат 'имя:тип'
        if ":" not in column_def:
            raise ValueError(ERROR_INVALID_COLUMN_FORMAT.format(column_def))

        # Разделяем на имя и тип (используем maxsplit=1 для случаев с : в имени)
        col_parts = column_def.split(":", 1)
        if len(col_parts) != 2:
            raise ValueError(ERROR_INVALID_COLUMN_FORMAT.format(column_def))

        col_name, col_type = col_parts

        # Проверяем, что тип данных поддерживается
        if col_type not in VALID_TYPES:
            # Формируем читаемое сообщение с доступными типами
            valid_types_str = ", ".join(sorted(VALID_TYPES))
            raise ValueError(ERROR_INVALID_TYPE.format(col_type, valid_types_str))

        # Добавляем валидированный столбец в список
        validated_columns.append(column_def)

    # Добавляем новую таблицу в метаданные
    metadata[table_name] = validated_columns
    return metadata


def drop_table(metadata: Dict[str, List[str]], table_name: str) -> Dict[str, List[str]]:
    """Удаляет таблицу из метаданных базы данных.
    Args:
        metadata: Текущие метаданные базы данных
        table_name: Имя удаляемой таблицы
    Returns:
        Dict[str, List[str]]: Обновленные метаданные без указанной таблицы
    Raises:
        ValueError: Если таблица не существует в метаданных
    Notes:
        - Удаляет только метаданные таблицы, не затрагивая файлы с данными
        - Проверяет существование таблицы перед удалением
    """
    # Проверяем существование таблицы
    if table_name not in metadata:
        raise ValueError(ERROR_TABLE_NOT_FOUND.format(table_name))

    # Удаляем таблицу из метаданных
    # Создаем копию метаданных для избежания side effects
    updated_metadata = metadata.copy()
    del updated_metadata[table_name]

    return updated_metadata


def list_tables(metadata: Dict[str, List[str]]) -> List[str]:
    """Возвращает список всех таблиц в базе данных.
    Args:
        metadata: Метаданные базы данных (словарь имя_таблицы -> список_столбцов)
    Returns:
        List[str]: Список имен таблиц, отсортированный по алфавиту
    Notes:
        - Возвращает пустой список, если в базе нет таблиц
        - Сортировка обеспечивает предсказуемый порядок вывода
    """
    # Получаем список имен таблиц и сортируем его
    tables = list(metadata.keys())
    tables.sort()
    return tables
