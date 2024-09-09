import json
from typing import Any

# noinspection PyPackageRequirements
import requests
# noinspection PyPackageRequirements
from telegram import Update, CallbackQuery
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext
# noinspection PyPackageRequirements
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton

from src.commands.abstract_command_category import CommandCategory


class MainCommands(CommandCategory):
    category_name = "Main Commands"

    urbandictionary_reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text='◀ Previous', callback_data='ud_previous'),
            InlineKeyboardButton(text='Next ▶', callback_data='ud_next')
        ]
    ])

    def get_command_information(self) -> dict[str, Any]:
        return {
            'help': {
                'command': 'helpMain',
                'function': self.command_help,
            },
            'commands': [{
                'command': 'ud',
                'function': self.command_urban_dictionary_definition,
                'description': "{Term} - Get the Urban Dictionary definition"
            }, {
                'command': 's',
                'function': self.command_switch_text,
                'description': "{Word} {New word(s)} or /s/{Words}/{New word(s)} - Replace a word with a new word or "
                               "sentence"
            }]
        }

    @staticmethod
    def command_switch_text(update: Update, context: CallbackContext) -> None:
        if update.effective_message.reply_to_message is None:
            update.message.reply_text(text='You must reply to a message whose content you want to change.')
            return

        change_me = update.effective_message.reply_to_message.text
        command_text = update.effective_message.text

        if len(command_text) > 3 and command_text[2] == "/":
            arguments = command_text.split('/s/', 1)[1].split('/', 1)

            if len(arguments) != 2:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Error: Wrong use of command. Use in the following style: /s/Original Part/New Text.",
                    reply_to_message_id=update.effective_message.reply_to_message.message_id
                )
                return
        else:
            arguments = command_text.split('/s ')[1].split(' ')

            if len(arguments) > 2:
                first = arguments[0]
                arguments = arguments[1::1]
                arguments = ' '.join(arguments)
                arguments = [first, arguments]

            if len(arguments) < 1:
                update.message.reply_text(text='Error: Missing Arguments.')
                return

            if len(arguments) == 1:
                arguments.append('')

        text = f'Did you mean: "{change_me.replace(arguments[0], arguments[1])}"'

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_to_message_id=update.effective_message.reply_to_message.message_id
        )

    # noinspection PyUnusedLocal
    def command_urban_dictionary_definition(self, update: Update, context: CallbackContext) -> None:
        term = update.message.text.replace('/ud ', '')
        if not term or term == '' or update.message.text == '/ud':
            update.message.reply_text('Fehler: Bitte einen richtigen Suchbegriff angeben.')
            return

        text = self._create_urbandictionary_message(term)
        if not text:
            update.message.reply_text('No definition found.')
            return

        update.message.reply_text(
            text=text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=self.urbandictionary_reply_markup
        )

    @staticmethod
    def _create_urbandictionary_message(term: str, page: int = 1) -> str:
        # Get data
        results = requests.get(
            url='https://api.urbandictionary.com/v0/define',
            params={'term': term}
        )

        definitions = json.loads(results.text)['list']
        if not definitions:
            return ''

        # Create message
        definition_data = definitions[page - 1]
        text = f'{definition_data["definition"]}\n\n<b>Example:</b>\n<i>{definition_data["example"]}</i>\n\nPage {page}/{len(definitions)}'

        # We get errors because of these... dunno how to handle them yet
        text = text.replace('<3', '❤️')

        # Replace [bracketed text] with links
        whole_text = text.split('[')
        rebuild_text = [whole_text[0]]
        whole_text = whole_text[1::1]

        for text_part in whole_text:
            text_part = text_part.split(']')
            text_part[0] = f'<a href="https://www.urbandictionary.com/define.php?term=' \
                           f'{text_part[0]}">{text_part[0]}</a>'
            text_part = ''.join(text_part)
            rebuild_text.append(text_part)

        text = ''.join(rebuild_text)

        return f'<b>{term}</b>\n{text}'

    def change_urbandictionary_page(self, callback_query: CallbackQuery) -> None:
        old_text = callback_query.message.text
        term = old_text.split('\n')[0]

        try:
            page_info = callback_query.message.text.split('\n')[-1].split(' ')[-1].split('/')
            current_page = int(page_info[0])
            last_page = int(page_info[1])

            if callback_query.data == 'ud_previous':
                page = current_page - 1 if current_page != 1 else last_page
            else:  # callback_query.data == 'ud_next'
                page = current_page + 1 if current_page != last_page else 1

            text = self._create_urbandictionary_message(term, page)

        except (ValueError, IndexError):
            text = f'{callback_query.message.text_html}\n\n<b>Something went wrong! I can\'t change the page!</b>'

        callback_query.message.edit_text(
            text=text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=self.urbandictionary_reply_markup
        )
