"""
Модуль парсера команд для базы данных.
"""

import shlex
from typing import Any, Callable, Dict, List, Optional

from .constants import (  # Импортируем константы
    CREATE_TABLE_EXAMPLE,
    DELETE_EXAMPLE,
    INSERT_EXAMPLE,
    SELECT_EXAMPLE,
    UPDATE_EXAMPLE,
)
from .core import (
    Command,
    ConditionParser,  # Импортируем из core.py
    CreateTableCommand,
    Database,
    DeleteCommand,  # Импортируем из core.py
    DropTableCommand,
    ExitCommand,  # Импортируем из core.py
    HelpCommand,  # Импортируем из core.py
    InfoTableCommand,
    InsertCommand,  # Импортируем из core.py
    ListTablesCommand,
    ParseError,
    SelectCommand,  # Импортируем из core.py
    UpdateCommand,  # Импортируем из core.py
    ValueParser,  # Импортируем из core.py
)


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

    def _parse_insert(self, args: List[str]) -> InsertCommand:
        """Парсит команду INSERT INTO."""
        if len(args) < 4 or args[0].lower() != "into" or args[2].lower() != "values":
            raise ParseError(
                "Синтаксис: insert into <таблица> values (<значение1>, ...)\n"
                f"Пример: {INSERT_EXAMPLE}"
            )

        table_name = args[1]
        values_str = " ".join(args[3:])

        # Удаляем скобки если есть
        if values_str.startswith("(") and values_str.endswith(")"):
            values_str = values_str[1:-1]

        # Парсим значения с помощью ValueParser
        values = []
        for val in values_str.split(","):
            val = val.strip()
            if val:
                values.append(ValueParser.parse(val))

        return InsertCommand(self.database, table_name, values)

    def _parse_select(self, args: List[str]) -> SelectCommand:
        """Парсит команду SELECT FROM."""
        if len(args) < 2 or args[0].lower() != "from":
            raise ParseError(
                "Синтаксис: select from <таблица> [where <условие>]\n"
                f"Пример: {SELECT_EXAMPLE}"
            )

        table_name = args[1]
        conditions = None

        # Проверяем наличие условия WHERE
        if len(args) > 3 and args[2].lower() == "where":
            condition_str = " ".join(args[3:])
            conditions = ConditionParser.parse(condition_str)

        return SelectCommand(self.database, table_name, conditions)

    def _parse_update(self, args: List[str]) -> UpdateCommand:
        """Парсит команду UPDATE."""
        # Минимальная проверка синтаксиса
        if len(args) < 6:
            raise ParseError(
                "Синтаксис: update <таблица> set <столбец>=<значение> "
                "where <условие>\n"
                f"Пример: {UPDATE_EXAMPLE}"
            )

        # Находим индексы ключевых слов
        args_lower = [arg.lower() for arg in args]

        try:
            set_idx = args_lower.index("set")
        except ValueError:
            raise ParseError("Отсутствует SET в команде UPDATE")

        try:
            where_idx = args_lower.index("where")
        except ValueError:
            raise ParseError("Отсутствует WHERE в команде UPDATE")

        if not (0 < set_idx < where_idx < len(args)):
            raise ParseError("Неправильный порядок в команде UPDATE")

        table_name = args[0]

        # Парсим SET часть (между SET и WHERE)
        set_parts = args[set_idx + 1 : where_idx]
        set_clause = self._parse_set_clause(set_parts)

        # Парсим WHERE часть (после WHERE)
        where_parts = args[where_idx + 1 :]
        where_condition = self._parse_where_condition(" ".join(where_parts))

        return UpdateCommand(self.database, table_name, set_clause, where_condition)

    def _parse_set_clause(self, parts: List[str]) -> Dict[str, Any]:
        """Парсит часть SET команды UPDATE."""
        set_clause = {}

        # Объединяем все части в строку
        set_str = " ".join(parts)

        # Разбиваем по запятым если есть несколько присваиваний
        assignments = [a.strip() for a in set_str.split(",") if a.strip()]

        for assignment in assignments:
            if "=" in assignment:
                col_name, value_str = assignment.split("=", 1)
                col_name = col_name.strip()
                value_str = value_str.strip()

                # Парсим значение
                value = ValueParser.parse(value_str)
                set_clause[col_name] = value
            else:
                raise ParseError(f"Некорректное присваивание в SET: {assignment}")

        return set_clause

    def _parse_where_condition(self, condition_str: str) -> Dict[str, Dict[str, Any]]:
        """Парсит условие WHERE."""
        return ConditionParser.parse(condition_str)

    def _parse_delete(self, args: List[str]) -> DeleteCommand:
        """Парсит команду DELETE FROM."""
        if len(args) < 3 or args[0].lower() != "from":
            raise ParseError(
                "Синтаксис: delete from <таблица> [where <условие>]\n"
                f"Пример: {DELETE_EXAMPLE}"
            )

        table_name = args[1]
        conditions = None

        # Проверяем наличие условия WHERE
        if len(args) > 3 and args[2].lower() == "where":
            condition_str = " ".join(args[3:])
            conditions = ConditionParser.parse(condition_str)

        return DeleteCommand(self.database, table_name, conditions)

    def _parse_help(self, args: List[str]) -> HelpCommand:
        """Парсит команду HELP."""

        # Создаем функцию для вывода справки
        def print_help():
            from .constants import (
                CREATE_TABLE_SYNTAX,
                DELETE_SYNTAX,
                DROP_TABLE_SYNTAX,
                EXIT_SYNTAX,
                HELP_SYNTAX,
                INFO_SYNTAX,
                INSERT_SYNTAX,
                LIST_TABLES_SYNTAX,
                SELECT_SYNTAX,
                UPDATE_SYNTAX,
            )

            print("\n" + "=" * 50)
            print("📘 СПРАВКА ПО КОМАНДАМ БАЗЫ ДАННЫХ")
            print("=" * 50)

            print("\n📁 УПРАВЛЕНИЕ ТАБЛИЦАМИ:")
            print(f"  {CREATE_TABLE_SYNTAX}")
            print(f"    Пример: {CREATE_TABLE_EXAMPLE}")
            print(f"  {DROP_TABLE_SYNTAX}")
            print(f"  {LIST_TABLES_SYNTAX}")
            print(f"  {INFO_SYNTAX}")

            print("\n📝 ОПЕРАЦИИ С ДАННЫМИ:")
            print(f"  {INSERT_SYNTAX}")
            print(f"    Пример: {INSERT_EXAMPLE}")
            print(f"  {SELECT_SYNTAX}")
            print(f"    Пример: {SELECT_EXAMPLE}")
            print(f"  {UPDATE_SYNTAX}")
            print(f"    Пример: {UPDATE_EXAMPLE}")
            print(f"  {DELETE_SYNTAX}")
            print(f"    Пример: {DELETE_EXAMPLE}")

            print("\n⚙️  ОБЩИЕ КОМАНДЫ:")
            print(f"  {HELP_SYNTAX}")
            print(f"  {EXIT_SYNTAX}")
            print("\n" + "=" * 50)

        return HelpCommand(self.database, print_help)

    def _parse_exit(self, args: List[str]) -> ExitCommand:
        """Парсит команду EXIT."""
        return ExitCommand(self.database)
