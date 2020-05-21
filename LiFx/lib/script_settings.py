import codecs
import json


class ScriptSettings(object):
    SUBCOMMAND_PROPERTIES = [
        '_duration',
        '_cost',
        '_enabled',
        '_response',
        '_subscriber',
        '_groups',
    ]
    LIFX_COLORS = ['white', 'red', 'orange', 'yellow', 'cyan', 'green', 'blue', 'purple', 'pink']

    def __init__(self):
        self.subcommands = {}
        self.lifx_token = ''
        self.global_cooldown = 0
        self.cooldown_response = ''
        self.default_scene = ''
        self.default_timeout = 0
        self.settings = {}
        self.custom_colors = {}

    def load(self, settings_file):
        with codecs.open(settings_file, encoding='utf-8-sig', mode='r') as f:
            settings = json.load(f, encoding='utf-8')
        self.lifx_token = settings['api_token']
        self.global_cooldown = settings['global_cooldown']
        self.cooldown_response = settings['cooldown_message']
        self.default_scene = settings['default_scene']
        self.default_timeout = settings['default_timeout']

        subcommands = {}
        for k, v in settings.items():
            is_subcommand_property = any([
                prop in k
                for prop in self.SUBCOMMAND_PROPERTIES
            ])
            if is_subcommand_property:
                subcommand, property = k.split('_')
                if not subcommand in subcommands:
                    subcommands[subcommand] = {}
                subcommands[subcommand][property] = v

            elif k.startswith('custom') and v:
                __, _id = k.split('_')
                value_key = 'color_' + str(_id)
                self.custom_colors[v.lower()] = settings[value_key]

        self.subcommands = subcommands
        self.settings = settings

    def save(self, settings_file):
        with codecs.open(settings_file, encoding='utf-8-sig', mode='r') as f:
            settings = json.dumps(self.settings, indent=True, encoding='utf-8')
            f.write(settings)
