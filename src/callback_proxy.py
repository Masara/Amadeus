# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src.commands.main_commands import MainCommands


class CallbackProxy:

    @staticmethod
    def handle_callback(update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        callback_data = query.data

        # Urban Dictionary
        if callback_data in {'ud_next', 'ud_previous'}:
            MainCommands().change_urbandictionary_page(query)

        else:
            update.message.reply_text(text='CallbackProxyError: Could not find an appropriate handler for this task!')
