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
import Autodesk.Revit.DB as DB
from pyrevit import revit, forms
from ventcalc import config
from ventcalc import graphics
from ventcalc import revit_utils


class SpeedForm(Form):
    def __init__(self, settings):
        Form.__init__(self)
        self.Text = u'Подсветка скоростей'
        self.Size = Size(360, 190)
        self.StartPosition = FormStartPosition.CenterScreen
        label_min = Label()
        label_min.Text = u'Минимальная скорость, м/с'
        label_min.Location = Point(12, 20)
        label_min.Size = Size(190, 22)
        self.Controls.Add(label_min)
        self.min_box = TextBox()
        self.min_box.Text = str(settings.get('min_velocity', 3.0))
        self.min_box.Location = Point(220, 20)
        self.min_box.Size = Size(90, 22)
        self.Controls.Add(self.min_box)
        label_max = Label()
        label_max.Text = u'Максимальная скорость, м/с'
        label_max.Location = Point(12, 56)
        label_max.Size = Size(190, 22)
        self.Controls.Add(label_max)
        self.max_box = TextBox()
        self.max_box.Text = str(settings.get('max_velocity', 5.0))
        self.max_box.Location = Point(220, 56)
        self.max_box.Size = Size(90, 22)
        self.Controls.Add(self.max_box)
        apply_button = Button()
        apply_button.Text = u'Применить'
        apply_button.Location = Point(60, 105)
        apply_button.DialogResult = DialogResult.OK
        clear_button = Button()
        clear_button.Text = u'Очистить'
        clear_button.Location = Point(155, 105)
        clear_button.DialogResult = DialogResult.Yes
        cancel_button = Button()
        cancel_button.Text = u'Отмена'
        cancel_button.Location = Point(250, 105)
        cancel_button.DialogResult = DialogResult.Cancel
        self.Controls.Add(apply_button)
        self.Controls.Add(clear_button)
        self.Controls.Add(cancel_button)


def active_view_ducts(doc):
    try:
        return list(DB.FilteredElementCollector(doc, revit.active_view.Id).OfCategory(DB.BuiltInCategory.OST_DuctCurves).WhereElementIsNotElementType().ToElements())
    except Exception:
        return list(revit_utils.ducts(doc))


def selected_system_ducts(doc):
    ducts = active_view_ducts(doc)
    selection = revit.get_selection()
    if not selection or len(selection) == 0:
        return ducts
    selected = selection[0]
    system = revit_utils.system_name(selected)
    if not system:
        return ducts
    result = []
    for duct in ducts:
        if revit_utils.system_name(duct) == system:
            result.append(duct)
    return result


def main():
    settings = config.load_settings(extension_root)
    form = SpeedForm(settings)
    result = form.ShowDialog()
    if result == DialogResult.Cancel:
        return
    if result == DialogResult.Yes:
        graphics.clear_speed_highlight(revit.doc, revit.active_view, extension_root)
        forms.alert(u'Подсветка скоростей очищена.', title=u'Подсветка скоростей')
        return
    settings['min_velocity'] = config.to_float(form.min_box.Text, settings.get('min_velocity', 3.0))
    settings['max_velocity'] = config.to_float(form.max_box.Text, settings.get('max_velocity', 5.0))
    graphics.clear_speed_highlight(revit.doc, revit.active_view, extension_root)
    ducts = selected_system_ducts(revit.doc)
    ids = graphics.apply_speed_highlight(revit.doc, revit.active_view, ducts, settings)
    settings['speed_highlight_ids'] = ids
    config.save_settings(settings, extension_root)
    forms.alert(u'Подсветка скоростей применена. Воздуховодов: ' + str(len(ids)), title=u'Подсветка скоростей')


main()
