from abc import ABC, abstractmethod
from typing import Any

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext


class CommandCategory(ABC):
    @property
    @abstractmethod
    def category_name(self) -> str: ...

    @abstractmethod
    def get_command_information(self) -> dict[str, Any]: ...

    def command_help(self, update: Update, context: CallbackContext) -> None:
        command_info = self.get_command_information()

        command_infos = [
            f'/{command["command"]} {command["description"]}'
            for command in command_info['commands']
        ]

        command_info = '\n'.join(command_infos)
        msg = f'<b>{self.category_name}</b>:\n{command_info}'

        update.message.reply_text(
            text=msg,
            parse_mode='HTML'
        )
