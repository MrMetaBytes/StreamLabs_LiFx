ScriptName="LiFx Controllers"
Website="https://github.com/MrMetaBytes/StreamLabs_LiFx"
Description="Enables Viewer Control of LiFx light bulbs"
Creator="MrMetaBytes"
Version="0.0.1"

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
from script_settings import ScriptSettings

global Config
Config = ScriptSettings()

global callbacks
callbacks = []

# =================================
#       Utility Methods
# =================================
def log(msg):
    Parent.Log('LiFx Controller', msg)


def load_settings():
    settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
    Config.load(settings_file)


def can_afford(user, subcommand):
    user_points = Parent.GetPoints(user)
    subcommand_cost = Config.subcommands[subcommand]['cost']
    if user_points >= subcommand_cost:
        return True
    else:
        Parent.SendStreamMessage('You can not afford this command')



# =================================
#       LiFx Commands
# =================================
def on():
    endpoint = 'https://api.lifx.com/v1/lights/group:%s/state' % Config.group
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    payload = {
        'power': 'on'
    }
    Parent.PutRequest(endpoint, headers, payload)
    Config.subcommands['off']['enabled'] = True


def off():
    global callbacks
    _config = Config.subcommands['off']
    if _config['response']:
        Parent.SendStreamMessage(_config['response'])

    endpoint = 'https://api.lifx.com/v1/lights/group:%s/state' % Config.group
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    payload = {
        'power': 'off'
    }
    Parent.PutRequest(endpoint, headers, payload)
    callbacks.append((time.time() + _config['duration'], on))
    _config['enabled'] = False


# =================================
#       Core Events
# =================================
def Init():
    pass


def Execute(data):
    # Do we care about this message?
    if not (data.IsChatMessage() and data.GetParam(0).lower() == '!lights'):
        return

    # Is the sub command enabled?
    subcommand = data.GetParam(1)
    subcommand_dict = Config.subcommands.get(subcommand, {})
    subcommand_enabled = subcommand_dict.get('enabled', False)
    if not subcommand_enabled:
        return

    # Can the user afford it?
    if not can_afford(data.User, subcommand):
        return

    subcommand_func = globals()[subcommand]
    subcommand_func()
    Parent.RemovePoints(data.User, data.UserName, subcommand_dict['cost'])


def Tick():
    global callbacks
    new_callbacks = []
    for timeout, func in callbacks:
        if time.time() >= timeout:
            func()
        else:
            new_callbacks.append((timeout, func))
    callbacks = new_callbacks



def ReloadSettings(jsonData):
    load_settings()


def ScriptToggled(state):
    if state:
        load_settings()
