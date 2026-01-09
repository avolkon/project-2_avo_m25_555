"""utils.py - Вспомогательные функции для работы с файлами."""

import json
import os
from typing import Any, Dict

from .constants import DATA_DIR, META_FILE, TABLES_DIR


def ensure_data_dirs() -> None:
    """Создает необходимые директории для хранения данных, если они не существуют.
    Returns:
        None: Функция создает директории или подтверждает их существование
    """
    try:
        # Создаем основную директорию данных с опцией exist_ok=True
        os.makedirs(DATA_DIR, exist_ok=True)
        # Создаем директорию для таблиц внутри data/
        os.makedirs(TABLES_DIR, exist_ok=True)
    except PermissionError as e:
        # Повторно вызываем исключение с понятным сообщением
        raise PermissionError(f"Нет прав на создание директории {DATA_DIR}: {e}") from e


def load_metadata(filepath: str = META_FILE) -> Dict[str, Any]:
    """Загружает метаданные базы данных из JSON-файла.
    Args:
        filepath: Путь к файлу метаданных, по умолчанию META_FILE
    Returns:
        Dict[str, Any]: Словарь с метаданными или пустой словарь при ошибке
    Notes:
        - Если файл не существует, возвращает пустой словарь
        - Если файл содержит некорректный JSON, возвращает пустой словарь
        - Автоматически создает необходимые директории перед загрузкой
    """
    # Гарантируем существование директорий перед работой с файлами
    ensure_data_dirs()

    try:
        # Открываем файл с явным указанием кодировки UTF-8
        with open(filepath, "r", encoding="utf-8") as f:
            # Загружаем JSON данные из файла
            return json.load(f)
    except FileNotFoundError:
        # Файл не существует - это нормально для первого запуска
        return {}
    except json.JSONDecodeError:
        # Файл поврежден или содержит некорректный JSON
        return {}


def save_metadata(data: Dict[str, Any], filepath: str = META_FILE) -> None:
    """Сохраняет метаданные базы данных в JSON-файл с атомарной записью.
    Args:
        data: Словарь с метаданными для сохранения
        filepath: Путь к файлу метаданных, по умолчанию META_FIL
    Raises:
        PermissionError: Если нет прав на запись в файл или директорию
        TypeError: Если данные не могут быть сериализованы в JSO
    Notes:
        - Использует атомарную запись через временный файл
        - Автоматически создает необходимые директории
        - Обеспечивает целостность данных при сбоях
    """
    # Гарантируем существование директорий перед сохранением
    ensure_data_dirs()

    # Имя временного файла для атомарной записи
    temp_file = filepath + ".tmp"

    try:
        # Записываем данные во временный файл
        with open(temp_file, "w", encoding="utf-8") as f:
            # Сериализуем данные в JSON с отступами и поддержкой Unicode
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Атомарная замена старого файла новым
        if os.path.exists(filepath):
            # Если файл существует, заменяем его атомарно
            os.replace(temp_file, filepath)
        else:
            # Если файла нет, просто переименовываем временный файл
            os.rename(temp_file, filepath)

    except (PermissionError, TypeError) as e:
        # Очищаем временный файл при ошибке записи
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                # Игнорируем ошибки удаления временного файла
                pass

        # Повторно вызываем исключение для обработки на верхнем уровне
        raise e
    except Exception as e:
        # Обработка любых других непредвиденных ошибок
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        raise e
