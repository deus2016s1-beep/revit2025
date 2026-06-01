# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

from pyrevit import revit, forms, script
from ventcalc import calc
from ventcalc import config
from ventcalc import excel
from ventcalc import graphics


def print_diagnostics(output, result):
    diagnostics = result.get('diagnostics', {})
    output.print_md(u'## VentCalc diagnostics')
    output.print_md(u'* ducts_count: ' + str(diagnostics.get('ducts_count', 0)))
    output.print_md(u'* end_duct_ids: ' + str(diagnostics.get('end_duct_ids', [])))
    output.print_md(u'* candidates_count: ' + str(diagnostics.get('candidates_count', 0)))
    output.print_md(u'* best_path_len: ' + str(diagnostics.get('best_path_len', 0)))
    output.print_md(u'* friction_pa: ' + str(round(diagnostics.get('friction_pa', 0.0), 3)))
    output.print_md(u'* local_pa: ' + str(round(diagnostics.get('local_pa', 0.0), 3)))
    output.print_md(u'* total_pa: ' + str(round(diagnostics.get('total_pa', 0.0), 3)))
    rows = []
    for row in diagnostics.get('first_rows', []):
        rows.append([
            row.get('duct_id', ''),
            round(row.get('flow_m3s', 0.0), 6),
            round(row.get('velocity_ms', 0.0), 3),
            round(row.get('friction_pa', 0.0), 3)
        ])
    if rows:
        output.print_table(table_data=rows, columns=[u'duct_id', u'flow_m3s', u'velocity_ms', u'friction_pa'])


def main():
    output = script.get_output()
    selection = revit.get_selection()
    selected_ids = None
    if selection and len(selection) > 0:
        selected_ids = [element.Id.IntegerValue for element in selection]
    try:
        result = calc.calculate(revit.doc, selected_ids, extension_root)
    except Exception as error:
        forms.alert(config.unicode_text(error), title=u'Расчет воздуховодов')
        return
    print_diagnostics(output, result)
    totals = result.get('totals', {})
    if totals.get('total_pa', 0.0) <= 0.0:
        forms.alert(u'Трасса найдена, но потери равны 0. Проверь расход/размеры воздуховодов.', title=u'Расчет воздуховодов')
    settings = result.get('settings', {})
    path = None
    if config.to_bool(settings.get('ask_before_excel', True), True):
        if forms.alert(u'Расчет выполнен. Создать Excel-файл?', yes=True, no=True):
            path = excel.export_calculation(result)
    else:
        path = excel.export_calculation(result)
    try:
        graphics.apply_overrides(revit.doc, revit.active_view, result)
    except Exception as error:
        message = u'Ошибка подсветки критической трассы: ' + config.unicode_text(error)
        output.print_md(message)
        forms.alert(message, title=u'Расчет воздуховодов')
    message = u'Расчет выполнен\nСумма: ' + str(round(totals.get('total_pa', 0.0), 2)) + u' Па\nС запасом: ' + str(round(totals.get('total_with_reserve_pa', 0.0), 2)) + u' Па'
    if path:
        message += u'\nФайл: ' + path
    forms.alert(message, title=u'Расчет воздуховодов')


main()
