"""!!!!!!!!!!!!!!!!!!!! CURRENTLY NOT IMPLEMENTED !!!!!!!!!!!!!!!!!!!!"""
import datetime
import json
import os
import random
import time
from multiprocessing import Process
from typing import Any

import cloudscraper
from bs4 import BeautifulSoup
# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.bot import Bot
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext
# noinspection PyPackageRequirements
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton

from src.commands.abstract_command_category import CommandCategory
from src.telegram_utilities import check_general_whitelist_permission, check_admin_permission, stop_subprocess

data_file_path = 'src/data/data.json'


class ImageCommands(CommandCategory):
    _votes_dir = 'src/data/image_votes.json'
    image_list_dir = 'src/data/image_list.json'

    subprocess_daily_iotd = None
    scraper = None
    __instance = None
    category_name = "Image Commands"

    def __init__(self):
        # Singleton
        if ImageCommands.__instance is not None:
            raise Exception("This class is a singleton! Call with ImageCommands.get_instance()")
        else:
            ImageCommands.__instance = self

        # Create image data files if they don't exist yes
        for file_path in {self.image_votes_dir, self.image_list_dir}:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.bad({}, f)

        self.scraper = cloudscraper.create_scraper()

        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        iotd_chat_ids = json_data['iotd']['chats']

        if self.subprocess_daily_iotd is None and iotd_chat_ids:
            self._start_subprocess_daily_iotd()

    @staticmethod
    def get_instance():
        """ Get Singleton Class """
        if ImageCommands.__instance is None:
            ImageCommands()
        return ImageCommands.__instance

    def get_command_information(self) -> dict[str, Any]:
        return {
            'help': {
                'command': 'helpImage',
                'function': self.command_help,
            },
            'commands': [{
                'command': 'image',
                'function': self.command_get_random_image,
                'description': "- Get a random Image from someImageDatabase.com"
            }, {
                'command': 'very_good',
                'function': self.command_get_random_very_good,
                'description': "- Get a random Image you love"
            }, {
                'command': 'good',
                'function': self.command_get_random_good,
                'description': "- Get a random Image you think is good"
            }, {
                'command': 'bad',
                'function': self.command_get_random_bad,
                'description': "- Get a random Image you think is bad"
            }, {
                'command': 'iotd',
                'function': self.command_get_image_of_the_day,
                'description': "- Get the Image of the day!"
            }, {
                'command': 'toggle_iotd',
                'function': self.command_toggle_daily_image_post,
                'description': "- I will post the Image of the day every day!"
                # }, {
                #     'command': 'update_image_list',
                #     'function': self.command_recreate_image_list,
                #     'description': '- Recreate image list file with all the vote data (if there should be problems)'
            }]
        }

    # ################################## Commands & Handler ###################################

    @check_general_whitelist_permission
    def command_get_random_image(self, update: Update, context: CallbackContext) -> None:
        image_data = self._get_image()
        image_id = image_data["url"].split('/')[-1]

        context.bot.send_photo(
            update.effective_chat.id,
            photo=image_data['image_url'],
            caption=f'[{image_data["name"]}]({image_data["url"]})',
            parse_mode='Markdown',
            reply_markup=self._create_image_vote_buttons(image_id)
        )

    # ############### Get previous votes

    @check_general_whitelist_permission
    def command_get_random_very_good(self, update: Update, context: CallbackContext) -> None:
        user_id = str(update.effective_user.id)
        caption = f'{update.effective_user.username}' + ' totally loves {}!'
        self._send_random_image_from_choice(update, context, user_id, 'very_good', caption)

    @check_general_whitelist_permission
    def command_get_random_bad(self, update: Update, context: CallbackContext) -> None:
        user_id = str(update.effective_user.id)
        caption = f'{update.effective_user.username}' + ' would never touch {}.'
        self._send_random_image_from_choice(update, context, user_id, 'bad', caption)

    @check_general_whitelist_permission
    def command_get_random_good(self, update: Update, context: CallbackContext) -> None:
        user_id = str(update.effective_user.id)
        caption = '{} is one of ' + f'{update.effective_user.username}\'s favorite images!'
        self._send_random_image_from_choice(update, context, user_id, 'good', caption)

    # ############### Image of the day

    # noinspection PyUnusedLocal
    @check_general_whitelist_permission
    def command_get_image_of_the_day(self, update: Update, context: CallbackContext) -> None:
        self._send_iotd(update.effective_chat.id)

    # noinspection PyUnusedLocal
    @check_general_whitelist_permission
    def command_toggle_daily_image_post(self, update: Update, context: CallbackContext) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        chat_ids = json_data['iotd']['chats']

        chat_id = str(update.effective_chat.id)
        if chat_id not in chat_ids:
            chat_ids.append(chat_id)
            update.message.reply_text('Started daily Image of the day posts!')
        else:
            index = chat_ids.index(chat_id)
            chat_ids.pop(index)
            update.message.reply_text('Stopped daily Image of the day posts!')

        # Save list file
        with open(data_file_path, 'w') as f:
            f.write(json.dumps(json_data))

        # Stop subprocess if no chats are in the list or start it if it isn't already running
        if not chat_ids and self.subprocess_daily_iotd is not None:
            try:
                stop_subprocess(self.subprocess_daily_iotd)
                self.subprocess_daily_iotd = None
            except Exception as e:
                update.message.reply_text(f'Error while stopping subprocess iotd:\n{e}')
        elif chat_ids and self.subprocess_daily_iotd is None:
            self._start_subprocess_daily_iotd()

    # ############### Misc Commands

    # noinspection PyUnusedLocal
    @check_admin_permission
    def command_recreate_image_list(self, update: Update, context: CallbackContext) -> None:
        """Dumps the old file and recreates a completly new list with the vote data"""
        with open(self.image_votes_dir, 'r') as f:
            data = json.loads(f.read())

        image_list_data = {}

        for image_id in list(data.keys()):
            image_votes = data[image_id]

            for image_voter in list(image_votes.keys()):

                if image_voter not in image_list_data.keys():
                    image_list_data[image_voter] = {
                        'bad': [], 'very_good': [], 'good': []
                    }

                vote = image_votes[image_voter]

                if not vote:
                    continue

                image_list_data[image_voter][vote].append(image_id)

        with open(self.image_list_dir, 'w') as f:
            f.write(json.dumps(image_list_data))

        update.message.reply_text('I have successfully recreated the image list!')

    def handle_rating(self, update: Update, context: CallbackContext, choice: str) -> None:
        # Next Image
        if choice == 'Next':
            self.command_get_random_image(update, context)
            return

        # Handle voting
        message = update.callback_query.message
        image_id = message.caption_markdown.split('/')[-1].split(')')[0]
        user_id = str(update.callback_query.from_user.id)

        self._update_image_list(user_id, image_id, choice)
        self._update_image_votes(user_id, image_id, choice)

        update.callback_query.edit_message_caption(
            caption=f'{update.callback_query.message.caption_markdown}',
            parse_mode='Markdown',
            reply_markup=self._create_image_vote_buttons(image_id)
        )

    # ################################## Functions ############################################

    # ######### Image of the day utilities

    @staticmethod
    def _todays_timestamp() -> str:
        return datetime.date.today().strftime("%y/%m/%d")

    def _send_iotd(self, chat_id: str) -> None:
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)
        bot_token = json_data['telegram_bot_token']
        bot = Bot(token=bot_token)

        # Check if we already generated a new image today
        if json_data['iotd']['last_sent_date'] == self._todays_timestamp():
            image_id = json_data['iotd']['image_id']
            image_data = self._get_image(image_id)
        else:
            image_data = self._get_image('', is_new_image=True)

            # Update last_sent_date, so we won't change the image of the day on the same day
            with open(data_file_path, 'r') as f:
                json_data = json.load(f)
            json_data['iotd']['last_sent_date'] = self._todays_timestamp()
            json_data['iotd']['image_id'] = image_data["image_id"]
            with open(data_file_path, 'w') as f:
                f.write(json.dumps(json_data))

        image_type = 'Image' if image_data['image_type'] == 'cat' else 'dog'

        bot.send_photo(
            chat_id=chat_id,
            photo=image_data['image_url'],
            caption=f'Todays {image_type} of the Day!\n[{image_data["name"]}]({image_data["url"]})',
            parse_mode='Markdown',
            reply_markup=self._create_image_vote_buttons(image_data["image_id"])
        )

    # Todo Cronjob for specific time?
    #  Use Threading to be able to stop it
    #  https://stackoverflow.com/questions/5114292/break-interrupt-a-time-sleep-in-python#answer-46346184
    #  -> Auch für Server Process!
    def _subprocess_send_daily_iotd(self) -> None:
        """Sends an automated message to the chats that activated iotd posting"""
        with open(data_file_path, 'r') as f:
            json_data = json.load(f)

        while json_data['iotd']['chats']:
            # We want the data to be up-to-date
            with open(data_file_path, 'r') as f:
                json_data = json.load(f)
            chat_ids = json_data['iotd']['chats']

            # Get current date and check if we already sent an iotd today, and only send it after 11 o'clock
            if 10 <= datetime.datetime.now().hour <= 12:
                for chat_id in chat_ids:
                    self._send_iotd(chat_id)

            time.sleep(10800)  # repeat the loop every 3h

    def _start_subprocess_daily_iotd(self) -> None:
        if self.subprocess_daily_iotd is None:
            self.subprocess_daily_iotd = Process(target=self._subprocess_send_daily_iotd)
            self.subprocess_daily_iotd.start()

    # ######### Misc

    def _send_random_image_from_choice(
            self,
            update: Update,
            context: CallbackContext,
            user_id: str,
            choice: str,
            caption: str
    ) -> None:
        content = self._get_image_list_data(self.image_list_dir)
        data = json.loads(content)
        choice_data = data[user_id][choice]

        try:
            image_id = random.choice(choice_data)
        except IndexError:
            update.message.reply_text(f'You don\'t have any images for your choice \"{choice}\"!')
            return

        image_data = self._get_image(image_id)

        image_caption = caption.format(f'[{image_data["name"]}]({image_data["url"]})')

        context.bot.send_photo(
            update.effective_chat.id,
            photo=image_data['image_url'],
            caption=image_caption,
            parse_mode='Markdown',
            reply_markup=self._create_image_vote_buttons(image_id)
        )

    def _update_image_votes(self, user_id: str, image_id: str, vote: str) -> None:
        # Get image_votes data
        content_votes = self._get_image_list_data(self.image_votes_dir)
        data_votes = json.loads(content_votes)

        # Add possibly missing dict entries
        if image_id not in list(data_votes.keys()):
            data_votes[image_id] = {}

        if user_id not in list(data_votes[image_id].keys()):
            data_votes[image_id][user_id] = ''

        # Update image votes data
        if data_votes[image_id][user_id] == vote:
            data_votes[image_id][user_id] = ''
        else:
            data_votes[image_id][user_id] = vote

        # Save votes file
        with open(self.image_votes_dir, 'w') as f:
            f.write(json.dumps(data_votes))

    def _update_image_list(self, user_id: str, image_id: str, vote: str) -> None:
        content_list = self._get_image_list_data(self.image_list_dir)
        data_list = json.loads(content_list)

        if user_id not in data_list:
            data_list[user_id] = {
                'bad': [], 'very_good': [], 'good': []
            }

        # Update image list
        for choice in list(data_list[user_id].keys()):
            # Remove image from all other lists and append her to the new choice
            if choice != vote:
                if image_id not in data_list[user_id][choice]:
                    continue

                data_list_index = data_list[user_id][choice].index(image_id)
                data_list[user_id][choice].pop(data_list_index)
            elif image_id not in data_list[user_id][vote]:
                data_list[user_id][vote].append(image_id)
            elif image_id in data_list[user_id][vote]:
                data_list_index = data_list[user_id][choice].index(image_id)
                data_list[user_id][choice].pop(data_list_index)

        # Save list file
        with open(self.image_list_dir, 'w') as f:
            f.write(json.dumps(data_list))

    @staticmethod
    def _get_image_list_data(file_dir: str) -> str:
        try:
            f = open(file_dir, 'r')
        except FileNotFoundError:
            f = open(file_dir, 'w')
            f.write('{}')
            f.close()
            f = open(file_dir, 'r')

        content = f.read() or '{}'
        f.close()

        return content

    def _create_image_vote_buttons(self, image_id) -> InlineKeyboardMarkup:
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text='♥ 0', callback_data='very_good'),
                InlineKeyboardButton(text='👍 0', callback_data='good')
            ], [
                InlineKeyboardButton(text='💩 0', callback_data='bad'),
                # Rightarrow
                InlineKeyboardButton(text='\U000027A1', callback_data='Next')
            ]
        ])

        with open(self.image_votes_dir, 'r') as f:
            data = json.loads(f.read())

        if image_id not in list(data.keys()):
            return reply_markup

        for voter in data[image_id].keys():
            choice = data[image_id][voter]

            for row in reply_markup.inline_keyboard:
                for button in row:
                    if button['callback_data'] == choice:
                        text_parts = str(button['text']).split(' ')
                        text_parts[-1] = str(int(text_parts[-1]) + 1)
                        button.text = ' '.join(text_parts)
                        break

        return reply_markup

    def _get_image(self, image_id: str = '', is_new_image: bool = False) -> dict:
        if not image_id:
            html = self.scraper.get('https://someImageDatabase.com/random').text
        else:
            html = self.scraper.get(f'https://someImageDatabase.com/image/{image_id}').text

        image_info = {}
        while True:
            s = BeautifulSoup(html, 'lxml')

            for script in s.select('script'):
                if script.text:
                    image_info = json.loads(script.text)
                    break
            if image_info == {}:
                raise ValueError("No image information found!")

            body = s.select('body')[0]
            div = body.next_element.next_element

            # noinspection PyUnresolvedReferences
            image_id = json.loads(div.attrs['data-page'])['url'].split('/')[-1]

            if not (is_new_image and self.is_image_already_voted_often(image_id)):
                break

        data = {
            'name': image_info['givenName'],
            'image_url': image_info['image'],
            'url': f'https://someImageDatabase.com/image/{image_id}',
            'image_type': image_info['image_type'],
            'image_id': image_id,
        }

        return data

    def is_image_already_voted_often(self, image_id: str) -> bool:
        if not image_id:
            return False

        with open(self.image_votes_dir, 'r') as f:
            data = json.loads(f.read())

        if image_id not in data:
            return False

        # True, if the image has more than one vote
        return len(data[image_id]) > 1
