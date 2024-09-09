# All self objects have to be up-to-date, thus we do it with a self parameter
def send_chat_message(self, new_message: str, is_error: bool = False) -> None:
    # If there was an error, send a seperate message to inform user and admin
    if is_error:
        self.update.message.reply_text('ACHTUNG! ' + new_message)
        if self.update.effective_user.id != self.admin_chat_id:
            self.context.bot.send_message(chat_id=self.admin_chat_id, text=f'ACHTUNG!\n{new_message}')
        return

    # Send the first message
    if self.message is None:
        self.message = self.update.message.reply_text(new_message)
        return

    # New messages will be appended to the first
    old_text = self.message.text
    new_text = old_text + '\n' + new_message

    self.message = self.context.bot.edit_message_text(
        chat_id=self.message.chat_id,
        message_id=self.message.message_id,
        text=new_text
    )


def send_update_to_admin(update, context, action, admin_chat_id):
    username_or_id = update.effective_user.username
    if username_or_id is None:
        username_or_id = update.effective_user.id

    message = f'{update.effective_user.full_name} ({username_or_id}) hat die Aktion ' \
              f'"{action}" ausgeführt.'
    context.bot.send_message(chat_id=admin_chat_id, text=message)
