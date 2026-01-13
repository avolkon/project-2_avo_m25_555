#!/usr/bin/env python3
"""Движок базы данных для интерактивного взаимодействия с пользователем."""

import sys
from typing import Any, Dict, List, Optional

from .constants import (
    CREATE_TABLE_EXAMPLE,
    DELETE_EXAMPLE,
    INSERT_EXAMPLE,
    SELECT_EXAMPLE,
    UPDATE_EXAMPLE,
)

# Импортируем внутренние модули проекта
from .core import CommandResult, Database
from .parser import CommandParser, ParseError


class SimpleTable:
    """Простая реализация таблицы для отображения данных."""

    def __init__(self) -> None:
        """Инициализирует пустую таблицу."""
        self.field_names: List[str] = []
        self.rows: List[List[Any]] = []
        self.align = "l"

    def add_row(self, row: List[Any]) -> None:
        """Добавляет строку в таблицу."""
        self.rows.append(row)

    def __str__(self) -> str:
        """Возвращает строковое представление таблицы."""
        if not self.field_names:
            return "Пустая таблица"

        # Вычисляем ширину столбцов
        col_widths = []
        for i, header in enumerate(self.field_names):
            max_width = len(str(header))
            for row in self.rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            # Добавляем отступы
            col_widths.append(max_width + 2)

        # Строим таблицу
        result_lines = []

        # Верхняя граница
        top_border = "+"
        for width in col_widths:
            top_border += "-" * width + "+"
        result_lines.append(top_border)

        # Заголовки
        header_row = "|"
        for i, header in enumerate(self.field_names):
            if self.align == "l":
                header_row += f" {str(header):<{col_widths[i]-1}}|"
            else:
                header_row += f" {str(header):^{col_widths[i]-1}}|"
        result_lines.append(header_row)

        # Разделитель
        sep_border = "+"
        for width in col_widths:
            sep_border += "-" * width + "+"
        result_lines.append(sep_border)

        # Данные
        for row in self.rows:
            data_row = "|"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    if self.align == "l":
                        data_row += f" {str(cell):<{col_widths[i]-1}}|"
                    else:
                        data_row += f" {str(cell):^{col_widths[i]-1}}|"
            result_lines.append(data_row)

        # Нижняя граница
        bottom_border = "+"
        for width in col_widths:
            bottom_border += "-" * width + "+"
        result_lines.append(bottom_border)

        return "\n".join(result_lines)


class DatabaseEngine:
    """Основной движок для работы с базой данных через командную строку."""

    def __init__(self) -> None:
        """
        Инициализирует движок базы данных.

        Создает экземпляр базы данных и парсера команд для обработки
        пользовательского ввода.
        """
        self.database = Database()  # Основная база данных
        self.parser = CommandParser(self.database)  # Парсер команд
        self.running = True  # Флаг работы программы
        self.prompt = ">>> Введите команду: "  # Приглашение для ввода

        # Инициализируем форматтер таблиц
        self._init_table_formatter()

    def _init_table_formatter(self) -> None:
        """Инициализирует форматтер таблиц (пробует использовать PrettyTable)."""
        try:
            # Пробуем импортировать PrettyTable
            from prettytable import PrettyTable

            self.table_formatter = PrettyTable
            print("📊 PrettyTable загружен для красивого вывода таблиц")
        except ImportError:
            # Используем нашу простую реализацию
            self.table_formatter = SimpleTable
            print("⚠️  PrettyTable не установлен, используется простой форматтер")
            print("   Для красивого вывода установите: poetry add prettytable")

    def run(self) -> None:
        """
        Запускает основной цикл работы базы данных.

        Выводит приветственное сообщение и обрабатывает команды пользователя
        до получения команды выхода или прерывания.
        """
        self._print_welcome()

        # Основной цикл обработки команд
        while self.running:
            try:
                user_input = self._get_user_input()
                if not user_input:
                    continue

                self._process_user_command(user_input)

            except KeyboardInterrupt:
                # Обработка Ctrl+C
                print("\n🛑 Работа прервана пользователем")
                self.running = False
            except EOFError:
                # Обработка Ctrl+D (конец файла)
                print("\n👋 До свидания!")
                self.running = False
            except Exception as e:
                # Обработка непредвиденных ошибок
                error_msg = f"❌ Критическая ошибка: {type(e).__name__}: {e}"
                print(error_msg)

    def _print_welcome(self) -> None:
        """Выводит приветственное сообщение при запуске программы."""
        print("\n" + "=" * 50)
        print("📊 PRIMITIVE DATABASE v0.1.0")
        print("=" * 50)
        print("Система управления простой базой данных")
        print("=" * 50)
        print("Введите 'help' для справки, 'exit' для выхода")
        print("=" * 50 + "\n")

    def _get_user_input(self) -> Optional[str]:
        """
        Получает ввод от пользователя.

        Returns:
            Строка с командой или None если достигнут конец ввода.
        """
        try:
            # Используем библиотеку prompt для удобного ввода
            import prompt

            return prompt.string(self.prompt).strip()
        except ImportError:
            # Fallback на стандартный input если prompt не установлен
            try:
                return input(self.prompt).strip()
            except EOFError:
                return None

    def _process_user_command(self, user_input: str) -> None:
        """
        Обрабатывает команду, введенную пользователем.

        Args:
            user_input: Строка с командой от пользователя
        """
        try:
            # Парсим команду с помощью парсера
            command = self.parser.parse(user_input)

            if not command:
                return  # Пустая команда

            # Выполняем команду и получаем результат
            result = command.execute()

            # Отображаем результат выполнения
            self._display_command_result(result)

            # Проверяем команду выхода
            if user_input.strip().lower() == "exit":
                self.running = False

        except ParseError as e:
            # Ошибка парсинга команды
            print(f"❌ Ошибка синтаксиса: {e}")
            print("   Введите 'help' для справки по командам")
        except Exception as e:
            # Ошибка выполнения команды
            error_type = type(e).__name__
            print(f"❌ Ошибка выполнения: {error_type}: {e}")

    def _display_command_result(self, result: CommandResult) -> None:
        """
        Отображает результат выполнения команды.

        Args:
            result: Результат выполнения команды
        """
        if not result.success:
            # Отображение ошибки
            print(f"❌ {result.message}")
            return

        # Отображение успешного результата
        if result.message:
            print(f"✅ {result.message}")

        # Отображение времени выполнения если оно есть
        if result.execution_time > 0:
            time_str = f"{result.execution_time:.3f}"
            print(f"⏱️  Время выполнения: {time_str} сек")

        # Обработка специальных типов данных
        self._handle_result_data(result.data)

    def _handle_result_data(self, data: Dict[str, Any]) -> None:
        """
        Обрабатывает дополнительные данные из результата команды.

        Args:
            data: Словарь с дополнительными данными
        """
        # Отображение таблиц для команды SELECT
        if "rows" in data and data["rows"]:
            self._display_data_table(data["rows"])

        # Отображение списка таблиц для команды LIST_TABLES
        elif "tables" in data:
            self._display_tables_list(data["tables"])

        # Отображение информации о таблице для команды INFO
        elif "table_name" in data:
            self._display_table_info(data)

    def _display_data_table(self, rows: List[Dict[str, Any]]) -> None:
        """
        Отображает данные в виде таблицы.

        Args:
            rows: Список словарей с данными для отображения
        """
        if not rows:
            print("📭 Нет данных для отображения")
            return

        # Создаем таблицу с помощью выбранного форматтера
        table = self.table_formatter()

        # Получаем заголовки из первого ряда
        headers = list(rows[0].keys())
        table.field_names = headers

        # Добавляем все строки данных
        for row in rows:
            table_row = [row.get(header, "") for header in headers]
            table.add_row(table_row)

        # Настраиваем выравнивание для PrettyTable
        if hasattr(table, "align"):
            table.align = "l"

        # Выводим таблицу
        print("\n" + str(table))

    def _display_tables_list(self, tables: List[str]) -> None:
        """
        Отображает список всех таблиц в базе данных.

        Args:
            tables: Список имен таблиц
        """
        if not tables:
            print("📭 В базе данных нет таблиц")
            return

        print("\n📋 Список таблиц в базе данных:")
        for table_name in tables:
            print(f"  • {table_name}")

        print(f"\nВсего таблиц: {len(tables)}")

    def _display_table_info(self, info_data: Dict[str, Any]) -> None:
        """
        Отображает информацию о конкретной таблице.

        Args:
            info_data: Словарь с информацией о таблице
        """
        table_name = info_data.get("table_name", "Неизвестно")
        print(f"\n📊 Информация о таблице '{table_name}':")

        if "columns" in info_data:
            columns = info_data["columns"]
            if columns:
                columns_str = ", ".join(str(col) for col in columns)
                print(f"  Столбцы: {columns_str}")

        if "record_count" in info_data:
            count = info_data["record_count"]
            print(f"  Количество записей: {count}")

    def show_help(self) -> None:
        """Выводит справочную информацию по всем командам."""
        print("\n" + "=" * 50)
        print("📘 СПРАВКА ПО КОМАНДАМ БАЗЫ ДАННЫХ")
        print("=" * 50)

        print("\n📁 УПРАВЛЕНИЕ ТАБЛИЦАМИ:")
        print("  create_table <таблица> <столбец:тип> <столбец:тип> ...")
        print(f"    Пример: {CREATE_TABLE_EXAMPLE}")
        print("  drop_table <таблица> - удалить таблицу")
        print("  list_tables - показать все таблицы")
        print("  info <таблица> - информация о таблице")

        print("\n📝 ОПЕРАЦИИ С ДАННЫМИ:")
        print("  insert into <таблица> values (<значение1>, <значение2>, ...)")
        print(f"    Пример: {INSERT_EXAMPLE}")
        print("  select from <таблица> - выбрать все записи")
        print("  select from <таблица> where <условие> - выбрать по условию")
        print(f"    Пример: {SELECT_EXAMPLE}")
        print("  update <таблица> set <столбец>=<значение> where <условие>")
        print(f"    Пример: {UPDATE_EXAMPLE}")
        print("  delete from <таблица> where <условие>")
        print(f"    Пример: {DELETE_EXAMPLE}")

        print("\n⚙️  ОБЩИЕ КОМАНДЫ:")
        print("  help - показать эту справку")
        print("  exit - выйти из программы")
        print("\n" + "=" * 50)


def run() -> None:
    """
    Основная функция для запуска движка базы данных.

    Создает экземпляр DatabaseEngine и запускает основной цикл.
    """
    try:
        print("🚀 Запуск Primitive Database...")
        engine = DatabaseEngine()
        engine.run()
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Фатальная ошибка при запуске: {e}")
        sys.exit(1)


# Точка входа при запуске модуля напрямую
if __name__ == "__main__":
    run()
