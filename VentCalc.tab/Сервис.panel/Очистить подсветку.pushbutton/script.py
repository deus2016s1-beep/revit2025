# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

from pyrevit import revit, forms
from ventcalc import config
from ventcalc import graphics


def main():
    settings = config.load_settings(extension_root)
    ids = []
    for element_id in settings.get('critical_highlight_ids', []):
        if element_id not in ids:
            ids.append(element_id)
    for element_id in settings.get('speed_highlight_ids', []):
        if element_id not in ids:
            ids.append(element_id)
    if not ids:
        forms.alert(u'Подсветка VentCalc не найдена.', title=u'Очистить подсветку')
        return
    graphics.clear_ids(revit.doc, revit.active_view, ids)
    settings['critical_highlight_enabled'] = False
    settings['critical_highlight_ids'] = []
    settings['speed_highlight_ids'] = []
    config.save_settings(settings, extension_root)
    forms.alert(u'Подсветка VentCalc очищена. Элементов: ' + str(len(ids)), title=u'Очистить подсветку')


main()
