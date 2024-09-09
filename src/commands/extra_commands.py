import math
from typing import Any

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src.commands.abstract_command_category import CommandCategory


class ExtraCommands(CommandCategory):
    category_name = "Extra Commands"

    def get_command_information(self) -> dict[str, Any]:
        return {
            'help': {
                'command': 'helpExtra',
                'function': self.command_help,
            },
            'commands': [{
                'command': 'my_telegram_id',
                'function': self.command_get_telegram_id,
                'description': '- Get your Telegram ID'
            }, {
                'command': 'mw',
                'function': self.command_minimum_probability,
                'description': '{Actual probability} {Probability you want to reach} - Indicates how many attempts it '
                               'takes to be successful. Values in decimal! (16.9% = 0.169)'
            }]
        }

    # noinspection PyUnusedLocal
    @staticmethod
    def command_get_telegram_id(update: Update, context: CallbackContext) -> None:
        update.message.reply_text(f'Deine Telegram UserID: {update.effective_user.id}')

    # noinspection PyUnusedLocal
    @staticmethod
    def command_minimum_probability(update: Update, context: CallbackContext) -> None:
        """Aka. probability mass function."""
        message = update.message.text.replace('/mw ', '')

        if not message or message == '' or update.message.text == '/mw':
            update.message.reply_text('Error: Please enter correct decimal values!')
            return

        parts = message.split(' ')
        parts = [part.replace(',', '.') for part in parts]

        if len(parts) != 2:
            update.message.reply_text('Error: Either too many or not enough arguments!')
            return

        try:
            chances = []
            for part in parts:
                if '/' in part:
                    chance_parts = part.split('/')
                    chance = float(chance_parts[0]) / float(chance_parts[1])
                else:
                    chance = float(part)

                if chance == 1:
                    chance -= 0.000001
                elif chance > 1:
                    update.message.reply_text('Error: Too large number value, please specify numbers smaller than 1!')
                    return

                chances.append(chance)
        except ValueError as _:
            update.message.reply_text('ValueError: Please enter correct decimal values!!')
            return

        attempts = (math.log(1 - chances[1], 2)) / math.log(1 - chances[0], 2)
        update.message.reply_text(f'You would need about {attempts} attempts to succeed with your given probability!')
