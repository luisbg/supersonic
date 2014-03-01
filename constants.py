"""constants.py - Miscellaneous constants."""

import os


def get_home_directory():
    """On UNIX-like systems, this method will return the path of the home
    directory, e.g. /home/username.
    """
    return os.path.expanduser('~')


def get_config_directory():
    """Return the path to the supersonic config directory.

    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_CONFIG_HOME environmental variable.
    """
    base_path = os.getenv('XDG_CONFIG_HOME',
                          os.path.join(get_home_directory(), '.config'))
    return os.path.join(base_path, 'supersonic')


VERSION = '0.2'
HOME_DIR = get_home_directory()
CONFIG_DIR = get_config_directory()
