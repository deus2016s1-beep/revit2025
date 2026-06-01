# -*- coding: utf-8 -*-
import math
from ventcalc import config
from ventcalc import network
from ventcalc import revit_utils
from ventcalc import zeta

MAX_SIMPLE_PATHS = 500
MAX_PATH_DEPTH = 200


def air_density(settings):
    return config.to_float(settings.get('air_density', 1.2), 1.2)


def dynamic_viscosity(settings):
    return config.to_float(settings.get('dynamic_viscosity', 0.0000181), 0.0000181)


def roughness_m(settings):
    return config.to_float(settings.get('roughness_mm', 0.1), 0.1) / 1000.0


def dynamic_pressure_by_velocity(velocity, settings):
    return air_density(settings) * velocity * velocity / 2.0


def dynamic_pressure(duct, settings):
    values = duct_values(duct, settings)
    return values.get('pv_pa', 0.0)


def reynolds(velocity, diameter, settings):
    mu = dynamic_viscosity(settings)
    if mu <= 0 or diameter <= 0 or velocity <= 0:
        return 0.0
    return air_density(settings) * velocity * diameter / mu


def friction_lambda(re_value, diameter, settings):
    if re_value <= 0 or diameter <= 0:
        return 0.0
    if re_value < 2300.0:
        return 64.0 / re_value
    eps = roughness_m(settings)
    value = 0.11 * math.pow((eps / diameter) + (68.0 / re_value), 0.25)
    if value < 0.008:
        value = 0.008
    return value


def duct_values(duct, settings):
    length = revit_utils.duct_length_m(duct)
    flow = revit_utils.duct_flow_m3s(duct)
    area = revit_utils.duct_area_m2(duct)
    velocity = 0.0
    if area > 0:
        velocity = flow / area
    diameter = revit_utils.hydraulic_diameter_m(duct)
    re_value = reynolds(velocity, diameter, settings)
    lambda_value = friction_lambda(re_value, diameter, settings)
    pv = dynamic_pressure_by_velocity(velocity, settings)
    r_pa_m = 0.0
    if diameter > 0:
        r_pa_m = lambda_value / diameter * pv
    friction = r_pa_m * length
    return {
        'length_m': length,
        'flow_m3s': flow,
        'flow_m3h': flow * 3600.0,
        'area_m2': area,
        'velocity_ms': velocity,
        'diameter_m': diameter,
        're': re_value,
        'lambda': lambda_value,
        'pv_pa': pv,
        'r_pa_m': r_pa_m,
        'friction_pa': friction
    }


def duct_row(duct, index, settings):
    values = duct_values(duct, settings)
    row = {
        'index': index + 1,
        'section': str(index) + '-' + str(index + 1),
        'duct_id': duct.Id.IntegerValue,
        'element_ids': [duct.Id.IntegerValue],
        'name': revit_utils.element_name(duct) or revit_utils.type_name(duct),
        'system': revit_utils.system_name(duct),
        'size': revit_utils.duct_size_text(duct),
        'local_zeta': 0.0,
        'local_pa': 0.0,
        'fittings': [],
        'note': '',
        'total_pa': values.get('friction_pa', 0.0)
    }
    row.update(values)
    return row


def calculate(doc, selected_ids=None, start_path=None):
    settings = config.load_settings(start_path)
    zeta_data = config.load_zeta(start_path)
    data = network.build_network(doc)
    if not data['ducts']:
        raise Exception(u'Воздуховоды не найдены')
    end_element = selected_end_element(doc, selected_ids)
    if end_element is None:
        raise Exception(u'Выберите один конечный элемент трассы: вентилятор, выброс, решетку, зонт, дефлектор или конечный воздуховод')
    end_duct_ids = network.endpoint_duct_ids(data, end_element)
    if not end_duct_ids:
        raise Exception(u'Выбранный элемент не подключен к воздуховоду')
    starts = start_points(data, end_element, end_duct_ids)
    path_info = choose_path(data, starts, end_duct_ids, settings, zeta_data)
    if not path_info:
        raise Exception(u'Критическая трасса до выбранного конечного элемента не найдена. Проверьте соединения воздуховодов и фитингов')
    rows, fitting_ids = make_rows(path_info, data, settings, zeta_data)
    if not rows:
        raise Exception(u'Трасса найдена, но расчетные участки не сформированы')
    reserve_percent = config.to_float(settings.get('reserve_percent', 15.0), 15.0)
    for row in rows:
        row['total_pa'] = row.get('friction_pa', 0.0) + row.get('local_pa', 0.0)
        row['total_with_reserve_pa'] = row['total_pa'] * (1.0 + reserve_percent / 100.0)
    totals = make_totals(rows, reserve_percent)
    diagnostics = make_diagnostics(data, starts, end_duct_ids, path_info.get('path', []), rows, totals)
    start_element = path_info.get('start_element')
    start_element_id = None
    if start_element is not None:
        start_element_id = start_element.Id.IntegerValue
    return {
        'rows': rows,
        'totals': totals,
        'settings': settings,
        'settings_start_path': start_path,
        'critical_path': path_info.get('path', []),
        'critical_duct_ids': path_info.get('path', []),
        'critical_fitting_ids': fitting_ids,
        'start_element_id': start_element_id,
        'start_element_name': element_display_name(start_element),
        'end_element_id': end_element.Id.IntegerValue,
        'end_element_name': element_display_name(end_element),
        'diagnostics': diagnostics
    }


def make_totals(rows, reserve_percent):
    return {
        'length_m': sum([row.get('length_m', 0.0) for row in rows]),
        'friction_pa': sum([row.get('friction_pa', 0.0) for row in rows]),
        'local_pa': sum([row.get('local_pa', 0.0) for row in rows]),
        'total_pa': sum([row.get('total_pa', 0.0) for row in rows]),
        'total_with_reserve_pa': sum([row.get('total_with_reserve_pa', 0.0) for row in rows]),
        'reserve_percent': reserve_percent
    }


def make_diagnostics(data, starts, end_duct_ids, path, rows, totals):
    first_rows = []
    for row in rows[:5]:
        first_rows.append({
            'duct_id': row.get('duct_id'),
            'flow_m3s': row.get('flow_m3s', 0.0),
            'velocity_ms': row.get('velocity_ms', 0.0),
            'friction_pa': row.get('friction_pa', 0.0)
        })
    return {
        'ducts_count': len(data.get('ducts', {})),
        'end_duct_ids': end_duct_ids,
        'candidates_count': len(starts),
        'best_path_len': len(path),
        'friction_pa': totals.get('friction_pa', 0.0),
        'local_pa': totals.get('local_pa', 0.0),
        'total_pa': totals.get('total_pa', 0.0),
        'first_rows': first_rows
    }


def selected_end_element(doc, selected_ids):
    if not selected_ids:
        return None
    if len(selected_ids) != 1:
        raise Exception(u'Для расчета выберите ровно один конечный элемент трассы')
    try:
        return doc.GetElement(DBElementId(selected_ids[0]))
    except Exception:
        try:
            import Autodesk.Revit.DB as DB
            return doc.GetElement(DB.ElementId(selected_ids[0]))
        except Exception:
            return None


def DBElementId(value):
    import Autodesk.Revit.DB as DB
    return DB.ElementId(value)


def start_points(data, end_element, end_duct_ids):
    result = []
    end_element_id = end_element.Id.IntegerValue
    ducts_with_normal_terminal = set()
    for element_id in data.get('terminals', {}):
        element = data['terminals'][element_id]
        linked_ducts = network.endpoint_duct_ids(data, element)
        if element_id == end_element_id:
            continue
        if not linked_ducts:
            continue
        if is_real_start_terminal(element):
            for duct_id in linked_ducts:
                ducts_with_normal_terminal.add(duct_id)
                if duct_id not in end_duct_ids:
                    result.append({'duct_id': duct_id, 'element': element, 'kind': 'terminal'})
    for duct_id in data.get('ducts', {}):
        if duct_id in end_duct_ids:
            continue
        if duct_id in ducts_with_normal_terminal:
            continue
        if len(data.get('graph', {}).get(duct_id, [])) <= 1:
            result.append({'duct_id': duct_id, 'element': None, 'kind': 'deadend'})
    return unique_starts(result)


def unique_starts(starts):
    result = []
    seen = set()
    for start in starts:
        element = start.get('element')
        element_id = 0
        if element is not None:
            element_id = element.Id.IntegerValue
        key = (start.get('duct_id'), element_id)
        if key not in seen:
            seen.add(key)
            result.append(start)
    return result


def is_real_start_terminal(element):
    if zeta.is_normal_terminal(element):
        return True
    linked = revit_utils.connected_ducts(element)
    if linked and len(linked) == 1:
        category = revit_utils.category_name(element).lower()
        if u'терминал' in category or 'terminal' in category:
            return True
        if u'оборуд' in category or 'equipment' in category:
            return True
    return False


def choose_path(data, starts, end_duct_ids, settings, zeta_data):
    best = None
    best_pressure = -1.0
    for start in starts:
        for end_id in end_duct_ids:
            paths = all_simple_paths(data.get('graph', {}), start.get('duct_id'), end_id, MAX_SIMPLE_PATHS, MAX_PATH_DEPTH)
            for path in paths:
                pressure = path_pressure(path, data, settings, zeta_data, start.get('element'))
                if pressure > best_pressure:
                    best_pressure = pressure
                    best = {'path': path, 'start_element': start.get('element'), 'start_kind': start.get('kind'), 'total_pa': pressure}
    return best


def all_simple_paths(graph, start, finish, max_paths, max_depth):
    if start is None or finish is None:
        return []
    stack = [(start, [start])]
    result = []
    while stack and len(result) < max_paths:
        current, path = stack.pop()
        if current == finish:
            result.append(path)
            continue
        if len(path) >= max_depth:
            continue
        for next_node in graph.get(current, []):
            if next_node not in path:
                stack.append((next_node, path + [next_node]))
    return result


def path_pressure(path, data, settings, zeta_data, start_element=None):
    pressure = 0.0
    ducts = data['ducts']
    for duct_id in path:
        pressure += duct_values(ducts[duct_id], settings).get('friction_pa', 0.0)
    if start_element is not None and path:
        pressure += terminal_pressure(start_element, ducts[path[0]], settings, zeta_data)
    for index in range(len(path) - 1):
        fitting = data['edges'].get((path[index], path[index + 1]))
        if fitting:
            pressure += fitting_pressure(fitting, ducts[path[index]], ducts[path[index + 1]], settings, zeta_data)
    return pressure


def make_rows(path_info, data, settings, zeta_data):
    rows = []
    fitting_ids = []
    path = path_info.get('path', [])
    ducts = data['ducts']
    start_element = path_info.get('start_element')
    for index in range(len(path)):
        duct_id = path[index]
        row = duct_row(ducts[duct_id], index, settings)
        if index == 0 and start_element is not None:
            add_terminal_to_row(row, start_element, ducts[duct_id], settings, zeta_data)
        if index > 0:
            previous_duct = ducts[path[index - 1]]
            fitting = data['edges'].get((path[index - 1], duct_id))
            if fitting:
                add_fitting_to_row(row, fitting, previous_duct, ducts[duct_id], settings, zeta_data)
                fitting_ids.append(fitting.Id.IntegerValue)
        rows.append(row)
    return rows, fitting_ids


def terminal_pressure(element, duct, settings, zeta_data):
    value = zeta.fitting_zeta(element, None, duct, zeta_data)
    return value * dynamic_pressure(duct, settings)


def fitting_pressure(fitting, previous_duct, next_duct, settings, zeta_data):
    value = zeta.fitting_zeta(fitting, previous_duct, next_duct, zeta_data)
    return value * dynamic_pressure(next_duct, settings)


def add_terminal_to_row(row, element, duct, settings, zeta_data):
    value = zeta.fitting_zeta(element, None, duct, zeta_data)
    pressure = value * dynamic_pressure(duct, settings)
    row['local_zeta'] += value
    row['local_pa'] += pressure
    row['fittings'].append({'id': element.Id.IntegerValue, 'kind': zeta.fitting_kind(element), 'zeta': value, 'pressure_pa': pressure})
    row['element_ids'].append(element.Id.IntegerValue)
    append_note(row, element, value)


def add_fitting_to_row(row, fitting, previous_duct, next_duct, settings, zeta_data):
    pressure_duct = next_duct
    if pressure_duct is None:
        pressure_duct = previous_duct
    if pressure_duct is None:
        return
    value = zeta.fitting_zeta(fitting, previous_duct, next_duct, zeta_data)
    pressure = value * dynamic_pressure(pressure_duct, settings)
    kind = zeta.fitting_kind(fitting)
    row['local_zeta'] += value
    row['local_pa'] += pressure
    row['fittings'].append({'id': fitting.Id.IntegerValue, 'kind': kind, 'zeta': value, 'pressure_pa': pressure})
    row['element_ids'].append(fitting.Id.IntegerValue)
    append_note(row, fitting, value)


def append_note(row, element, value):
    text = local_resistance_name(element) + ' z=' + zeta.format_number(value)
    if row.get('note'):
        row['note'] += '; ' + text
    else:
        row['note'] = text


def local_resistance_name(element):
    kind = zeta.fitting_kind(element)
    if kind == 'elbow':
        return u'отвод ' + str(zeta.elbow_angle(element)) + u'°'
    names = {
        'transition': u'переход',
        'tee': u'тройник',
        'cross': u'крестовина',
        'grille': u'решетка',
        'hood': u'зонт',
        'deflector': u'дефлектор',
        'equipment': u'оборудование',
        'inlet': u'вход',
        'outlet': u'выход',
        'cap': u'заглушка',
        'damper': u'клапан',
        'fire_damper': u'противопожарный клапан',
        'backdraft_damper': u'обратный клапан'
    }
    return names.get(kind, revit_utils.element_name(element) or revit_utils.type_name(element) or kind)


def element_display_name(element):
    if element is None:
        return ''
    return revit_utils.element_name(element) or revit_utils.type_name(element) or revit_utils.category_name(element)
