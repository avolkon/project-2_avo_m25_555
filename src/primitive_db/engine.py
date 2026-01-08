"""project-2_avo_m25_555_src_primitive_db_engine.py
Основной движок и цикл обработки команд."""

from .constants import COMMAND_EXIT, COMMAND_HELP


def run() -> None:
    """Основной цикл работы базы данных."""
    print("Приложение Primitive DB запущено.")
    print("Для справки введите 'help'.")
    print("Для выхода введите 'exit'.")

    while True:
        try:
            user_input = input("Введите команду: ").strip()

            if not user_input:
                continue

            command = user_input.lower()

            if command == COMMAND_EXIT:
                print("Завершение работы. До свидания!")
                break
            elif command == COMMAND_HELP:
                print("Доступные команды: help, exit")
            else:
                print(f"Команда '{command}' не распознана. Введите 'help' для справки.")

        except KeyboardInterrupt:
            print("\nЗавершение работы по запросу пользователя.")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            continue
