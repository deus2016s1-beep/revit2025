# -*- coding: utf-8 -*-
import math
from ventcalc import config
from ventcalc import network
from ventcalc import revit_utils
from ventcalc import zeta


def air_density(settings):
    return config.to_float(settings.get('air_density', 1.2), 1.2)


def dynamic_viscosity(settings):
    return config.to_float(settings.get('dynamic_viscosity', 0.0000181), 0.0000181)


def roughness_m(settings):
    return config.to_float(settings.get('roughness_mm', 0.1), 0.1) / 1000.0


def dynamic_pressure_by_velocity(velocity, settings):
    return air_density(settings) * velocity * velocity / 2.0


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


def dynamic_pressure(duct, settings):
    return duct_values(duct, settings).get('pv_pa', 0.0)


def duct_row(duct, index, settings):
    values = duct_values(duct, settings)
    warning = revit_utils.velocity_sanity_warning(duct, values.get('flow_m3s', 0.0), values.get('velocity_ms', 0.0))
    row = {
        'index': index + 1,
        'section': str(index) + '-' + str(index + 1),
        'duct_id': duct.Id.IntegerValue,
        'element_ids': [duct.Id.IntegerValue],
        'name': revit_utils.duct_shape_name(duct),
        'system': revit_utils.system_name(duct),
        'size': revit_utils.duct_size_text(duct),
        'local_zeta': 0.0,
        'local_pa': 0.0,
        'fittings': [],
        'note': warning,
        'warnings': [warning] if warning else [],
        'total_pa': values.get('friction_pa', 0.0)
    }
    row.update(values)
    return row


def calculate(doc, selected_ids=None, start_path=None):
    settings = config.load_settings(start_path)
    zeta_data = config.load_zeta(start_path)
    data = network.build_element_graph(doc)
    if not data.get('duct_ids'):
        raise Exception(u'Воздуховоды не найдены')
    selected_end_id = selected_element_id(selected_ids)
    if selected_end_id not in data['elements_by_id']:
        raise Exception(u'Выбранный элемент не входит в воздуховодную сеть')
    starts = find_start_candidates(data, selected_end_id)
    paths = []
    for start_id in starts:
        path_ids = find_path_between(data['graph'], start_id, selected_end_id)
        if path_ids:
            paths.append(calculate_element_path(path_ids, data, settings, zeta_data))
    critical = choose_critical_path(paths)
    if not critical:
        raise Exception(u'Критическая трасса до выбранного конечного элемента не найдена. Проверьте соединения воздуховодов и фитингов')
    reserve_percent = config.to_float(settings.get('reserve_percent', 15.0), 15.0)
    if reserve_percent <= 0.0:
        reserve_percent = 15.0
    rows = critical.get('rows', [])
    for row in rows:
        row['total_pa'] = row.get('friction_pa', 0.0) + row.get('local_pa', 0.0)
        row['total_with_reserve_pa'] = row['total_pa'] * (1.0 + reserve_percent / 100.0)
    totals = make_totals(rows, reserve_percent)
    start_id = critical.get('start_element_id')
    result = {
        'rows': rows,
        'totals': totals,
        'settings': settings,
        'settings_start_path': start_path,
        'critical_path_ids': critical.get('path_ids', []),
        'critical_path': critical.get('path_ids', []),
        'critical_duct_ids': critical.get('duct_ids', []),
        'critical_fitting_ids': critical.get('fitting_ids', []),
        'start_element_id': start_id,
        'start_element_name': element_display_name(data, start_id),
        'end_element_id': selected_end_id,
        'end_element_name': element_display_name(data, selected_end_id),
        'diagnostics': make_diagnostics(data, starts, critical, rows, totals),
        'candidate_summaries': candidate_summaries(paths, data)
    }
    return result



def candidate_summaries(paths, data):
    result = []
    for item in paths:
        start_id = item.get('start_element_id')
        rows = item.get('rows', [])
        totals = make_totals(rows, 0.0)
        result.append({
            'start_element_id': start_id,
            'start_name': element_display_name(data, start_id),
            'sections_count': len(rows),
            'length_m': totals.get('length_m', 0.0),
            'friction_pa': totals.get('friction_pa', 0.0),
            'local_pa': totals.get('local_pa', 0.0),
            'total_pa': totals.get('total_pa', 0.0)
        })
    return result

def selected_element_id(selected_ids):
    if not selected_ids:
        raise Exception(u'Выберите один конечный элемент трассы')
    if len(selected_ids) != 1:
        raise Exception(u'Для расчета выберите ровно один конечный элемент трассы')
    return selected_ids[0]


def find_start_candidates(data, selected_end_id):
    component = connected_component_ids(data.get('graph', {}), selected_end_id)
    result = []
    duct_has_terminal = set()
    terminal_like = data.get('terminal_ids', []) + data.get('equipment_ids', [])
    for element_id in terminal_like:
        if element_id == selected_end_id or element_id not in component:
            continue
        element = data['elements_by_id'][element_id]
        connected_ducts = connected_duct_ids(data, element_id)
        if not connected_ducts:
            continue
        if is_start_terminal(element):
            result.append(element_id)
            for duct_id in connected_ducts:
                duct_has_terminal.add(duct_id)
    has_real_start = len(result) > 0
    for element_id in component:
        if element_id == selected_end_id:
            continue
        if len(data['graph'].get(element_id, [])) > 1:
            continue
        element = data['elements_by_id'][element_id]
        if zeta.fitting_kind(element) == 'cap' and has_real_start:
            continue
        if element_id in data.get('duct_ids', []) and element_id in duct_has_terminal:
            continue
        if element_id not in result:
            result.append(element_id)
    return unique_ids(result)


def connected_component_ids(graph, start_id):
    if start_id not in graph:
        return set()
    result = set([start_id])
    stack = [start_id]
    while stack:
        current = stack.pop()
        for next_id in graph.get(current, []):
            if next_id not in result:
                result.add(next_id)
                stack.append(next_id)
    return result


def is_start_terminal(element):
    if zeta.is_normal_terminal(element):
        return True
    category = revit_utils.category_name(element).lower()
    if u'терминал' in category or 'terminal' in category:
        return True
    if u'оборуд' in category or 'equipment' in category:
        return True
    return False


def connected_duct_ids(data, element_id):
    result = []
    for connected_id in data['graph'].get(element_id, []):
        if connected_id in data.get('duct_ids', []) and connected_id not in result:
            result.append(connected_id)
    return result


def unique_ids(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def find_path_between(graph, start_id, end_id):
    return network.find_path_between(graph, start_id, end_id)


def calculate_element_path(path_ids, data, settings, zeta_data):
    rows = []
    row_by_duct_id = {}
    duct_ids = []
    fitting_ids = []
    for element_id in path_ids:
        if element_id in data.get('duct_ids', []):
            duct = data['elements_by_id'][element_id]
            row = duct_row(duct, len(rows), settings)
            rows.append(row)
            row_by_duct_id[element_id] = row
            duct_ids.append(element_id)
    for index in range(len(path_ids)):
        element_id = path_ids[index]
        if element_id in data.get('duct_ids', []):
            continue
        element = data['elements_by_id'][element_id]
        target_duct_id = target_duct_for_local(path_ids, index, data)
        if target_duct_id is None:
            continue
        row = row_by_duct_id.get(target_duct_id)
        if not row:
            continue
        previous_duct = nearest_duct_before(path_ids, index, data)
        next_duct = nearest_duct_after(path_ids, index, data)
        add_local_to_row(row, element, previous_duct, next_duct, data['elements_by_id'][target_duct_id], settings, zeta_data)
        if element_id not in data.get('terminal_ids', []) and element_id not in data.get('equipment_ids', []):
            fitting_ids.append(element_id)
    for row in rows:
        row['total_pa'] = row.get('friction_pa', 0.0) + row.get('local_pa', 0.0)
    totals = make_totals(rows, 0.0)
    return {
        'path_ids': path_ids,
        'rows': rows,
        'duct_ids': duct_ids,
        'fitting_ids': unique_ids(fitting_ids),
        'start_element_id': path_ids[0] if path_ids else None,
        'total_pa': totals.get('total_pa', 0.0),
        'friction_pa': totals.get('friction_pa', 0.0),
        'local_pa': totals.get('local_pa', 0.0)
    }


def target_duct_for_local(path_ids, index, data):
    previous_id = nearest_duct_id_before(path_ids, index, data)
    next_id = nearest_duct_id_after(path_ids, index, data)
    if previous_id is None and next_id is not None:
        return next_id
    if previous_id is not None:
        return previous_id
    return next_id


def nearest_duct_id_before(path_ids, index, data):
    for item in range(index - 1, -1, -1):
        element_id = path_ids[item]
        if element_id in data.get('duct_ids', []):
            return element_id
    return None


def nearest_duct_id_after(path_ids, index, data):
    for item in range(index + 1, len(path_ids)):
        element_id = path_ids[item]
        if element_id in data.get('duct_ids', []):
            return element_id
    return None


def nearest_duct_before(path_ids, index, data):
    duct_id = nearest_duct_id_before(path_ids, index, data)
    if duct_id is None:
        return None
    return data['elements_by_id'][duct_id]


def nearest_duct_after(path_ids, index, data):
    duct_id = nearest_duct_id_after(path_ids, index, data)
    if duct_id is None:
        return None
    return data['elements_by_id'][duct_id]


def add_local_to_row(row, element, previous_duct, next_duct, pressure_duct, settings, zeta_data):
    value = zeta.fitting_zeta(element, previous_duct, next_duct, zeta_data)
    pressure = value * dynamic_pressure(pressure_duct, settings)
    row['local_zeta'] += value
    row['local_pa'] += pressure
    row['fittings'].append({'id': element.Id.IntegerValue, 'kind': zeta.fitting_kind(element), 'zeta': value, 'pressure_pa': pressure})
    row['element_ids'].append(element.Id.IntegerValue)
    append_note(row, element, value)


def choose_critical_path(paths):
    best = None
    best_pressure = -1.0
    best_length = -1.0
    for path in paths:
        pressure = path.get('total_pa', 0.0)
        length = make_totals(path.get('rows', []), 0.0).get('length_m', 0.0)
        if pressure > best_pressure + 0.000001:
            best_pressure = pressure
            best_length = length
            best = path
        elif abs(pressure - best_pressure) <= 0.000001 and length > best_length:
            best_length = length
            best = path
    return best


def make_totals(rows, reserve_percent):
    total_pa = sum([row.get('total_pa', 0.0) for row in rows])
    return {
        'length_m': sum([row.get('length_m', 0.0) for row in rows]),
        'friction_pa': sum([row.get('friction_pa', 0.0) for row in rows]),
        'local_pa': sum([row.get('local_pa', 0.0) for row in rows]),
        'total_pa': total_pa,
        'total_with_reserve_pa': total_pa * (1.0 + reserve_percent / 100.0),
        'reserve_percent': reserve_percent
    }


def make_diagnostics(data, starts, critical, rows, totals):
    first_rows = []
    for row in rows[:5]:
        first_rows.append({'duct_id': row.get('duct_id'), 'flow_m3s': row.get('flow_m3s', 0.0), 'velocity_ms': row.get('velocity_ms', 0.0), 'friction_pa': row.get('friction_pa', 0.0)})
    return {
        'elements_count': len(data.get('elements_by_id', {})),
        'ducts_count': len(data.get('duct_ids', [])),
        'candidates_count': len(starts),
        'best_path_len': len(critical.get('path_ids', [])),
        'friction_pa': totals.get('friction_pa', 0.0),
        'local_pa': totals.get('local_pa', 0.0),
        'total_pa': totals.get('total_pa', 0.0),
        'first_rows': first_rows
    }


def append_note(row, element, value):
    text = local_resistance_name(element) + ' z=' + zeta.format_number(value)
    if row.get('note'):
        row['note'] += '; ' + text
    else:
        row['note'] = text


def local_resistance_name(element):
    kind = zeta.fitting_kind(element)
    if kind == 'elbow':
        return u'Отвод ' + str(zeta.elbow_angle(element)) + u'°'
    names = {
        'transition': u'Переход',
        'tee': u'Тройник',
        'cross': u'Крестовина',
        'grille': u'Решетка',
        'hood': u'Зонт',
        'deflector': u'Дефлектор',
        'equipment': u'Оборудование',
        'inlet': u'Вход',
        'outlet': u'Выход',
        'cap': u'Заглушка',
        'damper': u'Клапан',
        'fire_damper': u'Противопожарный клапан',
        'backdraft_damper': u'Обратный клапан'
    }
    return names.get(kind, revit_utils.element_name(element) or revit_utils.type_name(element) or kind)


def element_display_name(data, element_id):
    element = data.get('elements_by_id', {}).get(element_id)
    if element is None:
        return ''
    return revit_utils.element_name(element) or revit_utils.type_name(element) or revit_utils.category_name(element)
