# -*- coding: UTF-8 -*-

"""Text Editer from gae."""

# Author: Amir Gumerov
# Mail: ar8200@bk.ru

import configparser
import gettext
import importlib
import io
import os
import shutil
import string
import sys
import threading
import time
import webbrowser
import winsound
import zipfile

import clipboard
import iso639
import keyboard
import psutil
import requests
import wx.stc

import plugins

_ = None


class Tegae(wx.App):
    """main class."""

    def __init__(self, file_name=''):
        """Create instance of main class."""
        global _
        wx.App.__init__(self)
        self.SetAppName('Tegae++')
        self.start_time = time.localtime()
        self.user_config_dir = os.environ['APPDATA'] + '/Tegae/'
        with open(self.user_config_dir + '/errors.log', 'a') as f:
            f.write(
                f'{self.start_time.tm_year}.{self.start_time.tm_mon}.\
                    {self.start_time.tm_mday}.{self.start_time.tm_hour}.\
                        {self.start_time.tm_min}.{self.start_time.tm_sec}\
                            --- start\n'
            )
        self.errors = errors(self.user_config_dir + '/errors.log')
        # sys.stdout = self.errors.errors
        # sys.stderr = self.errors.errors
        self.user_config = configparser.ConfigParser()
        self.user_config.read(self.user_config_dir + '/tegae.ini')
        self.hotkeys = dict(self.user_config['hotkeys'])
        self.user_data = user_data(self.user_config)
        _ = gettext.translation(
            'Tegae++', 'locale', languages=[self.user_data.language]
        ).gettext
        if self.user_data.play_start_sound:
            threading.Thread(
                target=winsound.PlaySound,
                args=(
                    self.user_data.start_sound,
                    winsound.SND_FILENAME
                )
            ).start()
        if file_name != '':
            try:
                with open(file_name, 'r') as f:
                    self.file_text = f.read()
                self.file_name = file_name
            except UnicodeDecodeError:
                wx.MessageBox(
                    _('File is damaged or does not contain text'), _('Error')
                )
                sys.exit(1)
        else:
            self.file_name = 'new1' + self.user_data.default_extension
            self.file_text = ''
        self.Frame = Frame(self)
        for plugin in self.user_data.autostart_plugins:
            plugins.launch_plugin(self, plugin)
        self.MainLoop()

    def about_app(self):
        """Show information about application."""
        config = configparser.ConfigParser()
        config.read('data\\sys.ini')
        wx.MessageBox(
            f"{_('Summary')}: {config.get('info', 'summary')}\n\
                {_('Version')}: {config.get('info', 'version')}\n\
                    {_('Author')}: {config.get('info', 'author')}",
            _('About program')
        )

    def save_file(self):
        """
        Save file.

        if opened a new file, will be  offer to sellect path;
        if opened the file, this file will be update.
        """
        if self.file_name == 'new1' + self.user_data.default_extension:
            file_save_dialog = wx.  FileDialog(
                self.Frame, _('Saving'), self.user_data.path_by_default,
                'new1', style=wx.FD_SAVE
            )
            file_save_dialog.ShowModal()
            with open(file_save_dialog.GetPath(), 'w') as f:
                f.write(self.Frame.TextCtrl.GetValue())
            self.file_name = file_save_dialog.GetPath()
            self.file_text = self.Frame.TextCtrl.GetValue()
            self.Frame.SetLabel(self.file_name.split('\\')[-1] + '\nTegae++')
            self.Frame.update_status_text()
            file_save_dialog.Destroy()
        else:
            with open(self.file_name, 'w') as f:
                f.write(self.Frame.TextCtrl.GetValue())

    def open_file(self):
        file_open_dialog = wx.FileDialog(
            self.Frame, _('Opening'), '', '', '', style=wx.FD_OPEN
        )
        file_open_dialog.ShowModal()
        try:
            with open(file_open_dialog.GetPath(), 'r') as f:
                self.file_text = f.read()
            self.file_name = file_open_dialog.GetPath()
            self.Frame.SetLabel(self.file_name + '\nTegae++')
            self.Frame.update_status_text()
            self.Frame.TextCtrl.SetValue(self.file_text)
        except FileNotFoundError:
            pass
        except UnicodeDecodeError:
            wx.MessageBox(
                _('File is damaged or does not contain text'), _('Error')
            )
        file_open_dialog.Destroy()

    def save_how_file(self):
        if self.file_name == 'new1' + self.user_data.default_extension:
            file_save_dialog = wx.FileDialog(
                self.Frame, _('Saving'),
                self.user_data.path_by_default,
                'new1' + self.user_data.default_extension,
                style=wx.FD_SAVE
            )
        else:
            file_save_dialog = wx.FileDialog(
                self.Frame, _('Saving'),
                '\\'.join(self.file_name.split('\\')[0:-1]),
                self.file_name.split('\\')[-1],
                style=wx.FD_SAVE
            )
        file_save_dialog.ShowModal()
        with open(file_save_dialog.GetPath(), 'w') as f:
            f.write(self.Frame.TextCtrl.GetValue())
        file_save_dialog.Destroy()
        os.remove(self.file_name)
        sys.exit()


class user_data:
    def __init__(self, user_config):
        self.language = user_config.get('settings', 'language')
        self.play_start_sound = user_config.getboolean(
            'settings', 'play_start_sound'
        )
        self.start_sound = user_config.get('settings', 'start_sound')
        self.indent = user_config.get('edit', 'indent').split('"')[1]
        self.repeat_indent = user_config.getboolean('edit', 'repeat_indent')
        self.path_by_default = user_config.get('new file', 'path_by_default')
        self.default_extension = user_config.get(
            'new file', 'default_extension'
        )
        self.default_coding = user_config.get('new file', 'default_coding')
        self.launch_functions_list = user_config.get(
            'launch_functions', 'list'
        ).split('!')
        self.plugins_list = []
        for i in os.listdir('plugins'):
            if len(
                i.split('.')
            ) == 1 and i != '__pycache__' and i != '__init__.py':
                self.plugins_list.append(i)
        self.autostart_plugins = []
        for i in user_config.get('start', 'plugins').split('?'):
            if i != '':
                self.autostart_plugins.append(i)


class data:
    indents = ['	', '    ']
    langs = os.listdir('locale')
    codings = ['ANSI', 'UTF-8', 'Windows-1251']


class errors:
    def __init__(self, errors_log_file):
        self.errors = io.StringIO('')
        self.previous_errors = ''
        self.errors_log_file = errors_log_file
        threading.Thread(target=self.change_error).start()

    def change_error(self):
        while True:
            if self.errors.getvalue() != self.previous_errors:
                if self.previous_errors == '':
                    lpe = 0
                else:
                    lpe = len(self.previous_errors) - 1
                new_error = self.errors.getvalue()[lpe::]
                error_time = time.localtime()
                with open(self.errors_log_file, 'a') as ef:
                    ef.write(
                        f'{error_time.tm_year}.{error_time.tm_mon}.\
                            {error_time.tm_mday}.{error_time.tm_hour}.\
                                {error_time.tm_min}.{error_time.tm_sec} --- \
                            {new_error}'
                    )
                winsound.PlaySound(
                    'data\\sounds\\error.wav', winsound.SND_FILENAME
                )
                wx.MessageBox(new_error, _('Error'))
                self.previous_errors = self.errors.getvalue()


class Frame(wx.Frame):
    def __init__(self, tegae):
        self.Tegae = tegae
        self.XY = wx.GetDisplaySize()
        wx.Frame.__init__(
            self, None, -1, self.Tegae.file_name.split('\\')[-1] + '\nTegae++',
            size=(self.XY.GetWidth(), self.XY.GetHeight() - 35)
        )
        self.SetMenuBar(MenuBar(self.Tegae))
        self.CreateStatusBar()
        self.Bind(wx.EVT_CLOSE, lambda evt: self.frame_close())
        self.TextCtrl = TextCtrl(self.Tegae, self)
        self.Show()
        self.Center()

    def frame_close(self):
        if self.TextCtrl.GetValue() == self.Tegae.file_text:
            self.Tegae.Destroy()
        else:
            save_dialog = wx.Dialog(self, -1, _('Save?'))
            save_button = wx.Button(save_dialog, -1, _('Save'))
            save_button.Bind(
                wx.EVT_BUTTON, lambda evt: (
                    self.Tegae.save_file(),
                    sys.exit(0)
                )
            )
            no_button = wx.Button(save_dialog, -1, _('No'))
            no_button.Bind(
                wx.EVT_BUTTON, lambda evt: sys.exit(0)
            )
            save_dialog.ShowModal()

    def update_status_text(self):
        self.SetStatusText(
            f'''{self.Tegae.file_name.split( '.')[0]} {_('file')}
            '''
        )


class MenuBar(wx.MenuBar):
    def __init__(self, tegae):
        wx.MenuBar.__init__(self)
        self.Tegae = tegae
        file_menu = wx.Menu()
        new_file_item = file_menu.Append(
            -1, _('New file') + '\t' + self.Tegae.hotkeys['id1_1']
        )
        open_file_item = file_menu.Append(
            2, _('Open') + '\t' + self.Tegae.hotkeys['id1_2']
        )
        file_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.open_file(), open_file_item
        )
        open_menu = wx.Menu()
        open_file_by_url_item = open_menu.Append(
            -1, _('Open file by link') + '\t' + self.Tegae.hotkeys['id1_3_1']
        )
        open_menu.Bind(
            wx.EVT_MENU, lambda evt: self.open_file_by_url(),
            open_file_by_url_item
        )
        file_menu.AppendSubMenu(open_menu, _('Open'))
        save_file_item = file_menu.Append(
            1, _('Save') + '\t' + self.Tegae.hotkeys['id1_4']
        )
        file_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.save_file(), save_file_item
        )
        save_how_file_item = file_menu.Append(
            3, _('Save as') + '\t' + self.Tegae.hotkeys['id1_5']
        )
        file_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.save_how_file(),
            save_how_file_item
        )
        print_file_item = file_menu.Append(
            -1, _('Print') + '\t' + self.Tegae.hotkeys['id1_6']
        )
        self.Append(file_menu, _('File'))
        edit_menu = wx.Menu()
        indent_menu = wx.Menu()
        add_indent_item = indent_menu.Append(
            -1, _('Insert tab') + '\t' + self.Tegae.hotkeys['id2_1_1']
        )
        indent_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.Frame.TextCtrl.WriteText(
                self.Tegae.user_data.indent
            ),
            add_indent_item
        )
        del_indent_item = indent_menu.Append(
            -1, _('Delete tab') + '\t' + self.Tegae.hotkeys['id2_1_2']
        )
        indent_menu.Bind(
            wx.EVT_MENU, lambda evt: self.del_indent(), del_indent_item
        )
        edit_menu.AppendSubMenu(indent_menu, _('Indent'))
        comment_menu = wx.Menu()
        comment_on_item = comment_menu.Append(
            -1, _('Comment out a line') + '\t' + self.Tegae.hotkeys['id2_2_1']
        )
        comment_off_item = comment_menu.Append(
            -1, _('Uncomment the line') + '\t' + self.Tegae.hotkeys['id2_2_2']
        )
        edit_menu.AppendSubMenu(comment_menu, _('Commenting'))
        find_menu = wx.Menu()
        find_item = find_menu.Append(
            -1, _('Search') + '\t' + self.Tegae.hotkeys['id2_3_1']
        )
        find_next_item = find_menu.Append(
            -1, _('Search further') + '\t' + self.Tegae.hotkeys['id2_3_2']
        )
        find_previous_item = find_menu.Append(
            -1, _('Search earlier') + '\t' + self.Tegae.hotkeys['id2_3_3']
        )
        edit_menu.AppendSubMenu(find_menu, _('Search'))
        go_to_item = edit_menu.Append(
            -1, _('Go To') + '\t' + self.Tegae.hotkeys['id2_4']
        )
        edit_menu.Bind(wx.EVT_MENU, lambda evt: self.go_to(), go_to_item)
        self.Append(edit_menu, _('Edit'))
        launch_menu = wx.Menu()
        self.Append(launch_menu, _('Launch'))
        self.launch_functions()
        plugin_menu = wx.Menu()
        self.Append(plugin_menu, _('Plugins'))
        self.plugins()
        options_menu = wx.Menu()
        settings_item = options_menu.Append(
            -1, _('Settings') + '\t' + self.Tegae.hotkeys['id5_1']
        )
        settings_item.SetBitmap(
            wx.Bitmap('data\\icons\\settings.png', wx.BITMAP_TYPE_PNG)
        )
        options_menu.Bind(
            wx.EVT_MENU, lambda evt: Settings(self.Tegae), settings_item
        )
        blok_text_entry_item = options_menu.Append(
            -1, _(
                'Block / Unblock text input'
            ) + '\t' + self.Tegae.hotkeys['id5_2']
        )
        options_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.Frame.TextCtrl.SetEditable(
                not self.Tegae.Frame.TextCtrl.IsEditable()
            ),
            blok_text_entry_item
        )
        help_item = options_menu.Append(
            -1, _('Help') + '\t' + self.Tegae.hotkeys['id5_3']
        )
        options_menu.Bind(
            wx.EVT_MENU, lambda evt: webbrowser.open(
                f"https://gumerov-amir.github.io/Tegae/{self.Tegae.user_data.language}.html"
            ),
            help_item
        )
        about_app_item = options_menu.Append(-1, _('About program'))
        options_menu.Bind(
            wx.EVT_MENU, lambda evt: self.Tegae.about_app(), about_app_item
        )
        hide_tree_item = options_menu.Append(-1, _('Hide to background'))
        options_menu.Bind(wx.EVT_MENU, self.hide_frame, hide_tree_item)
        self.Append(options_menu, _('Options'))

    def open_file_by_url(self):
        text_dialog = wx.TextEntryDialog(
            self.frame, _('Link'), _('Open file by link')
        )
        if text_dialog.ShowModal() == wx.ID_OK:
            try:
                text = requests.get(text_dialog.GetValue()).text
                self.Tegae.file_name = text_dialog.GetValue()
                self.frame.SetLabel(file_name + '\nTegae++')
                self.Tegae.Frame.TextCtrl.SetValue(text)
                self.update_status_text()
            except Exception as error:
                wx.MessageBox(str(error), _('Error'))
        else:
            text_dialog.Destroy()

    def del_indent(self):
        point = self.Tegae.Frame.TextCtrl.GetInsertionPoint()
        if self.Tegae.Frame.TextCtrl.GetValue()[point - 4:point] == '    ':
            self.Tegae.Frame.TextCtrl.Remove(point - 4, point)

    def go_to(self):
        go_to_dialog = wx.Dialog(
            self.frame, -1, _('Go To'), pos=(0, 0), size=(
                self.XY.GetWidth(), self.XY.GetHeight()
            )
        )
        string_or_letter_radiobox = wx.RadioBox(
            go_to_dialog, -1, choices=[_('String'), _('Character')],
            pos=(0, 0), size=(150, 70)
        )
        string_or_letter_radiobox.SetSelection(0)
        number_of_string_or_letter_textctrl = wx.TextCtrl(
            go_to_dialog, -1, style=wx.TE_PROCESS_ENTER, pos=(150, 0),
            size=(150, 70)
        )
        number_of_string_or_letter_textctrl.Bind(
            wx.EVT_TEXT_ENTER, lambda evt: self.go(
                evt, string_or_letter_radiobox.GetSelection(),
                int(number_of_string_or_letter_textctrl.GetValue())
            )
        )
        number_of_string_or_letter_textctrl.SetFocus()
        go_button = wx.Button(
            go_to_dialog, -1, _('Forward'), pos=(300, 0),
            size=(150, 70)
        )
        go_button.Bind(
            wx.EVT_BUTTON,
            lambda evt: self.go(
                evt, string_or_letter_radiobox.GetSelection(),
                int(number_of_string_or_letter_textctrl.GetValue())
            )
        )
        cancel_button = wx.Button(
            go_to_dialog, -1, _('Cancel'), pos=(450, 0), size=(150, 70)
        )
        cancel_button.Bind(wx.EVT_BUTTON, lambda evt: go_to_dialog.Destroy())
        go_to_dialog.ShowModal()

    def go(self, evt, element, number):
        if element == 0:
            self.Tegae.Frame.TextCtrl.SetInsertionPoint(
                self.Tegae.Frame.TextCtrl.XYToPosition(0, number - 1)
            )
        elif element == 1:
            self.Tegae.Frame.TextCtrl.SetInsertionPoint(number)
        evt.GetEventObject().GetParent().Destroy()

    def launch_functions(self):
        menu = self.GetMenu(2)
        if self.Tegae.user_data.launch_functions_list != ['']:
            for id_, function in enumerate(
                self.Tegae.user_data.launch_functions_list
            ):
                if function != '':
                    menu.Bind(
                        wx.EVT_MENU, self.start_launch_function,
                        menu.Append(id_, function)
                    )

    def start_launch_function(self, evt):
        todo = self.Tegae.user_data.launch_functions_list[
            evt.GetId()
        ].split('\t')[0]
        if '$file_name' in todo:
            todo = string.Template(todo).substitute(file_name=file_name)
        try:
            threading.Thread(target=lambda: os.system(todo)).start()
        except Exception as e:
            wx.MessageBox(e, 'error')

    def plugins(self):
        menu = self.GetMenu(3)
        for i, j in enumerate(self.Tegae.user_data.plugins_list):
            if j in self.Tegae.hotkeys.keys():
                j += '\t' + self.Tegae.hotkeys[j]
            menu.Bind(
                wx.EVT_MENU, lambda evt: plugins.launch_plugin(
                    self.Tegae,
                    self.Tegae.user_data.plugins_list[evt.GetId() - 5]
                ),
                menu.Append(i + 5, j)
            )

    def plugins_launch(self, evt):
        name = self.Tegae.user_data.plugins_list[evt.GetId() - 5]
        plugin = importlib.import_module(f'plugins.{name}.__init__')
        plugin.__builtins__ = {**globals(), **plugin.__builtins__}
        plugin.main()

    def hide_frame(self, evt=None):
        self.Tegae.Frame.Hide()
        keyboard.wait(self.Tegae.hotkeys['id11_1'])
        self.Tegae.Frame.Show()


class TextCtrl(wx.stc.StyledTextCtrl):

    def __init__(self, tegae, frame):
        wx.stc.StyledTextCtrl.__init__(
            self, frame, 13,
            pos=(0, frame.XY.GetHeight() // 10),
            size=(frame.XY.GetWidth(), int(frame.XY.GetHeight() * 0.9)),
            style=wx.TE_MULTILINE,
        )
        self.Tegae = tegae
        self.SetValue(self.Tegae.file_text)
        self.SetLabel(_('Editor'))
        self.Bind(
            wx.stc.EVT_STC_UPDATEUI,
            lambda evt: self.Tegae.Frame.update_status_text
        )
        self.Bind(
            wx.EVT_NAVIGATION_KEY, lambda evt: self.renovating_status_text
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, lambda evt: self.new_line_in_user_text()
        )
        self.Bind(
            wx.EVT_CONTEXT_MENU,
            lambda evt: self.PopupMenu(PopupMenu(self))
        )

    def new_line_in_user_text(self):
        if self.Tegae.user_data.repeat_indent:
            previous_string = self.GetLineText(
                self.PositionToXY(
                    self.GetInsertionPoint()
                )[2])
            indent_of_new_line = ''
            for char in previous_string:
                if char == ' ' or char == '	':
                    indent_of_new_line += char
                else:
                    break
            if indent_of_new_line != '':
                self.WriteText('\n' + indent_of_new_line)


class PopupMenu(wx.Menu):
    def __init__(self, text_ctrl):
        wx.Menu.__init__(self)
        self.paste_item = self.Append(-1, _('Paste'))
        self.Bind(
            wx.EVT_MENU,
            lambda evt: text_ctrl.WriteText(
                clipboard.paste().encode().decode()
            ),
            self.paste_item
        )


class Settings(wx.Dialog):
    def __init__(self, tegae):
        self.Tegae = tegae
        wx.Dialog.__init__(
            self, self.Tegae.Frame, -1, _('Settings'), pos=(0, 0), size=(
                self.Tegae.Frame.XY.GetWidth(),
                self.Tegae.Frame.XY.GetHeight() - 35
            )
        )
        self.Panel = ''
        departments_list = wx.ListBox(
            self, -1, choices=[
                _('General'), _('Edit'), _('New file'), _('Launch'),
                _('Plugins')
            ]
        )
        departments_list.Bind(
            wx.EVT_LISTBOX, self.create_settings_panel
        )
        departments_list.SetSelection(0)
        button_close = wx.Button(
            self, -1, _('Close'),
            pos=(int(self.Tegae.Frame.XY.GetWidth() * 0.9), 0),
            size=(
                int(self.Tegae.Frame.XY.GetWidth() * 0.05),
                int(self.Tegae.Frame.XY.GetHeight() * 0.05)
            )
        )
        # button_close.Bind(
        # wx.EVT_BUTTON, lambda evt: self.settings_dialog.Destroy()
        # )
        self.create_settings_panel(0)
        self.Show()
        self.Center()

    def create_settings_panel(self, evt):
        if type(evt) == wx._core.CommandEvent:
            department = evt.GetSelection()
        elif type(evt) == int:
            department = evt
        if self.Panel != '':
            try:
                self.Panel.Destroy()
            except Exception:
                self.Panel = ''
        if department == 0:
            self.Panel = GeneralSettings(self.Tegae, self)
        elif department == 1:
            self.Panel = EditSettings(self.Tegae, self)
        elif department == 2:
            self.Panel = NewFileSettings(self.Tegae, self)
        elif department == 3:
            self.Panel = launchSettings(self.Tegae, self)
        elif department == 4:
            self.Panel = PluginsSettings(self.Tegae, self)


class GeneralSettings(wx.Panel):
    def __init__(self, tegae, settings):
        self.Tegae = tegae
        wx.Panel.__init__(
            self, settings, -1, pos=(135, 0), size=(
                int(self.Tegae.Frame.XY.GetWidth() * 0.95),
                self.Tegae.Frame.XY.GetHeight()
            )
        )
        wx.StaticText(
            self, -1, _(
                'Language (changes will take effect after restarting app)'
            ),
            pos=(0, 0)
        )
        langs_combobox = wx.ComboBox(
            self, -1, choices=[
                f"{iso639.to_name(i)}; {iso639.to_native(i)}"
                for i in data.langs
            ],
            pos=(0, 17), style=wx.CB_READONLY
        )
        langs_combobox.SetSelection(
            data.langs.index(
                iso639.to_iso639_2(self.Tegae.user_data.language)
            )
        )
        langs_combobox.Bind(wx.EVT_COMBOBOX, self.change_language)
        play_start_sound_checkbox = wx.CheckBox(
            self, 1, _('Play sound when the program starts'),
            pos=(0, 40)
        )
        play_start_sound_checkbox.SetValue(
            self.Tegae.user_data.play_start_sound
        )
        play_start_sound_checkbox.Bind(
            wx.EVT_CHECKBOX,
            self.change_starting_sound
        )
        wx.StaticText(self, -1, _('File Path'), pos=(260, 40))
        start_sound_textctrl = wx.TextCtrl(
            self, 2,
            self.Tegae.user_data.start_sound, pos=(260, 57), size=(300, 30)
        )
        start_sound_textctrl.Bind(
            wx.EVT_TEXT, self.change_starting_sound
        )
        brows_sound_button = wx.Button(
            self, 3, _('Overview'), pos=(560, 57), size=(60, 30)
        )
        brows_sound_button.Bind(
            wx.EVT_BUTTON, self.change_starting_sound
        )

    def change_language(self, evt):
        self.Tegae.user_config.set(
            'settings', 'language',
            data.langs[evt.GetSelection()]
        )
        with open(self.Tegae.user_config_dir + '\\tegae.ini', 'w') as f:
            self.Tegae.user_config.write(f)


    def change_starting_sound(self, evt):
        id_ = evt.GetId()
        if id_ == 1:
            config.set('settings', 'play_start_sound', str(evt.IsChecked()))
            with open(config_file, 'w') as f:
                config.write(f)
        elif id_ == 2:
            config.set('settings', 'start_sound', evt.GetString())
            with open(config_file, 'w') as f:
                config.write(f)
        elif id_ == 3:
            file_dialog = wx.FileDialog(
                self, '', '', '', style=(wx.FD_OPEN)
            )
            file_dialog.ShowModal()
            evt.SetString(file_dialog.GetPath())
            config.set(
                'settings', 'start_sound', file_dialog.GetPath()
            )
            with open(config_file, 'w') as f:
                config.write(f)


class EditSettings(wx.Panel):
    def __init__(self, tegae, settings):
        self.Tegae = tegae
        wx.Panel.__init__(
            self, settings, -1, pos=(135, 0), size=(
                int(self.Tegae.Frame.XY.GetWidth() * 0.95),
                self.Tegae.Frame.XY.GetHeight()
            )
        )
        wx.StaticText(self, -1, _('tab character'), pos=(0, 0))
        indents_listbox = wx.ListBox(
            self, 1, choices=[_('Tab'), _('4 spaces')], pos=(0, 20)
        )
        indents_listbox.SetSelection(
            data.indents.index(self.Tegae.user_data.indent)
        )
        indents_listbox.Bind(wx.EVT_LISTBOX, self.change_info_for_editing)
        repeat_indent_checkbox = wx.CheckBox(
            self, 2, _('Repeat indent the previous line'),
            pos=(150, 20)
        )
        repeat_indent_checkbox.SetValue(
            self.Tegae.user_data.repeat_indent
        )
        repeat_indent_checkbox.Bind(
            wx.EVT_CHECKBOX, self.change_info_for_editing
        )

    def change_info_for_editing(self, evt):
        id_ = evt.GetId()
        if id_ == 1:
            indent = data.indents[evt.GetSelection()]
            config.set('edit', 'indent', f'"{indent}"')
            with open(config_file, 'w') as f:
                config.write(f)
        elif id_ == 2:
            repeat_indent = evt.IsChecked()
            config.set('edit', 'repeat_indent', str(repeat_indent))
            with open(config_file, 'w') as f:
                config.write(f)


class NewFileSettings(wx.Panel):
    def __init__(self, tegae, settings):
        self.Tegae = tegae
        wx.Panel.__init__(
            self, settings, -1, pos=(135, 0),
            size=(
                self.Tegae.Frame.XY.GetWidth() * 0.95,
                self.Tegae.Frame.XY.GetHeight()
            )
        )
        wx.StaticText(self, -1, _('The default path'), pos=(0, 0))
        path_by_default_textctrl = wx.TextCtrl(
            self, -1, self.Tegae.user_data.path_by_default,
            pos=(0, 20)
        )
        path_by_default_textctrl.Bind(
            wx.EVT_TEXT, lambda evt: change_default_info_for_new_file(
                evt, 'pbdfnf'
            )
        )
        wx.StaticText(
            self, -1, _('Extension by default'), pos=(150, 0)
        )
        default_extension_textctrl = wx.TextCtrl(
            self, -1, self.Tegae.user_data.default_extension,
            pos=(150, 20)
        )
        default_extension_textctrl.Bind(
            wx.EVT_TEXT, lambda evt: self.change_default_info_for_new_file(
                evt, 'defnf'
            )
        )
        wx.StaticText(
            self, -1, _('Encoding by default'), pos=(300, 0)
        )
        default_coding_listbox = wx.ListBox(
            self, -1, choices=data.codings, pos=(300, 20)
        )
        default_coding_listbox.SetSelection(
            data.codings.index(self.Tegae.user_data.default_coding)
        )
        default_coding_listbox.Bind(
            wx.EVT_LISTBOX, lambda evt: change_default_info_for_new_file(
                evt, 'dcfnf'
            )
        )

    def change_default_info_for_new_file(evt, name):
        global file_name, path_by_default, default_extension, default_coding
        if name == 'pbdfnf':
            path_by_default = evt.GetString()
            config.set('new file', 'path_by_default', path_by_default)
            with open(config_file, 'w') as f:
                config.write(f)
        elif name == 'defnf':
            if file_name == 'new1' + default_extension:
                file_name = 'new1' + evt.GetString()
                frame.SetLabel(file_name + '\nTegae++')
            default_extension = evt.GetString()
            config.set('new file', 'default_extension', default_extension)
            with open(config_file, 'w') as f:
                config.write(f)
        elif name == 'dcfnf':
            default_coding = data.codings[evt.GetSelection()]
            config.set('new file', 'default_coding', default_coding)
            with open(config_file, 'w') as f:
                config.write(f)


class LaunchSettings(wx.Panel):
    def __init__(self, tegae, settings):
        self.Tegae = tegae
        wx.Panel.__init__(
            self, settings, -1, pos=(135, 0), size=(
                self.Tegae.Frame.XY.GetWidth() * 0.95,
                self.Tegae.Frame.XY.GetHeight()
            )
        )
        wx.StaticText(
            self, -1,
            _('(Changes will take effect after restarting app)'),
            pos=(0, 0)
        )
        y2 = 20
        if self.Tegae.user_data.launch_functions_list != ['']:
            for i, j in enumerate(
                self.Tegae.user_data.launch_functions_list
            ):
                if j == '':
                    continue
                wx.StaticText(self, -1, _('Action'), pos=(0, y2))
                wx.TextCtrl(
                    self, i, j.split('\t')[0], pos=(0, y2 + 20)
                ).Bind(
                    wx.EVT_TEXT, lambda evt: self.change_launch_functions(
                        evt, 'tdsf'
                    )
                )
                wx.StaticText(
                    self, -1, _('Combination'), pos=(150, y2)
                )
                wx.TextCtrl(
                    self, i, j.split('\t')[1], pos=(150, y2 + 20)
                ).Bind(
                    wx.EVT_TEXT, lambda evt: self.change_launch_functions(
                        evt, 'hksf'
                    )
                )
                wx.Button(
                    self, i, _('Delete'), pos=(300, y2 + 20)
                ).Bind(
                    wx.EVT_BUTTON,
                    lambda evt: self.change_launch_functions(
                        evt, 'dsf'
                    )
                )
                y2 += 70
        wx.StaticText(
            self, -1, _('New'), pos=(
                0, self.Tegae.Frame.XY.GetHeight() - 70
            )
        )
        wx.StaticText(
            self, -1, _('Action'), pos=(
                0, self.Tegae.Frame.XY.GetHeight() - 50
            )
        )
        todo_textctrl = wx.TextCtrl(
            self, -1, pos=(
                0, self.Tegae.Frame.XY.GetHeight() - 30
            )
        )
        wx.StaticText(
            self, -1, _('Combination'), pos=(
                150, self.Tegae.Frame.XY.GetHeight() - 50
            )
        )
        hotkey_textctrl = wx.TextCtrl(
            self, -1, pos=(
                150, self.Tegae.Frame.XY.GetHeight() - 30
            )
        )
        add_button = wx.Button(
            self, -1, _('Add'), pos=(
                300, self.Tegae.Frame.XY.GetHeight() - 30
            )
        )
        add_button.Bind(
            wx.EVT_BUTTON, lambda evt: change_launch_functions(
                evt, 'nsf', todo_textctrl.GetValue(),
                hotkey_textctrl.GetValue()
            )
        )

    def change_launch_functions(evt, name, ntdsf=None, nhksf=None):
        id_ = evt.GetId()
        if name == 'tdsf':
            launch_functions_list[id_] = evt.GetString() + '\t' + \
                launch_functions_list[id].split('\t')[1]
            config.set(
                'launch_functions', 'list', '?'.join(launch_functions_list)
            )
            with open(config_file, 'w') as f:
                config.write(f)
        elif name == 'hksf':
            launch_functions_list[id] = launch_functions_list[id_].split(
                '\t'
            )[0] + '\t' + evt.GetString()
            config.set(
                'launch_functions', 'list', '?'.join(launch_functions_list)
            )
            with open(config_file, 'w') as f:
                config.write(f)
        elif name == 'dsf':
            launch_functions_list.pop(id)
            config.set(
                'launch_functions', 'list', '?'.join(launch_functions_list)
            )
            with open(config_file, 'w') as f:
                config.write(f)
            create_panel_department_settings(3)
        elif name == 'nsf':
            if nhksf == '' or ntdsf == '':
                wx.MessageBox(
                    _('You must enter action and combination'),
                    _('Error')
                )
                return
            if '+'.join(
                [i.title() for i in nhksf.split('+')]
            ) in hotkeys.values():
                wx.MessageBox(_('This combination is busy'), _('Error'))
                return
            launch_functions_list.append(
                ntdsf + '\t' + '+'.join(
                    [i.title() for i in nhksf.split('+')]
                )
            )
            config.set(
                'launch_functions', 'list', '?'.join(launch_functions_list)
            )
            with open(config_file, 'w') as f:
                config.write(f)
            create_panel_department_settings(3)


class PluginsSettings(wx.Panel):
    def __init__(self, tegae, settings):
        self.Tegae = tegae
        if len(self.Tegae.user_data.plugins_list) > 0:
            wx.Panel.__init__(
                self, settings, -1, pos=(135, 0), size=(
                    self.Tegae.Frame.XY.GetWidth() * 0.95,
                    self.Tegae.Frame.XY.GetHeight()
                )
            )
            plugins_listbox = wx.ListBox(
                self, -1, choices=self.Tegae.user_data.plugins_list,
                pos=(0, 0)
            )
            wx.StaticText(self, -1, _('Summary'), pos=(150, 0))
            summary = wx.TextCtrl(
                self, -1, '', pos=(150, 50), size=(500, 80),
                style=(wx.TE_READONLY)
            )
            wx.StaticText(self, -1, _('Author'), pos=(650, 0))
            author = wx.TextCtrl(
                self, -1, '', pos=(650, 50), size=(150, 80),
                style=(wx.TE_READONLY)
            )
            wx.StaticText(self, -1, _('Version'), pos=(800, 0))
            version = wx.TextCtrl(
                self, -1, '', pos=(800, 50), size=(150, 80),
                style=wx.TE_READONLY
            )
            autostart = wx.CheckBox(
                self, -1, _('Auto start'), pos=(950, 0)
            )
            autostart.Bind(
                wx.EVT_CHECKBOX,
                lambda evt: self.change_autostart_for_plugin(
                    plugins_listbox.GetSelection(), autostart.GetValue()
                )
            )
            del_plugin_button = wx.Button(
                self, -1, _('Delete'), pos=(1100, 50)
            )
            del_plugin_button.Bind(
                wx.EVT_BUTTON, lambda evt: self.del_plugin(
                    plugins_listbox.GetSelection()
                )
            )
            plugins_listbox.Bind(
                wx.EVT_LISTBOX, lambda evt: self.info_of_plugin(
                    plugins_listbox.GetSelection(), summary, author,
                    version, autostart
                )
            )
            plugins_listbox.SetSelection(0)
            self.info_of_plugin(0, summary, author, version, autostart)
        elif len(self.Tegae.user_data.plugins_list) == 0:
            wx.StaticText(
                settings, -1,
                _('You don\'t have plugins'),
                pos=(0, 0)
            )

    def info_of_plugin(self, number, summary, author, version, autostart):
        plugin_config = configparser.ConfigParser()
        plugin_config.read(
            'plugins\\' + self.Tegae.user_data.plugins_list[number] + '.ini'
        )
        summary.SetValue(plugin_config.get('info', 'summary'))
        author.SetValue(plugin_config.get('info', 'author'))
        version.SetValue(plugin_config.get('info', 'version'))
        autostart.SetValue(plugin_config.getboolean('system', 'autostart'))

    def change_autostart_for_plugin(self, number, value):
        plugin_config = configparser.ConfigParser()
        plugin_config.read(
            'plugins\\' + self.Tegae.user_data.plugins_list[number] + '.ini'
        )
        plugin_config.set('system', 'autostart', str(value))
        with open(
            'plugins\\' + self.Tegae.user_data.plugins_list[number] + '.ini',
            'w'
        ) as f:
            plugin_config.write(f)
        if not value:
            self.Tegae.user_data.autostart_plugins.pop(number)
            self.Tegae.user_config.set('start', 'plugins', '?'.join(
                self.Tegae.user_data.autostart_plugins
            ) + '?')
            with open(self.Tegae.user_config_dir + '\\tegae.ini', 'w') as f:
                self.Tegae.user_config.write(f)
        elif value:
            self.Tegae.user_data.autostart_plugins.append(
                self.Tegae.user_data.plugins_list[number]
            )
            self.Tegae.user_config.set('start', 'plugins', '?'.join(
                self.Tegae.user_data.autostart_plugins
            ) + '?')
            with open(self.Tegae.user_config_dir + '\\tegae.ini', 'w') as f:
                self.Tegae.user_config.write(f)


if __name__ == '__main__':
    Tegae()
