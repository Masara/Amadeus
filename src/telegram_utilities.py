import json
import time
from multiprocessing.context import Process

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

data_file_path = 'src/data/data.json'


def check_admin_permission(func):
    """ Wrapper function to check if a telegram user has admin permissions to use certain commands """

    def wrapper(self, update: Update, context: CallbackContext, **kwargs):
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        admin_id = json_data['admin_chat_id']

        user_id = str(update.effective_user.id)
        if user_id == admin_id:
            # noinspection PyCallingNonCallable
            func(self, update, context, **kwargs)
        else:
            update.message.reply_text('You have no permission to use this command!')

    return wrapper


def check_general_whitelist_permission(func):
    """ Wrapper function to check if a telegram user has whitelist permissions to use certain commands """

    def wrapper(self, update: Update, context: CallbackContext, **kwargs):
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        whitelist = json_data['general_whitelist']

        user_id = str(update.effective_user.id)
        if user_id in list(whitelist.keys()):
            # noinspection PyCallingNonCallable
            func(self, update, context, **kwargs)
        else:
            update.message.reply_text(
                'You have no permission to use this command!\n'
                'Please ask the Bot maintainer to add you to the whitelist to get permissions!'
            )

    return wrapper


def stop_subprocess(subprocess: Process) -> None:
    if subprocess is not None:
        subprocess.terminate()

        unclosed = True
        max_tries = 120
        while unclosed and max_tries >= 0:
            # noinspection PyBroadException
            try:
                subprocess.close()
            except Exception:
                time.sleep(1)
                max_tries -= 1
                continue
            unclosed = False

        if max_tries < 0:
            # Last try, it will throw an exception for us anyway
            subprocess.close()
