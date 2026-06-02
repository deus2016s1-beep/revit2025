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
    path = config.data_path('ventcalc_last_result.json', extension_root)
    if not os.path.exists(path):
        forms.alert(u'Сначала выполните расчет воздуховодов.', title=u'Подсветить критическую трассу')
        return
    result = config.read_json(path, {})
    if not result.get('critical_path_ids'):
        forms.alert(u'В последнем расчете нет critical_path_ids.', title=u'Подсветить критическую трассу')
        return
    enabled, ids = graphics.toggle_critical_path(revit.doc, revit.active_view, result, extension_root)
    if enabled:
        forms.alert(u'Критическая трасса подсвечена. Элементов: ' + str(len(ids)), title=u'Подсветить критическую трассу')
    else:
        forms.alert(u'Подсветка критической трассы очищена.', title=u'Подсветить критическую трассу')


main()
