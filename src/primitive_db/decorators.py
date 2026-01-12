"""
Модуль декораторов для базы данных.
Содержит декораторы для обработки ошибок, подтверждения действий,
логирования времени и кэширования.
"""

import functools
import json
import time
from typing import Any, Callable, Dict, Optional, Tuple


def handle_db_errors(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок базы данных.

    Перехватывает:
    - FileNotFoundError: файлы данных не найдены
    - KeyError: таблица или столбец не найден
    - ValueError: ошибки валидации данных
    - json.JSONDecodeError: ошибки чтения JSON
    - PermissionError: проблемы с доступом к файлам

    Возвращает None при любой ошибке.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Optional[Any]:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            print(f"❌ Ошибка: Файл не найден - {e}")
            print("   Возможно, база данных не инициализирована.")
        except KeyError as e:
            print(f"❌ Ошибка: Объект не найден - {e}")
            print("   Проверьте имя таблицы или столбца.")
        except PermissionError as e:
            print(f"❌ Ошибка доступа: {e}")
            print("   Проверьте права на запись в директорию данных.")
        except (ValueError, json.JSONDecodeError) as e:
            if isinstance(e, json.JSONDecodeError):
                print(f"❌ Ошибка чтения данных: {e}")
                print("   Файл данных поврежден.")
            else:
                print(f"❌ Ошибка валидации: {e}")
                print("   Проверьте типы и значения данных.")
        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {type(e).__name__}: {e}")
            print("   Пожалуйста, сообщите об этой ошибке разработчику.")
        return None

    return wrapper


def confirm_action(action_name: str) -> Callable:
    """
    Фабрика декораторов для подтверждения действий.

    Args:
        action_name: Название действия для отображения пользователю

    Returns:
        Декоратор, который запрашивает подтверждение перед выполнением функции
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            print(
                f'⚠️  Вы уверены, что хотите выполнить "{action_name}"? [y/N]: ', end=""
            )
            response = input().strip()
            if response.lower() != "y":
                print("🚫 Операция отменена.")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func: Callable) -> Callable:
    """
    Декоратор для логирования времени выполнения функции.

    Измеряет время с помощью time.monotonic() для избежания проблем с
    корректировкой системного времени.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.monotonic()
        result = func(*args, **kwargs)
        end_time = time.monotonic()
        execution_time = end_time - start_time
        if execution_time > 0.01:
            func_name = func.__name__
            print(
                f"⏱️  Функция '{func_name}' выполнилась за "
                f"{execution_time:.3f} секунд"
            )
        return result

    return wrapper


def create_cacher(ttl: int = 300) -> Callable:
    """
    Фабрика для создания кэшера с заданным TTL.

    Args:
        ttl: Время жизни записей в секундах (по умолчанию 300)

    Returns:
        Функция для кэширования результатов
    """
    cache: Dict[str, Tuple[Any, float]] = {}

    def cache_result(key: str, value_func: Callable) -> Any:
        """
        Кэширует результат выполнения функции.

        Args:
            key: Ключ для кэширования
            value_func: Функция для получения значения

        Returns:
            Кэшированное значение или результат выполнения функции
        """
        current_time = time.time()
        if key in cache:
            cached_value, timestamp = cache[key]
            if current_time - timestamp < ttl:
                print(f"📊 Кэш-попадание для ключа: {key}")
                return cached_value
        print(f"📊 Кэш-промах для ключа: {key}")
        value = value_func()
        cache[key] = (value, current_time)
        _clean_expired_cache(cache, ttl, current_time)
        return value

    def _clean_expired_cache(
        cache_dict: Dict[str, Tuple[Any, float]], cache_ttl: int, current_time: float
    ) -> None:
        """Очищает устаревшие записи из кэша."""
        expired_keys = [
            key
            for key, (_, timestamp) in cache_dict.items()
            if current_time - timestamp >= cache_ttl
        ]
        for key in expired_keys:
            del cache_dict[key]
        if expired_keys:
            print(f"🧹 Очищено {len(expired_keys)} устаревших записей кэша")

    def clear_cache() -> None:
        """Очищает весь кэш."""
        cache.clear()
        print("🧹 Весь кэш очищен")

    class CacheWrapper:
        """Обертка для кэшера с дополнительными методами."""

        def __init__(
            self,
            cache_func: Callable,
            clear_func: Callable,
            cache_dict: Dict,
            cache_ttl: int,
        ):
            self.cache_func = cache_func
            self.clear_func = clear_func
            self.cache_dict = cache_dict
            self.cache_ttl = cache_ttl

        def __call__(self, key: str, value_func: Callable) -> Any:
            return self.cache_func(key, value_func)

        def clear(self) -> None:
            self.clear_func()

        def get_cache_size(self) -> int:
            return len(self.cache_dict)

        def get_ttl(self) -> int:
            return self.cache_ttl

    return CacheWrapper(cache_result, clear_cache, cache, ttl)
