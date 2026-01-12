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
TABLES_DIR = DATA_DIR / "tables"
META_FILE = DATA_DIR / "db_meta.json"

# Настройки хранилищ
DEFAULT_CACHE_TTL = 300  # 5 минут
DEFAULT_META_PATH = "db_meta.json"
DEFAULT_TABLES_DIR = "data/tables"

# Сообщения хранилищ
ERROR_STORAGE_SAVE = "Ошибка сохранения данных: {}"
ERROR_STORAGE_LOAD = "Ошибка загрузки данных: {}"
WARNING_JSON_ERROR = "Предупреждение: Ошибка чтения JSON {}: {}"
INFO_CACHE_HIT = "📊 Кэш-попадание для ключа: {}"
INFO_CACHE_MISS = "📊 Кэш-промах для ключа: {}"

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

# Синтаксис команд
CREATE_TABLE_SYNTAX = "create_table <table> <col:type> ..."
DROP_TABLE_SYNTAX = "drop_table <table>"
LIST_TABLES_SYNTAX = "list_tables"
INSERT_SYNTAX = "insert into <table> values (<val1>, <val2>, ...)"
SELECT_SYNTAX = "select from <table> [where <condition>]"
UPDATE_SYNTAX = "update <table> set <col>=<val> where <condition>"
DELETE_SYNTAX = "delete from <table> where <condition>"
INFO_SYNTAX = "info <table>"
HELP_SYNTAX = "help"
EXIT_SYNTAX = "exit"

# Примеры команд
CREATE_TABLE_EXAMPLE = "create_table users name:str age:int is_active:bool"
INSERT_EXAMPLE = 'insert into users values ("John", 25, true)'
SELECT_EXAMPLE = "select from users where age = 28"
UPDATE_EXAMPLE = 'update users set age = 29 where name = "Sergei"'
DELETE_EXAMPLE = "delete from users where ID = 1"

# Операторы условий
WHERE_OPERATORS = ["=", "!=", "<", ">", "<=", ">="]

# Сообщения парсера
ERROR_UNKNOWN_COMMAND = "Неизвестная команда: '{}'. Введите 'help' для справки."
ERROR_INVALID_SYNTAX = "Неправильный синтаксис. Ожидалось: {}"
ERROR_WRONG_ARG_COUNT = "Команда '{}' требует {} аргументов, получено {}."
ERROR_VALUE_CONVERSION = "Невозможно преобразовать '{}' в тип {}"
ERROR_CONDITION_SYNTAX = "Некорректный синтаксис условия: '{}'"
