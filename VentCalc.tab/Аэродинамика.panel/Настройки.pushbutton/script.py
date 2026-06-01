# -*- coding: utf-8 -*-
import os
import sys
import clr

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Windows.Forms import Form, Label, TextBox, Button, CheckBox, DialogResult, FormStartPosition
from System.Drawing import Point, Size
from pyrevit import forms
from ventcalc import config


class SettingsForm(Form):
    def __init__(self, settings):
        Form.__init__(self)
        self.Text = u'Настройки VentCalc'
        self.Size = Size(430, 260)
        self.StartPosition = FormStartPosition.CenterScreen
        self.inputs = {}
        self.checks = {}
        rows = [
            ('min_velocity', u'Минимальная скорость, м/с'),
            ('max_velocity', u'Максимальная скорость, м/с'),
            ('reserve_percent', u'Запас давления, %'),
            ('roughness_mm', u'Шероховатость, мм')
        ]
        y = 20
        for key, caption in rows:
            label = Label()
            label.Text = caption
            label.Location = Point(12, y)
            label.Size = Size(230, 22)
            self.Controls.Add(label)
            box = TextBox()
            box.Text = str(settings.get(key, ''))
            box.Location = Point(255, y)
            box.Size = Size(120, 22)
            self.Controls.Add(box)
            self.inputs[key] = box
            y += 36
        check = CheckBox()
        check.Text = u'Спрашивать перед созданием Excel'
        check.Location = Point(12, y)
        check.Size = Size(360, 24)
        check.Checked = config.to_bool(settings.get('ask_before_excel', True), True)
        self.Controls.Add(check)
        self.checks['ask_before_excel'] = check
        ok = Button()
        ok.Text = 'OK'
        ok.Location = Point(225, 190)
        ok.DialogResult = DialogResult.OK
        cancel = Button()
        cancel.Text = u'Отмена'
        cancel.Location = Point(315, 190)
        cancel.DialogResult = DialogResult.Cancel
        self.Controls.Add(ok)
        self.Controls.Add(cancel)
        self.AcceptButton = ok
        self.CancelButton = cancel

    def result(self, settings):
        data = config.copy_dict(settings)
        for key in self.inputs:
            data[key] = config.to_float(self.inputs[key].Text, settings.get(key, 0.0))
        for key in self.checks:
            data[key] = bool(self.checks[key].Checked)
        return data


def main():
    settings = config.load_settings(extension_root)
    form = SettingsForm(settings)
    if form.ShowDialog() != DialogResult.OK:
        return
    config.save_settings(form.result(settings), extension_root)
    forms.alert(u'Настройки сохранены')


main()
