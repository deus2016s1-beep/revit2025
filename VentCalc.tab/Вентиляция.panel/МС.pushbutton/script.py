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
from System.Windows.Forms import Form, Label, TextBox, Button, DialogResult, FormStartPosition, Panel
from System.Drawing import Point, Size
import Autodesk.Revit.DB as DB
from pyrevit import revit, forms
from ventcalc import config
from ventcalc import revit_utils
from ventcalc import zeta

ITEMS = [
    ('elbow_15', u'Отвод 15°', 'elbow', '15', 'z'),
    ('elbow_30', u'Отвод 30°', 'elbow', '30', 'z'),
    ('elbow_45', u'Отвод 45°', 'elbow', '45', 'z'),
    ('elbow_60', u'Отвод 60°', 'elbow', '60', 'z'),
    ('elbow_90', u'Отвод 90°', 'elbow', '90', 'z'),
    ('transition_narrow', u'Переход сужение', 'transition', None, 'z_narrow'),
    ('transition_expand', u'Переход расширение', 'transition', None, 'z_expand'),
    ('tee_pass', u'Тройник проход', 'tee', None, 'z_pass'),
    ('tee_branch', u'Тройник ответвление', 'tee', None, 'z_branch'),
    ('tap', u'Врезка', 'tap', None, 'z'),
    ('cross_pass', u'Крестовина проход', 'cross', None, 'z_pass'),
    ('cross_branch', u'Крестовина ответвление', 'cross', None, 'z_branch'),
    ('offset', u'Утка', 'offset', None, 'z'),
    ('cap', u'Заглушка', 'cap', None, 'z'),
    ('damper', u'Дроссель-клапан', 'damper', None, 'z'),
    ('fire_damper', u'Противопожарный клапан', 'fire_damper', None, 'z'),
    ('backdraft_damper', u'Обратный клапан', 'backdraft_damper', None, 'z'),
    ('inlet', u'Вход', 'inlet', None, 'z'),
    ('outlet', u'Выход', 'outlet', None, 'z'),
    ('grille', u'Решетка', 'grille', None, 'z'),
    ('hood', u'Зонт', 'hood', None, 'z'),
    ('deflector', u'Дефлектор', 'deflector', None, 'z')
]


class ZetaForm(Form):
    def __init__(self, store):
        Form.__init__(self)
        self.Text = u'Местные сопротивления'
        self.Size = Size(620, 720)
        self.StartPosition = FormStartPosition.CenterScreen
        self.inputs = {}
        title = Label()
        title.Text = u'Рекомендуемые значения будут записаны во все элементы воздуховодной сети проекта.'
        title.Location = Point(12, 12)
        title.Size = Size(520, 32)
        self.Controls.Add(title)
        header1 = Label()
        header1.Text = u'Тип элемента'
        header1.Location = Point(20, 50)
        header1.Size = Size(220, 22)
        self.Controls.Add(header1)
        header2 = Label()
        header2.Text = u'Рекомендуется'
        header2.Location = Point(270, 50)
        header2.Size = Size(120, 22)
        self.Controls.Add(header2)
        header3 = Label()
        header3.Text = u'Записать значение'
        header3.Location = Point(420, 50)
        header3.Size = Size(140, 22)
        self.Controls.Add(header3)
        panel = Panel()
        panel.Location = Point(12, 76)
        panel.Size = Size(580, 540)
        panel.AutoScroll = True
        self.Controls.Add(panel)
        y = 0
        for item in ITEMS:
            item_key, caption, section, subkey, value_key = item
            label = Label()
            label.Text = caption
            label.Location = Point(4, y + 3)
            label.Size = Size(240, 22)
            panel.Controls.Add(label)
            recommended = Label()
            recommended.Text = zeta.format_number(default_value(section, subkey, value_key))
            recommended.Location = Point(258, y + 3)
            recommended.Size = Size(90, 22)
            panel.Controls.Add(recommended)
            box = TextBox()
            box.Text = zeta.format_number(store_value(store, section, subkey, value_key))
            box.Location = Point(408, y)
            box.Size = Size(90, 22)
            panel.Controls.Add(box)
            self.inputs[item_key] = box
            y += 28
        ok = Button()
        ok.Text = u'Добавить'
        ok.Location = Point(400, 630)
        ok.Size = Size(90, 28)
        ok.DialogResult = DialogResult.OK
        cancel = Button()
        cancel.Text = u'Отмена'
        cancel.Location = Point(500, 630)
        cancel.Size = Size(90, 28)
        cancel.DialogResult = DialogResult.Cancel
        self.Controls.Add(ok)
        self.Controls.Add(cancel)
        self.AcceptButton = ok
        self.CancelButton = cancel

    def apply_to_store(self, store):
        for item in ITEMS:
            item_key, caption, section, subkey, value_key = item
            value = config.to_float(self.inputs[item_key].Text, store_value(store, section, subkey, value_key))
            if section == 'elbow':
                store.setdefault('elbow', {})[subkey] = value
            else:
                store.setdefault(section, {})[value_key] = value


def default_value(section, subkey, value_key):
    if section == 'elbow':
        return config.DEFAULT_ZETA.get('elbow', {}).get(subkey, 0.0)
    return config.DEFAULT_ZETA.get(section, {}).get(value_key, 0.0)


def store_value(store, section, subkey, value_key):
    if section == 'elbow':
        return store.get('elbow', {}).get(subkey, default_value(section, subkey, value_key))
    return store.get(section, {}).get(value_key, default_value(section, subkey, value_key))


def collect_target_elements(doc):
    return revit_utils.air_network_elements(doc)


def values_for_comment(element, store):
    kind = zeta.fitting_kind(element)
    if kind == 'elbow':
        angle = zeta.elbow_angle(element)
        return kind, {'z': store.get('elbow', {}).get(str(angle), config.DEFAULT_ZETA.get('elbow', {}).get(str(angle), 0.35)), 'angle': angle}
    if kind == 'transition':
        values = store.get('transition', {})
        return kind, {'z_narrow': values.get('z_narrow', config.DEFAULT_ZETA['transition']['z_narrow']), 'z_expand': values.get('z_expand', config.DEFAULT_ZETA['transition']['z_expand'])}
    if kind == 'tee':
        values = store.get('tee', {})
        return kind, {'z_pass': values.get('z_pass', config.DEFAULT_ZETA['tee']['z_pass']), 'z_branch': values.get('z_branch', config.DEFAULT_ZETA['tee']['z_branch'])}
    if kind == 'cross':
        values = store.get('cross', {})
        return kind, {'z_pass': values.get('z_pass', config.DEFAULT_ZETA['cross']['z_pass']), 'z_branch': values.get('z_branch', config.DEFAULT_ZETA['cross']['z_branch'])}
    values = store.get(kind, {})
    defaults = config.DEFAULT_ZETA.get(kind, config.DEFAULT_ZETA.get('unknown', {}))
    return kind, {'z': values.get('z', defaults.get('z', 0.0))}


def main():
    store = config.load_zeta(extension_root)
    form = ZetaForm(store)
    if form.ShowDialog() != DialogResult.OK:
        return
    form.apply_to_store(store)
    elements = collect_target_elements(revit.doc)
    if not elements:
        forms.alert(u'Элементы воздуховодной сети не найдены')
        return
    updated = 0
    skipped = 0
    transaction = DB.Transaction(revit.doc, 'VentCalc zeta')
    transaction.Start()
    try:
        for element in elements:
            kind, values = values_for_comment(element, store)
            if revit_utils.set_comments(element, zeta.format_comment(kind, values)):
                updated += 1
            else:
                skipped += 1
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
    config.save_zeta(store, extension_root)
    forms.alert(u'Значения местных сопротивлений сохранены\nОбновлено: ' + str(updated) + u'\nПропущено: ' + str(skipped))


main()
