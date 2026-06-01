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
from ventcalc import revit_utils
from ventcalc import zeta


class ZetaForm(Form):
    def __init__(self, fitting, kind, values):
        self.Text = u'Местные сопротивления'
        self.Size = Size(420, 260)
        self.StartPosition = FormStartPosition.CenterScreen
        self.kind = kind
        self.values = values
        self.inputs = {}
        title = Label()
        title.Text = u'Элемент: ' + (revit_utils.element_name(fitting) or revit_utils.type_name(fitting))
        title.Location = Point(12, 12)
        title.Size = Size(380, 24)
        self.Controls.Add(title)
        y = 48
        for key in self.keys_for_kind(kind):
            label = Label()
            label.Text = self.caption(key) + u' рекомендовано: ' + zeta.format_number(values.get(key, 0.0))
            label.Location = Point(12, y)
            label.Size = Size(240, 22)
            self.Controls.Add(label)
            box = TextBox()
            box.Text = zeta.format_number(values.get(key, 0.0))
            box.Location = Point(260, y)
            box.Size = Size(120, 22)
            self.Controls.Add(box)
            self.inputs[key] = box
            y += 32
        ok = Button()
        ok.Text = 'OK'
        ok.Location = Point(215, 175)
        ok.DialogResult = DialogResult.OK
        cancel = Button()
        cancel.Text = u'Отмена'
        cancel.Location = Point(305, 175)
        cancel.DialogResult = DialogResult.Cancel
        self.Controls.Add(ok)
        self.Controls.Add(cancel)
        self.AcceptButton = ok
        self.CancelButton = cancel

    def keys_for_kind(self, kind):
        if kind == 'transition':
            return ['z_narrow', 'z_expand']
        if kind == 'tee' or kind == 'cross':
            return ['z_pass', 'z_branch']
        return ['z']

    def caption(self, key):
        names = {
            'z': 'z',
            'z_narrow': 'z_narrow',
            'z_expand': 'z_expand',
            'z_pass': 'z_pass',
            'z_branch': 'z_branch'
        }
        return names.get(key, key)

    def result_values(self):
        result = {}
        for key in self.inputs:
            result[key] = config.to_float(self.inputs[key].Text, self.values.get(key, 0.0))
        return result


def selected_fittings():
    result = []
    selection = revit.get_selection()
    for element in selection:
        if element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DuctFitting):
            result.append(element)
    if result:
        return result
    picked = forms.pick_elements_by_category(DB.BuiltInCategory.OST_DuctFitting, message=u'Выберите фитинги')
    if picked:
        return picked
    return []


def update_store(store, kind, values):
    if kind == 'elbow':
        angle = values.get('angle')
        if angle:
            store.setdefault('elbow', {})[str(angle)] = values.get('z', 0.0)
        return
    if kind == 'transition':
        store.setdefault('transition', {})['z_narrow'] = values.get('z_narrow', 0.0)
        store.setdefault('transition', {})['z_expand'] = values.get('z_expand', 0.0)
        return
    if kind == 'tee':
        store.setdefault('tee', {})['z_pass'] = values.get('z_pass', 0.0)
        store.setdefault('tee', {})['z_branch'] = values.get('z_branch', 0.0)
        return
    if kind == 'cross':
        store.setdefault('cross', {})['z_pass'] = values.get('z_pass', 0.0)
        store.setdefault('cross', {})['z_branch'] = values.get('z_branch', 0.0)
        return
    store.setdefault('other', {})['z'] = values.get('z', 0.0)


def main():
    fittings = selected_fittings()
    if not fittings:
        forms.alert(u'Фитинги не выбраны')
        return
    store = config.load_zeta(extension_root)
    transaction = DB.Transaction(revit.doc, 'VentCalc zeta')
    transaction.Start()
    try:
        for fitting in fittings:
            kind, values = zeta.recommended_values(fitting, store)
            form = ZetaForm(fitting, kind, values)
            if form.ShowDialog() != DialogResult.OK:
                continue
            user_values = form.result_values()
            if values.get('angle'):
                user_values['angle'] = values.get('angle')
            update_store(store, kind, user_values)
            revit_utils.set_comments(fitting, zeta.format_comment(kind, user_values))
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
    config.save_zeta(store, extension_root)
    forms.alert(u'Значения местных сопротивлений сохранены')


main()
