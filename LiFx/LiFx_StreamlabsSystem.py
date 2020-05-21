ScriptName="LiFx Controllers"
Website="https://github.com/MrMetaBytes/StreamLabs_LiFx"
Description="Enables Viewer Control of LiFx light bulbs"
Creator="MrMetaBytes"
Version="0.0.1"

import json
import os
import re
import sys
import time
from copy import deepcopy

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
from script_settings import ScriptSettings

global Config
Config = ScriptSettings()

global callbacks
callbacks = []

global ON_COOLDOWN
ON_COOLDOWN = False

global LAST_COMMAND_TIME
LAST_COMMAND_TIME = time.time()

global DEFAULTED
DEFAULTED = True

COLOR_PATTERN = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')

# =================================
#       Utility Methods
# =================================
def log(msg):
    Parent.Log('LiFx Controller', msg)


def load_settings():
    settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
    Config.load(settings_file)


def reset_cd():
    global callbacks
    global ON_COOLDOWN
    ON_COOLDOWN = False


#TODO: Work in Progress, I can't seem to get the UI button to trigger this?
def add_color():
    settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
    custom_color_count = len(Config.custom_colors)
    last_label_key = 'custom_' + str(custom_color_count)
    last_color_key = 'color_' + str(custom_color_count)
    new_label_key = 'custom_' + str(custom_color_count+1)
    new_color_key = 'color_' + str(custom_color_count+1)
    Config.settings[new_label_key] = deepcopy(Config.settings[last_label_key])
    Config.settings[new_color_key] = deepcopy(Config.settings[last_color_key])
    Config.settings[new_label_key]['value'] = new_label_key
    Config.save(settings_file)


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
def activate_scene(scene_name=None):
    if scene_name is None:
        scene_name = Config.default_scene
    scene_uuid = None
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    get_scenes_endpoint = 'https://api.lifx.com/v1/scenes'
    response = json.loads(Parent.GetRequest(get_scenes_endpoint, headers))
    scenes = json.loads(response['response'])
    for scene in scenes:
        if scene['name'] == scene_name:
            scene_uuid = scene['uuid']
            break
    if not scene_uuid:
        return False
    # scenes = response.json()
    set_scene_endpoint = 'https://api.lifx.com/v1/scenes/scene_id:%s/activate' % scene_uuid
    
    Parent.PutRequest(set_scene_endpoint, headers, {})


def on():
    _config = Config.subcommands['off']
    groups = _config['groups'].split(',')
    selectors = [
        'group:{}'.format(group.strip())
        for group in groups
    ]
    selector_expression = ','.join(selectors)
    endpoint = 'https://api.lifx.com/v1/lights/%s/state' % selector_expression
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    payload = {
        'power': 'on'
    }
    Parent.PutRequest(endpoint, headers, payload)
    _config['enabled'] = True


def off(data):
    global callbacks
    _config = Config.subcommands['off']
    _config['enabled'] = False
    if _config['response']:
        Parent.SendStreamMessage(_config['response'])

    groups = _config['groups'].split(',')
    selectors = [
        'group:{}'.format(group)
        for group in groups
    ]
    selector_expression = ','.join(selectors)
    endpoint = 'https://api.lifx.com/v1/lights/%s/state' % selector_expression
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    payload = {
        'power': 'off'
    }
    Parent.PutRequest(endpoint, headers, payload)
    Parent.RemovePoints(data.User, data.UserName, _config['cost'])
    callbacks.append((time.time() + _config['duration'], on))
    return True


def color(data):
    global callbacks
    _config = Config.subcommands['color']

    color_code = data.GetParam(2).lower()
    if color_code == 'list':
        options = Config.LIFX_COLORS + list(Config.custom_colors.keys())
        option_str = ', '.join(options)
        Parent.SendStreamMessage('You can change the lights to any of the following colors, or use a custom hex code! - ' + option_str)
        return False
    if not any([
            color_code in Config.LIFX_COLORS,
            color_code in Config.custom_colors,
            COLOR_PATTERN.match(color_code),
            'random' in color_code,
        ]):
            Parent.SendStreamMessage('Invalid color code')
            return False
    elif _config['response']:
        Parent.SendStreamMessage(_config['response'])

    color_code = Config.custom_colors.get(color_code, color_code)
    if 'random' in color_code:
        color_code = "#{:02x}{:02x}{:02x}".format(
            Parent.GetRandom(0, 255),
            Parent.GetRandom(0, 255),
            Parent.GetRandom(0, 255),
        )
        Parent.SendStreamMessage('I picked {} as the random Color'.format(color_code))
    if 'rgba' in color_code:
        red, green, blue, __ = re.findall(r'\d+', color_code)
        color_code = "#{:02x}{:02x}{:02x}".format(int(red), int(green), int(blue))
    log('Setting color to: ' + color_code)
    groups = _config['groups'].split(',')
    selectors = [
        'group:{}'.format(group)
        for group in groups
    ]
    selector_expression = ','.join(selectors)
    endpoint = 'https://api.lifx.com/v1/lights/%s/state' % selector_expression
    headers = {
        'Authorization': 'Bearer %s' % Config.lifx_token,
    }
    payload = {
        'color': color_code
    }
    Parent.PutRequest(endpoint, headers, payload)
    Parent.RemovePoints(data.User, data.UserName, _config['cost'])
    return True


# =================================
#       Core Events
# =================================
def Init():
    pass


def Execute(data):
    global callbacks
    global ON_COOLDOWN
    global DEFAULTED
    global LAST_COMMAND_TIME
    # Do we care about this message?
    if not (data.IsChatMessage() and data.GetParam(0).lower() == '!lights'):
        return

    # Are we on Cooldown?
    if ON_COOLDOWN:
        if Config.cooldown_response:
            Parent.SendStreamMessage(Config.cooldown_response)
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

    # Does the User have permission to use it
    if subcommand_dict['subscriber'] and not Parent.HasPermission(data.User, 'subscriber', ''):
        return

    subcommand_func = globals()[subcommand]
    if subcommand_func(data):
        ON_COOLDOWN = True
        if Config.default_timeout:
            LAST_COMMAND_TIME = time.time()
            DEFAULTED = False
        callbacks.append((time.time() + Config.global_cooldown, reset_cd))


def Tick():
    global callbacks
    global DEFAULTED
    global LAST_COMMAND_TIME
    if not DEFAULTED and time.time() > LAST_COMMAND_TIME + Config.default_timeout:
        activate_scene(Config.default_scene)
        DEFAULTED = True
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
