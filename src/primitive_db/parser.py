"""
Модуль парсера команд для базы данных.
"""

import shlex
from typing import Any, Callable, Dict, List, Optional

from .core import (
    Command,
    CreateTableCommand,
    Database,
    DropTableCommand,
    InfoTableCommand,
    ListTablesCommand,
    ParseError,
)


class ValueParser:
    """Парсер значений для преобразования строк в типы данных."""

    @staticmethod
    def parse(value_str: str) -> Any:
        """
        Преобразует строковое значение в соответствующий тип данных.

        Args:
            value_str: Строковое значение для парсинга

        Returns:
            Значение соответствующего типа (int, str, bool)

        Raises:
            ParseError: Если значение не может быть преобразовано
        """
        value_str = value_str.strip()

        # Булевые значения
        if value_str.lower() in ("true", "false"):
            return value_str.lower() == "true"

        # Целочисленные значения
        if value_str.isdigit() or (value_str[0] == "-" and value_str[1:].isdigit()):
            return int(value_str)

        # Строковые значения (убираем кавычки если есть)
        if (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]

        # Если не удалось определить тип, возвращаем как строку
        return value_str


class ConditionParser:
    """Парсер условий WHERE для команд SELECT, UPDATE, DELETE."""

    @staticmethod
    def parse(condition_str: str) -> Dict[str, Any]:
        """
        Парсит условие вида "столбец = значение".

        Args:
            condition_str: Строка условия

        Returns:
            Словарь с ключом-столбцом и значением

        Raises:
            ParseError: Если синтаксис условия некорректный
        """
        condition_str = condition_str.strip()

        # Поддерживаемые операторы
        operators = ["=", "!=", "<", ">", "<=", ">="]

        for op in operators:
            if op in condition_str:
                parts = condition_str.split(op, 1)
                if len(parts) == 2:
                    column = parts[0].strip()
                    value_str = parts[1].strip()
                    value = ValueParser.parse(value_str)
                    return {column: {"operator": op, "value": value}}

        raise ParseError(
            f"Некорректный синтаксис условия: '{condition_str}'. "
            f"Поддерживаемые операторы: {', '.join(operators)}"
        )

    @staticmethod
    def parse_multiple(conditions_str: str) -> List[Dict[str, Any]]:
        """
        Парсит несколько условий, разделенных AND.

        Args:
            conditions_str: Строка с несколькими условиями

        Returns:
            Список словарей с условиями
        """
        conditions = []
        # Простая реализация - разбиваем по AND (без учета вложенных условий)
        for cond in conditions_str.split("and"):
            cond = cond.strip()
            if cond:
                conditions.append(ConditionParser.parse(cond))
        return conditions


class CommandParser:
    """Основной парсер текстовых команд в объекты Command."""

    def __init__(self, database: Database):
        """
        Инициализация парсера команд.

        Args:
            database: Экземпляр базы данных
        """
        self.database = database
        self.command_patterns = self._build_command_patterns()

    def _build_command_patterns(self) -> Dict[str, Callable]:
        """Создает словарь методов парсинга для каждой команды."""
        return {
            "create_table": self._parse_create_table,
            "drop_table": self._parse_drop_table,
            "list_tables": self._parse_list_tables,
            "insert": self._parse_insert,
            "select": self._parse_select,
            "update": self._parse_update,
            "delete": self._parse_delete,
            "info": self._parse_info,
            "help": self._parse_help,
            "exit": self._parse_exit,
        }

    def parse(self, input_string: str) -> Optional[Command]:
        """
        Преобразует строку ввода в объект Command.

        Args:
            input_string: Входная строка команды

        Returns:
            Объект Command или None если команда пустая

        Raises:
            ParseError: При ошибке парсинга команды
        """
        if not input_string.strip():
            return None

        # Разбиваем на токены с сохранением кавычек
        try:
            tokens = shlex.split(input_string, posix=True)
        except ValueError as e:
            raise ParseError(f"Ошибка разбора строки: {e}")

        if not tokens:
            return None

        command_name = tokens[0].lower()
        args = tokens[1:] if len(tokens) > 1 else []

        # Находим подходящий парсер
        for cmd_key, parser_func in self.command_patterns.items():
            if command_name == cmd_key:
                return parser_func(args)

        # Проверяем составные команды
        if len(tokens) >= 2:
            compound_cmd = f"{tokens[0]} {tokens[1]}".lower()
            if compound_cmd == "insert into":
                return self._parse_insert(tokens[2:])
            elif compound_cmd == "select from":
                return self._parse_select(tokens[2:])
            elif compound_cmd == "delete from":
                return self._parse_delete(tokens[2:])

        raise ParseError(
            f"Неизвестная команда: '{command_name}'. Введите 'help' для справки."
        )

    def _parse_create_table(self, args: List[str]) -> CreateTableCommand:
        """Парсит команду CREATE TABLE."""
        if len(args) < 2:
            raise ParseError(
                "Синтаксис: create_table <имя_таблицы> <столбец1:тип> "
                "<столбец2:тип> ...\nПример: create_table users name:str "
                "age:int is_active:bool"
            )

        table_name = args[0]
        columns_def = args[1:]

        return CreateTableCommand(self.database, table_name, columns_def)

    def _parse_drop_table(self, args: List[str]) -> DropTableCommand:
        """Парсит команду DROP TABLE."""
        if len(args) != 1:
            raise ParseError(
                "Синтаксис: drop_table <имя_таблицы>\nПример: drop_table users"
            )

        return DropTableCommand(self.database, args[0])

    def _parse_list_tables(self, args: List[str]) -> ListTablesCommand:
        """Парсит команду LIST_TABLES."""
        if args:
            raise ParseError("Синтаксис: list_tables (без аргументов)")

        return ListTablesCommand(self.database)

    def _parse_info(self, args: List[str]) -> InfoTableCommand:
        """Парсит команду INFO."""
        if len(args) != 1:
            raise ParseError("Синтаксис: info <имя_таблицы>\nПример: info users")

        return InfoTableCommand(self.database, args[0])

    def _parse_insert(self, args: List[str]) -> "InsertCommand":
        """Парсит команду INSERT INTO."""
        # Временная заглушка - будет реализована в задаче 1.5
        raise ParseError(
            "Команда INSERT еще не реализована. Будет доступна в задаче 1.5"
        )

    def _parse_select(self, args: List[str]) -> "SelectCommand":
        """Парсит команду SELECT FROM."""
        # Временная заглушка - будет реализована в задаче 1.5
        raise ParseError(
            "Команда SELECT еще не реализована. Будет доступна в задаче 1.5"
        )

    def _parse_update(self, args: List[str]) -> "UpdateCommand":
        """Парсит команду UPDATE."""
        # Временная заглушка - будет реализована в задаче 1.5
        raise ParseError(
            "Команда UPDATE еще не реализована. Будет доступна в задаче 1.5"
        )

    def _parse_delete(self, args: List[str]) -> "DeleteCommand":
        """Парсит команду DELETE FROM."""
        # Временная заглушка - будет реализована в задаче 1.5
        raise ParseError(
            "Команда DELETE еще не реализована. Будет доступна в задаче 1.5"
        )

    # def _parse_help(self, args: List[str]) -> 'HelpCommand':
    #     """Парсит команду HELP."""
    #     # Временная заглушка - будет реализована в задаче 1.5
    #     from .engine import print_help
    #     return HelpCommand(self.database, print_help)

    def _parse_help(self, args: List[str]) -> "HelpCommand":
        """Парсит команду HELP."""

        # Временная заглушка - будет реализована в задаче 1.5
        # Создаем временную функцию для вывода справки
        def print_help_temporary():
            print("\n***Процесс работы с таблицей***")
            print("Функции:")
            print(
                "<command> create_table <имя_таблицы> <столбец1:тип> .. - "
                "создать таблицу"
            )
            print("<command> list_tables - показать список всех таблиц")
            print("<command> drop_table <имя_таблицы> - удалить таблицу")
            print("\nОбщие команды:")
            print("<command> exit - выход из программы")
            print("<command> help - справочная информация\n")

        return HelpCommand(self.database, print_help_temporary)

    def _parse_exit(self, args: List[str]) -> "ExitCommand":
        """Парсит команду EXIT."""
        # Временная заглушка - будет реализована в задаче 1.5
        return ExitCommand(self.database)


# Временные классы-заглушки для команд, которые будут реализованы позже
class InsertCommand(Command):
    """Команда INSERT INTO (заглушка)."""

    pass


class SelectCommand(Command):
    """Команда SELECT FROM (заглушка)."""

    pass


class UpdateCommand(Command):
    """Команда UPDATE (заглушка)."""

    pass


class DeleteCommand(Command):
    """Команда DELETE FROM (заглушка)."""

    pass


class HelpCommand(Command):
    """Команда HELP (заглушка)."""

    def __init__(self, database: Database, help_func: Callable):
        super().__init__(database)
        self.help_func = help_func

    def execute(self):
        self.help_func()
        from .core import CommandResult

        return CommandResult(success=True, message="Справка показана")


class ExitCommand(Command):
    """Команда EXIT (заглушка)."""

    def execute(self):
        from .core import CommandResult

        return CommandResult(success=True, message="Выход из программы")
