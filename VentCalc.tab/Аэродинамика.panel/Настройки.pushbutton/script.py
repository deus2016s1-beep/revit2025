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
from System.Windows.Forms import Form, Label, TextBox, Button, DialogResult, FormStartPosition
from System.Drawing import Point, Size
from pyrevit import forms
from ventcalc import config


class SettingsForm(Form):
    def __init__(self, settings):
        self.Text = u'Настройки VentCalc'
        self.Size = Size(360, 230)
        self.StartPosition = FormStartPosition.CenterScreen
        self.inputs = {}
        rows = [
            ('air_density', u'Плотность воздуха, кг/м³'),
            ('reserve_percent', u'Запас, %'),
            ('friction_factor', u'Коэффициент трения')
        ]
        y = 20
        for key, caption in rows:
            label = Label()
            label.Text = caption
            label.Location = Point(12, y)
            label.Size = Size(190, 22)
            self.Controls.Add(label)
            box = TextBox()
            box.Text = str(settings.get(key, ''))
            box.Location = Point(210, y)
            box.Size = Size(100, 22)
            self.Controls.Add(box)
            self.inputs[key] = box
            y += 36
        ok = Button()
        ok.Text = 'OK'
        ok.Location = Point(145, 145)
        ok.DialogResult = DialogResult.OK
        cancel = Button()
        cancel.Text = u'Отмена'
        cancel.Location = Point(235, 145)
        cancel.DialogResult = DialogResult.Cancel
        self.Controls.Add(ok)
        self.Controls.Add(cancel)
        self.AcceptButton = ok
        self.CancelButton = cancel

    def result(self, settings):
        data = config.copy_dict(settings)
        for key in self.inputs:
            data[key] = config.to_float(self.inputs[key].Text, settings.get(key, 0.0))
        return data


def main():
    settings = config.load_settings(extension_root)
    form = SettingsForm(settings)
    if form.ShowDialog() != DialogResult.OK:
        return
    config.save_settings(form.result(settings), extension_root)
    forms.alert(u'Настройки сохранены')


main()
