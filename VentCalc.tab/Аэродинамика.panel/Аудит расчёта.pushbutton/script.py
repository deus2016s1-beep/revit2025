# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

import Autodesk.Revit.DB as DB
from pyrevit import forms, script
from ventcalc import config


def round_value(value, digits):
    try:
        return round(float(value), digits)
    except Exception:
        return value


def candidate_rows(output, result):
    rows = []
    for item in result.get('candidate_summaries', []):
        selected = u'Да' if config.to_bool(item.get('selected', False), False) else u'Нет'
        rows.append([
            item.get('start_element_id', ''),
            item.get('start_name', ''),
            item.get('sections_count', 0),
            item.get('revit_ducts_count', 0),
            round_value(item.get('length_m', 0.0), 2),
            round_value(item.get('friction_pa', 0.0), 2),
            round_value(item.get('local_pa', 0.0), 2),
            round_value(item.get('total_pa', 0.0), 2),
            selected
        ])
    return rows


def local_rows(output, result):
    rows = []
    for item in result.get('local_resistance_audit', []):
        element_id = item.get('element_id', '')
        link = element_id
        try:
            link = output.linkify(DB.ElementId(int(element_id)))
        except Exception:
            link = element_id
        rows.append([
            item.get('section', ''),
            link,
            item.get('type', ''),
            item.get('decision', ''),
            round_value(item.get('zeta', 0.0), 2),
            round_value(item.get('pv_pa', 0.0), 2),
            round_value(item.get('local_pa', 0.0), 2),
            item.get('reason', '')
        ])
    return rows


def main():
    path = config.data_path('ventcalc_last_result.json', extension_root)
    if not os.path.exists(path):
        forms.alert(u'Сначала выполните расчет воздуховодов.', title=u'Аудит расчёта')
        return
    result = config.read_json(path, {})
    output = script.get_output()
    output.set_title(u'Аудит расчёта VentCalc')
    output.print_md(u'## Аудит расчёта VentCalc')
    output.print_md(u'* Файл Excel: ' + config.unicode_text(result.get('excel_path', u'не создан')))
    output.print_md(u'* Старт: ElementId ' + config.unicode_text(result.get('start_element_id', '')))
    output.print_md(u'* Конец: ElementId ' + config.unicode_text(result.get('end_element_id', '')))
    output.print_md(u'### Кандидаты критической трассы')
    candidates = candidate_rows(output, result)
    if candidates:
        output.print_table(table_data=candidates, columns=[u'Старт ElementId', u'Имя старта', u'Количество участков', u'Воздуховодов Revit', u'Длина, м', u'Трение, Па', u'МС, Па', u'Итого, Па', u'Выбрана'])
    else:
        output.print_md(u'Кандидаты не сохранены. Выполните расчет заново.')
    output.print_md(u'### Местные сопротивления критической трассы')
    locals_table = local_rows(output, result)
    if locals_table:
        output.print_table(table_data=locals_table, columns=[u'Участок', u'ElementId', u'Тип', u'Решение', u'ζ', u'Pv, Па', u'МС, Па', u'Причина'])
    else:
        output.print_md(u'Местные сопротивления в последнем результате не найдены.')


main()
