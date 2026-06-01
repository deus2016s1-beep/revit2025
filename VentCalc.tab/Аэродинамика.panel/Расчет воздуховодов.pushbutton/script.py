# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

from pyrevit import revit, forms
from ventcalc import calc
from ventcalc import excel
from ventcalc import graphics


def main():
    selection = revit.get_selection()
    selected_ids = None
    if selection and len(selection) > 0:
        selected_ids = [element.Id.IntegerValue for element in selection]
    result = calc.calculate(revit.doc, selected_ids)
    if not result.get('rows'):
        forms.alert(u'Воздуховоды не найдены')
        return
    path = excel.export_calculation(result)
    try:
        graphics.apply_overrides(revit.doc, revit.active_view, result.get('rows', []))
    except Exception:
        pass
    totals = result.get('totals', {})
    forms.alert(u'Расчет выполнен\nФайл: ' + path + u'\nСумма: ' + str(round(totals.get('total_pa', 0.0), 2)) + u' Па\nС запасом: ' + str(round(totals.get('total_with_reserve_pa', 0.0), 2)) + u' Па')


main()
