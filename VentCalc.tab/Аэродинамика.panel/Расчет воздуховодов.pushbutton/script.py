# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

from pyrevit import revit, forms
from ventcalc import calc
from ventcalc import config
from ventcalc import excel
from ventcalc import graphics


def main():
    selection = revit.get_selection()
    selected_ids = None
    if selection and len(selection) > 0:
        selected_ids = [element.Id.IntegerValue for element in selection]
    try:
        result = calc.calculate(revit.doc, selected_ids, extension_root)
    except Exception as error:
        forms.alert(config.unicode_text(error), title=u'Расчет воздуховодов')
        return
    settings = result.get('settings', {})
    path = None
    if config.to_bool(settings.get('ask_before_excel', True), True):
        if forms.alert(u'Расчет выполнен. Создать Excel-файл?', yes=True, no=True):
            path = excel.export_calculation(result)
    else:
        path = excel.export_calculation(result)
    try:
        graphics.apply_overrides(revit.doc, revit.active_view, result)
    except Exception:
        pass
    totals = result.get('totals', {})
    message = u'Расчет выполнен\nСумма: ' + str(round(totals.get('total_pa', 0.0), 2)) + u' Па\nС запасом: ' + str(round(totals.get('total_with_reserve_pa', 0.0), 2)) + u' Па'
    if path:
        message += u'\nФайл: ' + path
    forms.alert(message, title=u'Расчет воздуховодов')


main()
