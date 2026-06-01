# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

import Autodesk.Revit.DB as DB
from pyrevit import revit, script
from ventcalc import network
from ventcalc import revit_utils
from ventcalc import zeta


class Issue(object):
    def __init__(self, status, element, problem, action):
        self.status = status
        self.element = element
        self.problem = problem
        self.action = action


def add_issue(issues, status, element, problem, action):
    issues.append(Issue(status, element, problem, action))


def element_type_text(element):
    text = revit_utils.type_name(element)
    if not text:
        text = revit_utils.element_name(element)
    return text


def check_ducts(doc, issues):
    ducts = revit_utils.ducts(doc)
    for duct in ducts:
        if revit_utils.duct_flow_m3s(duct) <= 0:
            add_issue(issues, u'Ошибка', duct, u'Воздуховод без расхода', u'Заполнить расход воздуха')
        if revit_utils.duct_area_m2(duct) <= 0 or revit_utils.hydraulic_diameter_m(duct) <= 0:
            add_issue(issues, u'Ошибка', duct, u'Воздуховод без размера', u'Проверить ширину, высоту или диаметр')
        if revit_utils.duct_length_m(duct) <= 0:
            add_issue(issues, u'Ошибка', duct, u'Воздуховод с нулевой длиной', u'Исправить геометрию участка')
    return ducts


def check_elements(doc, issues):
    elements = revit_utils.air_network_elements(doc)
    for element in elements:
        kind = zeta.fitting_kind(element)
        values = zeta.parse_comment(revit_utils.comments(element))
        if kind == 'unknown':
            add_issue(issues, u'Предупреждение', element, u'Элемент не удалось классифицировать', u'Переименовать тип/семейство или вручную задать z')
        if not values:
            add_issue(issues, u'Ошибка', element, u'Нет z/zeta/z_pass/z_branch/z_narrow/z_expand в комментариях', u'Запустить кнопку Местные сопротивления')
        else:
            if has_zero_value(values) and not zeta.zero_allowed(element):
                add_issue(issues, u'Предупреждение', element, u'Коэффициент местного сопротивления равен 0.0', u'Проверить значение; 0.0 допускается только для заглушки')
    return elements


def has_zero_value(values):
    for key in values:
        try:
            if abs(float(values[key])) < 0.000001:
                return True
        except Exception:
            pass
    return False


def check_breaks(doc, issues):
    ducts, fittings, graph, edges = network.collect_network(doc, None)
    for duct_id in graph:
        if len(graph.get(duct_id, [])) == 0:
            add_issue(issues, u'Предупреждение', ducts[duct_id], u'Одиночный воздуховод или разрыв сети', u'Проверить соединения коннекторов')
    for element in revit_utils.air_network_elements(doc):
        connected_ducts = revit_utils.connected_ducts(element)
        if len(connected_ducts) == 0:
            add_issue(issues, u'Предупреждение', element, u'Одиночный элемент без соединенных воздуховодов', u'Подключить элемент к сети')
        elif len(connected_ducts) == 1 and zeta.fitting_kind(element) not in ['cap', 'inlet', 'outlet', 'grille', 'hood', 'deflector']:
            add_issue(issues, u'Предупреждение', element, u'Элемент подключен только к одному воздуховоду', u'Проверить возможный разрыв сети')


def apply_highlight(doc, view, issues):
    transaction = DB.Transaction(doc, 'VentCalc check graphics')
    transaction.Start()
    try:
        red = DB.Color(255, 0, 0)
        yellow = DB.Color(255, 210, 0)
        handled = set()
        for issue in issues:
            element_id_value = issue.element.Id.IntegerValue
            if element_id_value in handled and issue.status != u'Ошибка':
                continue
            settings = DB.OverrideGraphicSettings()
            if issue.status == u'Ошибка':
                settings.SetProjectionLineColor(red)
                settings.SetProjectionLineWeight(8)
            else:
                settings.SetProjectionLineColor(yellow)
                settings.SetProjectionLineWeight(6)
            view.SetElementOverrides(issue.element.Id, settings)
            handled.add(element_id_value)
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise


def table_rows(output, issues):
    rows = []
    for issue in issues:
        element = issue.element
        rows.append([
            issue.status,
            output.linkify(element.Id),
            revit_utils.category_name(element),
            element_type_text(element),
            issue.problem,
            issue.action
        ])
    return rows


def main():
    output = script.get_output()
    output.set_title(u'Проверка системы VentCalc')
    issues = []
    ducts = check_ducts(revit.doc, issues)
    elements = check_elements(revit.doc, issues)
    check_breaks(revit.doc, issues)
    if issues:
        try:
            apply_highlight(revit.doc, revit.active_view, issues)
        except Exception:
            pass
    errors = len([issue for issue in issues if issue.status == u'Ошибка'])
    warnings = len([issue for issue in issues if issue.status != u'Ошибка'])
    output.print_md(u'## Проверка системы VentCalc')
    output.print_md(u'* Воздуховодов: ' + str(len(ducts)))
    output.print_md(u'* Элементов воздуховодной сети: ' + str(len(elements)))
    output.print_md(u'* Ошибок: ' + str(errors))
    output.print_md(u'* Предупреждений: ' + str(warnings))
    if issues:
        output.print_table(table_data=table_rows(output, issues), columns=[u'Статус', u'ElementId', u'Категория', u'Тип', u'Проблема', u'Что сделать'])
    else:
        output.print_md(u'Ошибки не найдены.')


main()
