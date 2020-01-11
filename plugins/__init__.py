from . import *

import configparser
import gettext
import importlib
import os
import wx
import zipfile

def install_plugin(file):
    """install plugin."""
    plugin_name = file.split('\\')[-1][0:-4]
    user_config_path = os.environ['APPDATA'] + '/Tegae/tegae.ini'
    user_config = configparser.ConfigParser()
    user_config.read(user_config_path)
    _ = gettext.translation('Tegae++', 'locale', languages=[
        user_config.get('settings', 'language')
    ]).gettext
    plugin_zipfile = zipfile.ZipFile(file)
    plugin_config = configparser.ConfigParser()
    plugin_config.read_string(
        plugin_zipfile.read(plugin_name + '/' + plugin_name + '.ini').decode('utf-8')
    )
    app = wx.App()
    if wx.MessageBox(
        _('Do you want to install ') + plugin_name + '?\n' + \
        _('Summary: ') + plugin_config.get('info', 'summary') + \
        _('Author: ') + plugin_config.get('info', 'author') + \
        _('Version: ') + plugin_config.get('info', 'version'),
        _('attention'), style=wx.CANCEL
    ) == wx.OK:
        plugin_zipfile.extractall()
        plugin_zipfile.close()
        os.rename(
            plugin_name + '\\' + plugin_name + '.py',
            'plugins\\' + plugin_name + '.py'
        )
        os.rename(
            plugin_name + '\\' + plugin_name + '.ini',
            'plugins\\' + plugin_name + '.ini'
        )
        os.rmdir(plugin_name)
        if plugin_config.getboolean('system', 'autostart'):
            autostart_plugins = []
            for i in user_config.get('start', 'plugins').split('?'):
                if i != '':
                    autostart_plugins.append(i)
            autostart_plugins.append(plugin_name)
            user_config.set(
                'start', 'plugins', '?'.join(autostart_plugins) + '?'
            )
            with open(user_config_path, 'w') as f:
                user_config.write(f)

def launch_plugin(Tegae, plugin_name):
    PluginTegae = type('PluginTegae', (), {'Tegae': 'Tegae'})
    plugin = importlib.import_module(plugin_name, plugin_name)
    plugin.launch(PluginTegae)