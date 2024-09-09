import json
from typing import Any

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src.commands.abstract_command_category import CommandCategory
from src.telegram_utilities import check_admin_permission

data_file_path = 'src/data/data.json'


class AdminCommands(CommandCategory):
    category_name = "Admin Commands"

    def get_command_information(self) -> dict[str, Any]:
        return {
            'help': {
                'command': 'helpAdmin',
                'function': self.command_help_with_admin_permission,
            },
            'commands': [{
                'command': 'getGeneralWhitelist',
                'function': self.commands_get_general_whitelisted_users,
                'description': '- Get all general whitelisted users'
            }, {
                'command': 'addUserToGeneralWhitelist',
                'function': self.command_add_user_to_general_whitelist,
                'description': '[username] [user_id] - Add a user to the general whitelist (reply to a msg of the user '
                               'to save yourself the arguments)'
            }, {
                'command': 'removeUserFromGeneralWhitelist',
                'function': self.command_remove_user_from_general_whitelist,
                'description': '[user_id] - Remove a user from the general whitelist (reply to a msg of the user to '
                               'save yourself the arguments)'
            }, {
                'command': 'getServerWhitelist',
                'function': self.commands_get_server_whitelisted_users,
                'description': '- Get all server whitelisted users'
            }, {
                'command': 'addUserToServerWhitelist',
                'function': self.command_add_user_to_server_whitelist,
                'description': '[username] [user_id] - Add a user to the server whitelist (reply to a msg of the user '
                               'to save yourself the arguments)'
            }, {
                'command': 'removeUserFromServerWhitelist',
                'function': self.command_remove_user_from_server_whitelist,
                'description': '[user_id] - Remove a user from the server whitelist (reply to a msg of the user to '
                               'save yourself the arguments)'
            }]
        }

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_help_with_admin_permission(self, update: Update, context: CallbackContext) -> None:
        self.command_help(update, context)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_add_user_to_general_whitelist(self, update: Update, context: CallbackContext) -> None:
        self._add_to_whitelist('general_whitelist', update)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_add_user_to_server_whitelist(self, update: Update, context: CallbackContext) -> None:
        self._add_to_whitelist('server_whitelist', update)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_remove_user_from_general_whitelist(self, update: Update, context: CallbackContext) -> None:
        self._remove_from_whitelist('general_whitelist', update)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_remove_user_from_server_whitelist(self, update: Update, context: CallbackContext) -> None:
        self._remove_from_whitelist('server_whitelist', update)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def commands_get_general_whitelisted_users(self, update: Update, context: CallbackContext) -> None:
        self._get_whitelisted_users('General', 'general_whitelist', update)

    # noinspection PyUnusedLocal
    @check_admin_permission
    def commands_get_server_whitelisted_users(self, update: Update, context: CallbackContext) -> None:
        self._get_whitelisted_users('Server', 'server_whitelist', update)

    # ######################### Utilities ######################### #

    @staticmethod
    def _add_to_whitelist(whitelist_name: str, update: Update) -> None:
        with open(data_file_path, 'r') as f:
            data_file_content = json.loads(f.read())

        if update.effective_message.reply_to_message:
            user_data = update.effective_message.reply_to_message.from_user

            username = user_data['username']
            user_id = str(user_data['id'])
        else:
            arguments = update.effective_message.text.split(' ')[1:]

            if len(arguments) != 2:
                update.message.reply_text(text='Error: Too many or not enough Arguments.')
                return

            username = arguments[0]
            user_id = arguments[1]

            # Test if ID argument was given correctly
            try:
                int(arguments[1])
            except ValueError:
                update.message.reply_text(text='Error: The ID has to be numbers only.')
                return

        if user_id in data_file_content[whitelist_name]:
            update.message.reply_text(text=f'{username} was already in the whitelist!')
            return

        data_file_content[whitelist_name][user_id] = username

        # Save the new data.json
        with open(data_file_path, 'w') as f:
            f.write(json.dumps(data_file_content))

        update.message.reply_text(text=f'{username} was added to the whitelist!')

    @staticmethod
    def _get_whitelisted_users(title: str, whitelist_name: str, update: Update) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        whitelist = json_data[whitelist_name]

        text = f'<b>Users on the {title}-Whitelist:</b>'

        for entry in whitelist:
            text += f'\n{whitelist[entry]} ({entry})'

        update.message.reply_text(
            text=text,
            parse_mode='HTML'
        )

    @staticmethod
    def _remove_from_whitelist(whitelist_name: str, update: Update) -> None:
        with open(data_file_path, 'r') as f:
            data_file_content = json.loads(f.read())

        if update.effective_message.reply_to_message:
            user_data = update.effective_message.reply_to_message.from_user
            user_id = str(user_data['id'])
        else:
            arguments = update.effective_message.text.split(' ')[1:]

            if len(arguments) != 1:
                update.message.reply_text(text='Error: Too many or not enough Arguments.')
                return

            user_id = arguments[0]

        if user_id not in data_file_content[whitelist_name]:
            update.message.reply_text(text='Error: User not found in whitelist!')
            return

        username = data_file_content[whitelist_name].pop(user_id)

        # Save the new data.json
        with open(data_file_path, 'w') as f:
            f.write(json.dumps(data_file_content))

        update.message.reply_text(text=f'{username} was removed from the whitelist!')
