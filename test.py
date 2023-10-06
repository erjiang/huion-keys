import yaml
import os

CONFIG_FILE_PATH = os.path.expanduser(os.path.join(
                os.getenv('XDG_CONFIG_HOME', default='~/.config'), 'huion_keys.conf'))

CONFIG = yaml.load(open(CONFIG_FILE_PATH, 'r'), yaml.Loader)

for binding in CONFIG['Bindings']: 
  print(type(binding) is int)