import json
import os

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Updater,
)

from src import message_handler
from src.commands.abstract_command_category import CommandCategory
from src.commands.admin_commands import AdminCommands
from src.commands.audio_commands import AudioCommands
from src.callback_proxy import CallbackProxy
from src.commands.extra_commands import ExtraCommands
from src.commands.main_commands import MainCommands
from src.commands.server.server_commands import ServerCommands

data_file_path = 'src/data/data.json'


def check_data_file() -> None:
    """Check if data.json exists, if not, create it."""
    if os.path.exists(data_file_path):
        return

    with open(data_file_path, 'w') as f:
        data_structure = {
            "server_whitelist": {},
            "general_whitelist": {},
            "admin_chat_id": os.environ['ADMIN_CHAT_ID'],
            "telegram_bot_token": os.environ['TELEGRAM_TOKEN'],
            "hetzner_api_token": os.environ['HETZNER_TOKEN'],
            "restic_backup_dir": os.environ['RESTIC_BACKUP_DIR'],
            "restic_pwd_file": os.environ['RESTIC_PWD_FILE'],
            "standard_ip": "",
            "running_test_bot": False
        }
        json.dump(data_structure, f)


if __name__ == '__main__':
    check_data_file()

    # Start Telegram bot
    with open(data_file_path, 'r') as f:
        data = json.load(f)
    bot_token = data['telegram_bot_token']
    updater = Updater(bot_token)

    # Get all commands from the command classes
    command_objects: list[CommandCategory] = [
        MainCommands(),
        AudioCommands(),
        ExtraCommands(),
        ServerCommands(),
        AdminCommands(),
    ]

    category_help_commands: list[str] = []
    command_data = {}
    for command_object in command_objects:
        # Get regular commands
        commands_data = command_object.get_command_information()
        for command in commands_data['commands']:
            command_data[command['command']] = command['function']

        # Get help commands
        help_command = commands_data['help']
        category_help_commands.append(help_command['command'])
        command_data[help_command['command']] = help_command['function']

    # Add the global "help" command
    # noinspection PyUnusedLocal, PyArgumentList
    def command_help_main(update: Update, context: CallbackContext) -> None:
        help_infos = [f'/{help_categorie}' for help_categorie in category_help_commands]
        help_info = '\n'.join(help_infos)
        msg = f'<b>Command Categories</b>:\n{help_info}'

        update.message.reply_text(text=msg, parse_mode='HTML')


    command_data['help'] = command_help_main

    # Add the commands to the Telegram CommandHandler
    for command in command_data:
        updater.dispatcher.add_handler(CommandHandler(command, command_data[command]))

    # Add Message-Handler

    # The message handler is triggered if certain specified messages are used in the chat
    # message_handler = MessageHandler(Filters.all, message_handler.message_handler)

    updater.dispatcher.add_handler(message_handler)

    # Add callback proxy to handle all callbacks
    updater.dispatcher.add_handler(CallbackQueryHandler(CallbackProxy.handle_callback))

    updater.start_polling()
    updater.idle()
