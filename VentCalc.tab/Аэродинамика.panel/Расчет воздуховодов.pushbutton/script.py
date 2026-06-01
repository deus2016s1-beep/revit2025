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


def print_calculation_table(output, result):
    rows = []
    for row in result.get('rows', []):
        rows.append([
            row.get('section', ''),
            row.get('size', ''),
            round(row.get('flow_m3h', 0.0), 1),
            round(row.get('length_m', 0.0), 2),
            round(row.get('velocity_ms', 0.0), 2),
            round(row.get('re', 0.0), 0),
            round(row.get('lambda', 0.0), 4),
            round(row.get('pv_pa', 0.0), 2),
            round(row.get('r_pa_m', 0.0), 2),
            round(row.get('friction_pa', 0.0), 2),
            round(row.get('local_zeta', 0.0), 3),
            round(row.get('local_pa', 0.0), 2),
            round(row.get('total_pa', 0.0), 2)
        ])
    output.print_md(u'## Критическая трасса VentCalc')
    if rows:
        output.print_table(table_data=rows, columns=[u'Участок', u'Размер', u'Расход м³/ч', u'Длина', u'Скорость', u'Re', u'λ', u'Pv', u'R', u'R·l', u'Σζ', u'Z', u'ΔP'])
    else:
        output.print_md(u'Расчетные участки не найдены.')


def save_last_result(result, path):
    data = {
        'critical_path_ids': result.get('critical_path_ids', []),
        'critical_duct_ids': result.get('critical_duct_ids', []),
        'critical_fitting_ids': result.get('critical_fitting_ids', []),
        'start_element_id': result.get('start_element_id'),
        'end_element_id': result.get('end_element_id'),
        'rows': minimal_rows(result.get('rows', [])),
        'totals': result.get('totals', {}),
        'excel_path': path
    }
    config.write_json(config.data_path('ventcalc_last_result.json', extension_root), data)


def minimal_rows(rows):
    result = []
    for row in rows:
        result.append({'duct_id': row.get('duct_id'), 'velocity_ms': row.get('velocity_ms', 0.0)})
    return result



def print_candidate_table(output, result):
    rows = []
    for item in result.get('candidate_summaries', []):
        rows.append([
            item.get('start_element_id', ''),
            item.get('start_name', ''),
            item.get('sections_count', 0),
            round(item.get('length_m', 0.0), 2),
            round(item.get('friction_pa', 0.0), 2),
            round(item.get('local_pa', 0.0), 2),
            round(item.get('total_pa', 0.0), 2)
        ])
    output.print_md(u'## Кандидаты критической трассы')
    if rows:
        output.print_table(table_data=rows, columns=[u'Старт ElementId', u'Имя старта', u'Количество участков', u'Длина, м', u'Трение, Па', u'МС, Па', u'Итого, Па'])
    else:
        output.print_md(u'Кандидаты не найдены.')

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
    print_candidate_table(output, result)
    print_calculation_table(output, result)
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
    save_last_result(result, path)
    reserve = totals.get('reserve_percent', 0.0)
    message = u'Расчет выполнен'
    message += u'\nСтарт: ElementId ' + str(result.get('start_element_id', ''))
    message += u'\nКонец: ElementId ' + str(result.get('end_element_id', ''))
    message += u'\nУчастков: ' + str(len(result.get('rows', [])))
    message += u'\nДлина: ' + str(round(totals.get('length_m', 0.0), 2)) + u' м'
    message += u'\nТрение: ' + str(round(totals.get('friction_pa', 0.0), 2)) + u' Па'
    message += u'\nМС: ' + str(round(totals.get('local_pa', 0.0), 2)) + u' Па'
    message += u'\nИтого: ' + str(round(totals.get('total_pa', 0.0), 2)) + u' Па'
    message += u'\nС запасом ' + str(round(reserve, 2)) + u'%: ' + str(round(totals.get('total_with_reserve_pa', 0.0), 2)) + u' Па'
    if path:
        message += u'\nФайл: ' + path
    else:
        message += u'\nФайл: не создан'
    forms.alert(message, title=u'Расчет воздуховодов')


main()
