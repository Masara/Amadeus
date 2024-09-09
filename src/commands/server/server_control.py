import datetime
import json
import subprocess
import time

from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.servers.client import BoundServer

from src.commands.server.server_utilities import send_chat_message, send_update_to_admin

data_file_path = 'src/data/data.json'
restic_output_file = 'src/data/restic_output.txt'


# Todo "Multi-Server-Setup" -> Currently this works only with the Amadeus server
class ServerControl:
    client = None
    update = None
    context = None
    message = None

    server_name = 'amadeus'
    image_description = 'amadeus_auto_image'
    default_error_msg = 'Bitte benachrichtige den Admin und benutze KEINE weitere Befehle!'

    def __init__(self, token, update, context):
        with open(data_file_path, "r") as f:
            json_data = json.load(f)

        self.admin_chat_id = json_data['admin_chat_id']
        self.standard_ip = json_data['standard_ip']
        self.running_test_bot = json_data['running_test_bot']

        self.restic_backup_dir = json_data['restic_backup_dir']
        self.restic_pwd_file = json_data['restic_pwd_file']

        self.client = Client(token)
        self.update = update
        self.context = context

    def destroy_amadeus(self) -> None:
        if str(self.update.effective_user.id) != self.admin_chat_id:
            send_update_to_admin(self.update, self.context, 'Destroy', self.admin_chat_id)

        if not self.server:
            send_chat_message(self, 'Der Server ist schon gestoppt.')
            return

        send_chat_message(self, 'Starte das Herunterfahren des Servers...')

        # Restic
        if not self.running_test_bot:
            self._execute_restic_backup()

        # Shuts down server gracefully
        self.client.servers.shutdown(self.server)

        # Wait for shutdown
        self.wait_for_server(80, 'off', 'Herunterfahren')

        # Delete last Image
        all_images = self.client.images.get_all()
        for image in all_images:
            if image.data_model.description == self.image_description:
                # Delete ALL images with given description
                last_image = self.client.images.get_by_id(image.data_model.id)
                self.client.images.delete(last_image)

        # Create new Image
        new_image = self.client.servers.create_image(self.server, description=self.image_description)
        image_id = new_image.image.data_model.id

        send_chat_message(self, 'Erstelle das Server Image, dies kann ein paar Minuten dauern...')

        max_image_ticks = 60
        while self.client.images.get_by_id(image_id).data_model.status != 'available':
            time.sleep(10)
            max_image_ticks -= 1

            if max_image_ticks <= 0:
                send_chat_message(
                    self,
                    f'Das Sichern der Speicherdaten braucht länger als gewöhnlich!\n{self.default_error_msg}',
                    True
                )
                return

        # Delete Server
        self.client.servers.delete(self.server)

        send_chat_message(self, 'Herunterfahren abgeschlossen.')

    def _execute_restic_backup(self) -> None:
        # Parameters
        restic_call = f'ssh -o "StrictHostKeyChecking no" root@{self.current_ip} restic -r'
        forget_params = 'forget --keep-last 20 --keep-monthly 4 --keep-yearly 1 --prune'
        server_dirs_to_backup = '/opt/minecraft/server/HoloBros/'

        # Remove old snapshots of the backup
        send_chat_message(self, 'Entferne alte Snapshots vom Backup...')
        forget_command = f'{restic_call} {self.restic_backup_dir} {forget_params} --password-file {self.restic_pwd_file}'

        with open('restic_output.txt', 'a+') as f:
            f.write(f'{datetime.datetime.now()}\n\n')
            process = subprocess.Popen(forget_command, shell=True, stdout=f)
            process.wait()

        if process.returncode != 0:
            send_chat_message(self, f'(Restic) Error while removing old snapshots! Please contact the admin!'
                                    f'\nReturncode: {process.returncode}', True)

        # Backup the game savedata to Salierie
        send_chat_message(self, 'Erstelle das (restic) Backup...')
        backup_command = f'{restic_call} {self.restic_backup_dir} --verbose=3 backup {server_dirs_to_backup}' \
                         f' --password-file {self.restic_pwd_file}'

        with open('restic_output.txt', 'a') as f:
            process = subprocess.Popen(backup_command, shell=True, stdout=f)
            process.wait()

        if process.returncode != 0:
            send_chat_message(self, f'(Restic) Backup error! Please contact the admin! '
                                    f'The bot will be stopped but the game server is still running.\n'
                                    f'Returncode: {process.returncode}', True)
            raise Exception('Restic backup error. Server is still running.')

    def revive_amadeus(self) -> None:
        if str(self.update.effective_user.id) != self.admin_chat_id:
            send_update_to_admin(self.update, self.context, 'Revive', self.admin_chat_id)

        if self.is_running:
            send_chat_message(self, 'Server läuft schon!')
            return

        send_chat_message(self, 'Beginne Serverstart Process...')

        # Get image
        send_chat_message(self, 'Spiele letzten Speicherpunkt ein...')
        all_images = self.client.images.get_all()
        last_image = None
        for image in all_images:
            if image.data_model.description == self.image_description:
                last_image = self.client.images.get_by_id(image.data_model.id)
                break

        if not last_image:
            send_chat_message(self, 'Fehler! Es wurden keine Speicherdaten gefunden!\n'
                                    f'{self.default_error_msg}', True)
            return

        # Wait if last image is still in cration process
        max_image_ticks = 60
        while self.client.images.get_by_id(last_image.data_model.id).data_model.status != 'available':
            time.sleep(10)
            max_image_ticks -= 1

            if max_image_ticks <= 0:
                send_chat_message(self, 'Es gab ein Problem beim einspielen des letzten Speicherpunktes!\n'
                                        f'{self.default_error_msg}', True)
                return

        # Create server
        self.client.servers.create(
            name=self.server_name,
            server_type=ServerType(name='cx21'),
            image=last_image,
            location=self.client.locations.get_by_name('nbg1'),
            ssh_keys=self.client.ssh_keys.get_all()
        )

        send_chat_message(self, 'Server wird gestartet, bitte warten...')

        # Wait for the server to start
        self.wait_for_server(120, 'running', 'Starten des Servers')

        # Check if new IPv4 address
        ipv4_adress = self.current_ip
        if ipv4_adress != self.standard_ip:
            send_chat_message(self,
                              f'Warnung! Neue IP Adresse: {ipv4_adress}\n'
                              f'Nutze /updateServerStandardIP um diese Meldung nicht mehr zu zeigen.'
                              )

        send_chat_message(self, 'Der Server ist gestartet!')

    def reboot_amadeus(self) -> None:
        if str(self.update.effective_user.id) != self.admin_chat_id:
            send_update_to_admin(self.update, self.context, 'Reboot', self.admin_chat_id)

        if not self.server:
            send_chat_message(self, 'Der Server ist nicht gestart - Kann nicht rebooten!')
            return

        # Shuts down server gracefully
        send_chat_message(self, 'Fahre den Server runter...')
        self.client.servers.shutdown(self.server)

        # Wait for shutdown
        self.wait_for_server(40, 'off', 'Herunterfahren')

        # Start server
        send_chat_message(self, 'Fahre den Server wieder hoch...')
        self.client.servers.power_on(self.server)

        # Wait for start up
        self.wait_for_server(40, 'running', 'Hochfahren')

        send_chat_message(self, 'Der Server wurde erfolgreich neu gestartet!')
        return

    # ################################################ Utilities #######################################################

    def wait_for_server(self, ticks, expected_status, msg) -> None:
        error_msg = (f'Der Server hat bei der folgenden Aktion länger gebraucht als '
                     f'erwartet: "{msg}".\n {self.default_error_msg}')

        while self.server_status != expected_status:
            time.sleep(5)
            ticks -= 1

            if ticks <= 0:
                send_chat_message(self, error_msg, True)
                return

    @property
    def current_ip(self) -> str:
        if self.is_running:
            return self.server.data_model.public_net.ipv4.ip

        # if the server is not running try to get the "standard_ip" value
        return self.standard_ip

    @property
    def server(self) -> BoundServer:
        return self.client.servers.get_by_name(self.server_name)

    @property
    def server_status(self):
        return self.server.data_model.status

    @property
    def is_running(self) -> bool:
        return self.server is not None
