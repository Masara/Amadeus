import json
from typing import Any

# noinspection PyPackageRequirements
import requests
# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src.commands.abstract_command_category import CommandCategory

data_file_path = 'src/data/data.json'


class AudioCommands(CommandCategory):
    category_name = "Audio Commands"

    def __init__(self) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        self.bot_token = json_data['telegram_bot_token']

    def get_command_information(self) -> dict[str, Any]:
        """Layout for the commands:
        {
            'command': 'command_name',
            'function': self.command_audio,
            'description': 'Help description'
        }

        :return:
        """

        return {
            'help': {
                'command': 'helpAudio',
                'function': self.command_help,
            },
            'commands': []
        }

    # noinspection PyUnusedLocal
    def command_audio(self, update: Update, context: CallbackContext) -> None:
        command = update.effective_message.text.replace('/', '')
        filename = f'{command}.opus'
        self._send_audio(
            chat_id=update.effective_chat.id,
            filename=filename,
            file_dir=f'src/audio/{filename}',
            caption=''
        )

    def _send_audio(self, chat_id: str, filename: str, file_dir: str, caption: str = '') -> None:
        """Sends an audio file via POST, since the usual API code does not work."""
        with open(file_dir, 'rb') as f:
            ara_data = f.read()

        file = {'audio': (filename, ara_data)}

        upload_audio_url = f'https://api.telegram.org/bot{self.bot_token}/sendAudio'
        params = {
            'caption': caption,
            'chat_id': chat_id
        }

        requests.post(upload_audio_url, files=file, params=params)
