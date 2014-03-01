"""config.py - Config handler."""

import os
import ConfigParser

import constants

# All the configurations are stored here.
prefs = {
    # defaults
    'gtk-application-prefer-dark-theme': True,

    'url': "http://127.0.0.1:8080",
    'authurl': "/auth/v1.0",
    'user': "guest",
    'key': "password",
    'temp_url_key': "b3968d0207b54ece87cccc06515a89d4",
    'dbc': "Index",      # database container
    'dbo': "music.db"   # database object
}

_config_path = os.path.join(constants.CONFIG_DIR, 'config')


def read_config_file():
    """Read preferences data from disk."""
    if os.path.isfile(_config_path):
        global prefs
        config = ConfigParser.ConfigParser()
        config.read(_config_path)

        prefs['url'] = config.get('Swift', 'url')
        prefs['authurl'] = config.get('Swift', 'authurl')
        prefs['user'] = config.get('Swift', 'user')
        prefs['key'] = config.get('Swift', 'key')
        prefs['temp_url_key'] = config.get('Swift', 'temp_url_key')
        prefs['dbc'] = config.get('Swift', 'dbc')
        prefs['dbo'] = config.get('Swift', 'dbo')


# def write_preferences_file():
#     """Write preference data to disk."""
#     config = open(_config_path, 'wb')
#     cPickle.dump(constants.VERSION, config, cPickle.HIGHEST_PROTOCOL)
#     cPickle.dump(prefs, config, cPickle.HIGHEST_PROTOCOL)
#     config.close()
