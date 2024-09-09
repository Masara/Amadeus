import random

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from src.commands.main_commands import MainCommands


# noinspection PyUnusedLocal
def message_handler(update: Update, context: CallbackContext) -> None:
    """Handle specific messages, that either start with /s/ for the switch command or contain certain words."""

    if not update.message.text:
        return

    user_ids = []
    if update.message.text.startswith("/s/"):
        MainCommands.command_switch_text(update, context)
    # Specify which users trigger the message handler
    elif update.effective_user.id in user_ids:
        for word in {"some_word"}:
            if word in update.message.text.lower():
                choices = ["answer"]
                answer = random.choice(choices)
                update.message.reply_text(answer)
                break
