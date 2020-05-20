import codecs
import json


class ScriptSettings(object):
    SUBCOMMAND_PROPERTIES = [
        '_duration',
        '_cost',
        '_enabled',
        '_response',
    ]

    def __init__(self):
        self.subcommands = {}
        self.lifx_token = ''
        self.group = ''

    def load(self, settings_file):
        with codecs.open(settings_file, encoding='utf-8-sig', mode='r') as f:
            settings = json.load(f, encoding='utf-8')
        self.lifx_token = settings['api_token']
        self.group = settings['light_group']

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

        self.subcommands = subcommands
