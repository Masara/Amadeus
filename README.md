## Todo
- Maybe add an "if(onServer)" to the deploy script update_amadeus.sh
- Log file for the deploy script

### Server
- Multiple Snapshots
- Logging
- Multi-Server-Setup (multiple game servers, not only one)
- Automatisches Herunterfahren, wenn keiner auf dem Server (?)

### Telegram
- <strike>Discord Bot</strike>
- <strike>Daily Image Posting?</strike>
- Mindestwahrscheinlichkeit: Attempts instead of end probability
- Add Exception handler (decorator) for all commands

____
## Setup
### Docker setup
Pull the amadeus-docker-config repo and run the command ````make clone````. Then follow the
instructions given in the console.

____
### data.json
There has to be a ```data.json``` file in the ```src/data``` director. The follwing fields are required:
* ```admin_chat_id```
* ```telegram_bot_token```
* ```hetzner_api_token```

The structure of the ```data.json``` file can be found in the check_data_file() function in the main.py file.
___
### Backups
A restic backup repo has to be initialized in the ```./backups``` directory. Use the following command to do it:

```$ restic init --repo ./backups/[REPO_NAME] --repository-version 1```
___
## Extra - Setup without docker
### Setting up supervisord
https://stackoverflow.com/questions/16420092/how-to-make-python-script-run-as-service#answer-16420472

Open amadeus config file:
```
$ vi /etc/supervisor/conf.d/amadeus.conf
```

Input:
```
[program:amadeus]
directory=/data/amadeus
command=/data/amadeus/.venv/bin/python main.py
autostart=true
autorestart=true
killasgroup=true
#run supervisorctl update if you change stuff!
```

Then run
````
$ supervisorctl update
````

Start / Stop / Restart process commands:
```
$ supervisorctl start
$ supervisorctl stop
$ supervisorctl restart
```
