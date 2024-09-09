import json
import time
from multiprocessing import Process
from typing import Any

import hcloud
# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.bot import Bot
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src import telegram_utilities
from .server_control import ServerControl
from src.commands.abstract_command_category import CommandCategory

server_name = 'amadeus'
data_file_path = 'src/data/data.json'


def send_server_status_to_admin(bot_token: str) -> None:
    """Sends an automated message (every 2 hours) to the admin if the server is running"""
    with open(data_file_path, "r") as f:
        json_data = json.load(f)

    server_token = json_data['hetzner_api_token']
    admin_chat_id = json_data['admin_chat_id']

    bot = Bot(token=bot_token)
    client = hcloud.Client(token=server_token)

    while True:
        time.sleep(7200)  # 2h
        if client.servers.get_by_name(server_name) is not None:
            bot.send_message(chat_id=admin_chat_id, text='INFO: Der Server läuft aktuell.')


# noinspection PyMethodParameters
def check_permission_and_prepare(func):
    """Decorator: Updated the data.json data int the class and checks if the commanding user has permissions"""

    def wrapper(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)

        # 1) Update our needed data
        self.set_json_data()

        if user_id in self.server_whitelist:
            # 2) Renew server class to update its data
            self.server_control = ServerControl(self.server_api_token, update, context)

            # 3) Run the called function
            # noinspection PyCallingNonCallable
            func(self, update, context)
        else:
            update.message.reply_text('You have no permission to use this command!')

    return wrapper


class ServerCommands(CommandCategory):
    server_api_token = ''
    admin_chat_id = ''
    standard_ip = ''
    server_whitelist = []
    server_control = None
    subprocess_status_update = None
    category_name = "Server Commands"

    def get_command_information(self) -> dict[str, Any]:
        return {
            'help': {
                'command': 'helpServer',
                'function': self.command_help,
            },
            'commands': [{
                'command': 'startServer',
                'function': self.command_start,
                'description': "- Soll ich den Server starten?"
            }, {
                'command': 'stopServer',
                'function': self.command_stop,
                'description': "- Soll ich den Server stoppen?"
            }, {
                'command': 'statusServer',
                'function': self.command_status,
                'description': "- Brauchst du eine Statusmeldung zum Server?"
            }, {
                'command': 'rebootServer',
                'function': self.command_reboot,
                'description': "- Soll ich den laufenden Server rebooten?"
            }, {
                'command': 'updateServerStandardIP',
                'function': self.command_update_standard_ip,
                'description': "- Gespeicherte IP überschreiben"
            }]
        }

    def set_json_data(self) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)

        self.server_api_token = json_data['hetzner_api_token']
        self.admin_chat_id = json_data['admin_chat_id']
        self.standard_ip = json_data['standard_ip']
        self.server_whitelist = json_data['server_whitelist']

    # Todo Singleton
    def __init__(self) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        self.bot_token = json_data['telegram_bot_token']

        self.set_json_data()
        self.server_control = ServerControl(self.server_api_token, None, None)

        if self.subprocess_status_update is None and self.server_control.is_running:
            self._start_subprocess_status_update()

    @property
    def _current_ip(self) -> str:
        if self.server_control.is_running:
            return self.server_control.server.data_model.public_net.ipv4.ip

        # if the server is not running try to get the "standard_ip" value
        return self.standard_ip

    # noinspection PyUnusedLocal, PyArgumentList
    @check_permission_and_prepare
    def command_stop(self, update: Update, context: CallbackContext) -> None:
        if self.server_control.is_running:
            # Stop the game server
            try:
                self.server_control.destroy_amadeus()
            except Exception as e:
                update.message.reply_text(f'Error while stopping the server:\n{e}')

            # Stop the "status update" subprocess
            try:
                telegram_utilities.stop_subprocess(self.subprocess_status_update)
                self.subprocess_status_update = None
            except Exception as e:
                # Todo Somehow the subprocess will always throw an error if we try to terminate and close it
                #  Since it poses no problems to us (and I think it closes after some time anyway)
                #  we will ignore it for now...
                # update.message.reply_text(f'Error while stopping subprocess:\n{e}')
                pass
        else:
            update.message.reply_text('Der Server ist schon ausgeschaltet!')

    # noinspection PyUnusedLocal, PyArgumentList
    @check_permission_and_prepare
    def command_start(self, update: Update, context: CallbackContext) -> None:
        if self.server_control.is_running:
            update.message.reply_text('Der Server läuft schon!')
        else:
            # Start the game server
            try:
                self.server_control.revive_amadeus()
            except Exception as e:
                update.message.reply_text(f'Error while starting the server:\n{e}')

            # Start the "status update" subprocess
            try:
                self._start_subprocess_status_update()
            except Exception as e:
                update.message.reply_text(f'Error while starting subprocess "status update":\n{e}')

    # noinspection PyUnusedLocal, PyArgumentList
    @check_permission_and_prepare
    def command_reboot(self, update: Update, context: CallbackContext) -> None:
        if self.server_control.is_running:
            try:
                self.server_control.reboot_amadeus()
            except Exception as e:
                update.message.reply_text(f'Error:\n{e}')
        else:
            update.message.reply_text('Der Server ist nicht gestart - Kann nicht rebooten!')

    # noinspection PyUnusedLocal, PyArgumentList
    @check_permission_and_prepare
    def command_status(self, update: Update, context: CallbackContext) -> None:
        if not self.server_control.is_running:
            update.message.reply_text('Der Server ist ausgeschaltet.')
            return

        current_ip = self._current_ip

        ip_changed = ''
        if self.standard_ip != current_ip:
            ip_changed = '(Die IP hat sich seit dem letzten mal wahrscheinlich geändert!)\n'

        msg = f'Der Server läuft gerade!\n' \
              f'IPv4 Adresse: {current_ip}\n{ip_changed}' \
              f'Port: 25565'

        update.message.reply_text(msg)

    # noinspection PyUnusedLocal, PyArgumentList
    @check_permission_and_prepare
    def command_update_standard_ip(self, update: Update, context: CallbackContext) -> None:
        if not self.server_control.is_running:
            update.message.reply_text('Der Server läuft nicht. Standard IP kann nicht geändert werden.')
            return

        # Update the data.json file
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)

        json_data['standard_ip'] = self._current_ip

        with open(data_file_path, 'w') as json_file:
            json_file.write(
                json.dumps(json_data, indent=4)
            )

        # Update classes
        self.server_control.standard_ip = self._current_ip
        self.standard_ip = self._current_ip

        update.message.reply_text('IP wurde angepasst.')

    def _start_subprocess_status_update(self) -> None:
        # Send a message to the admin if the server is running
        if self.subprocess_status_update is None:
            self.subprocess_status_update = Process(
                target=send_server_status_to_admin,
                kwargs={'bot_token': self.bot_token}
            )
            self.subprocess_status_update.start()
