"""
Константы для базы данных.
"""
from pathlib import Path

# Поддерживаемые типы данных
SUPPORTED_TYPES = {"int": int, "str": str, "bool": bool}

# Имена и типы столбцов по умолчанию
DEFAULT_ID_COLUMN_NAME = "ID"
DEFAULT_ID_COLUMN_TYPE = "int"

# Пути к файлам
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
META_FILE = DATA_DIR / "db_meta.json"

# Сообщения об ошибках
ERROR_TABLE_EXISTS = "Таблица '{}' уже существует."
ERROR_TABLE_NOT_FOUND = "Таблица '{}' не найдена."
ERROR_INVALID_TYPE = "Неподдерживаемый тип: {}. Допустимые типы: {}"
ERROR_COLUMN_COUNT = "Ожидалось {} значений, получено {}."
ERROR_TYPE_CONVERSION = "Ошибка преобразования '{}' в тип {} для столбца '{}': {}"

# Сообщения об успехе
SUCCESS_TABLE_CREATED = 'Таблица "{}" успешно создана со столбцами: {}'
SUCCESS_TABLE_DROPPED = 'Таблица "{}" успешно удалена.'
SUCCESS_ROW_INSERTED = 'Запись с ID={} успешно добавлена в таблицу "{}".'

# Форматы вывода
TIME_FORMAT = "{:.3f}"
ID_FORMAT = "ID:{}"

