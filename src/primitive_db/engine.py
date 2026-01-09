"""project-2_avo_m25_555_src_primitive_db_engine.py
Основной движок и цикл обработки команд."""

import shlex

from .constants import (
    COMMAND_CREATE_TABLE,
    COMMAND_DROP_TABLE,
    COMMAND_EXIT,
    COMMAND_HELP,
    COMMAND_LIST_TABLES,
    SUCCESS_TABLE_CREATED,
    SUCCESS_TABLE_DROPPED,
)
from .core import create_table, drop_table, list_tables
from .utils import load_metadata, save_metadata


def print_help() -> None:
    """Выводит справочную информацию о доступных командах.
    Notes:
        Форматирует вывод в соответствии с требованиями ТЗ.
        Включает все команды управления таблицами и общие команды.
    """
    print("\n***Процесс работы с таблицей***")
    print("Функции:")
    print(
        "<command> create_table <имя_таблицы> <столбец1:тип> .. - создать таблицу"
    )
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")
    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def run() -> None:
    """Основной цикл работы базы данных.
    Notes:
        - Обрабатывает ввод пользователя и выполняет соответствующие команды
        - Использует shlex для корректного парсинга аргументов
        - Загружает и сохраняет метаданные при каждой операции
        - Обрабатывает исключения и выводит понятные сообщения об ошибках
    """
    print("Приложение Primitive DB запущено.")
    print("Для справки введите 'help'.")
    print("Для выхода введите 'exit'.")

    # Основной цикл обработки команд
    while True:
        try:
            # Получаем ввод от пользователя
            user_input = input("Введите команду: ").strip()

            # Пропускаем пустой ввод
            if not user_input:
                continue

            # Парсим команду с помощью shlex для корректной обработки аргументов
            args = shlex.split(user_input)
            command = args[0].lower()

            # Обработка команды exit
            if command == COMMAND_EXIT:
                print("Завершение работы. До свидания!")
                break

            # Обработка команды help
            elif command == COMMAND_HELP:
                print_help()

            # Обработка команды list_tables
            elif command == COMMAND_LIST_TABLES:
                # Проверяем корректное количество аргументов
                if len(args) != 1:
                    print("Ошибка: Команда list_tables не принимает аргументов.")
                    continue

                # Загружаем метаданные и получаем список таблиц
                metadata = load_metadata()
                tables = list_tables(metadata)

                # Выводим результат
                if not tables:
                    print("В базе данных нет таблиц.")
                else:
                    for table in tables:
                        print(f"- {table}")

            # Обработка команды create_table
            elif command == COMMAND_CREATE_TABLE:
                # Проверяем минимальное количество аргументов (имя + хотя бы 1 столбец)
                if len(args) < 3:
                    print("Ошибка: Недостаточно аргументов для команды create_table.")
                    print("Формат: create_table <имя_таблицы> <столбец1:тип> ...")
                    continue

                # Извлекаем имя таблицы и список столбцов
                table_name = args[1]
                columns = args[2:]

                # Загружаем текущие метаданные
                metadata = load_metadata()

                try:
                    # Создаем таблицу через бизнес-логику
                    updated_metadata = create_table(metadata, table_name, columns)

                    # Сохраняем обновленные метаданные
                    save_metadata(updated_metadata)

                    # Формируем и выводим сообщение об успехе
                    columns_str = ", ".join(updated_metadata[table_name])
                    print(SUCCESS_TABLE_CREATED.format(table_name, columns_str))

                except ValueError as e:
                    # Выводим сообщение об ошибке от бизнес-логики
                    print(str(e))

            # Обработка команды drop_table
            elif command == COMMAND_DROP_TABLE:
                # Проверяем корректное количество аргументов
                if len(args) != 2:
                    print("Ошибка: Команда drop_table требует ровно один аргумент.")
                    print("Формат: drop_table <имя_таблицы>")
                    continue

                # Извлекаем имя таблицы
                table_name = args[1]

                # Загружаем текущие метаданные
                metadata = load_metadata()

                try:
                    # Удаляем таблицу через бизнес-логику
                    updated_metadata = drop_table(metadata, table_name)

                    # Сохраняем обновленные метаданные
                    save_metadata(updated_metadata)

                    # Выводим сообщение об успехе
                    print(SUCCESS_TABLE_DROPPED.format(table_name))

                except ValueError as e:
                    # Выводим сообщение об ошибке от бизнес-логики
                    print(str(e))

            # Обработка неизвестной команды
            else:
                print(f"Команда '{command}' не распознана. Введите 'help' для справки.")

        # Обработка прерывания по Ctrl+C
        except KeyboardInterrupt:
            print("\nЗавершение работы по запросу пользователя.")
            break

        # Обработка непредвиденных ошибок
        except Exception as e:
            print(f"Произошла непредвиденная ошибка: {e}")
            continue

