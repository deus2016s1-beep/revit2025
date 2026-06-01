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


def dynamic_pressure(duct, settings):
    values = duct_values(duct, settings)
    return dynamic_pressure_by_velocity(values.get('velocity_ms', 0.0), settings)


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
    r_pa_m = 0.0
    if diameter > 0:
        r_pa_m = lambda_value / diameter * dynamic_pressure_by_velocity(velocity, settings)
    friction = r_pa_m * length
    return {
        'length_m': length,
        'flow_m3s': flow,
        'area_m2': area,
        'velocity_ms': velocity,
        'diameter_m': diameter,
        're': re_value,
        'lambda': lambda_value,
        'r_pa_m': r_pa_m,
        'friction_pa': friction
    }


def duct_row(duct, index, settings):
    values = duct_values(duct, settings)
    row = {
        'index': index,
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
    candidates = path_candidates(data, end_duct_ids)
    path = choose_path(data, end_duct_ids, settings, zeta_data, candidates)
    if not path:
        raise Exception(u'Критическая трасса до выбранного конечного элемента не найдена. Проверьте соединения воздуховодов и фитингов')
    rows, fitting_ids = make_rows(path, data, settings, zeta_data)
    if not rows:
        raise Exception(u'Трасса найдена, но расчетные участки не сформированы')
    reserve_percent = config.to_float(settings.get('reserve_percent', 10.0), 10.0)
    for row in rows:
        row['total_pa'] = row.get('friction_pa', 0.0) + row.get('local_pa', 0.0)
        row['total_with_reserve_pa'] = row['total_pa'] * (1.0 + reserve_percent / 100.0)
    totals = {
        'friction_pa': sum([row.get('friction_pa', 0.0) for row in rows]),
        'local_pa': sum([row.get('local_pa', 0.0) for row in rows]),
        'total_pa': sum([row.get('total_pa', 0.0) for row in rows]),
        'total_with_reserve_pa': sum([row.get('total_with_reserve_pa', 0.0) for row in rows]),
        'reserve_percent': reserve_percent
    }
    diagnostics = make_diagnostics(data, end_duct_ids, candidates, path, rows, totals)
    return {
        'rows': rows,
        'totals': totals,
        'settings': settings,
        'critical_path': path,
        'critical_duct_ids': path,
        'critical_fitting_ids': fitting_ids,
        'end_element_id': end_element.Id.IntegerValue,
        'diagnostics': diagnostics
    }



def make_diagnostics(data, end_duct_ids, candidates, path, rows, totals):
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
        'candidates_count': len(candidates),
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


def path_candidates(data, end_duct_ids):
    graph = data['graph']
    candidates = network.terminal_start_duct_ids(data, end_duct_ids)
    if not candidates:
        for component in network.connected_components(graph):
            for duct_id in component:
                if duct_id not in end_duct_ids and len(graph.get(duct_id, [])) <= 1:
                    candidates.append(duct_id)
    return candidates


def choose_path(data, end_duct_ids, settings, zeta_data, candidates=None):
    graph = data['graph']
    if candidates is None:
        candidates = path_candidates(data, end_duct_ids)
    best_path = []
    best_pressure = -1.0
    for start_id in candidates:
        for end_id in end_duct_ids:
            path = network.shortest_path(graph, start_id, end_id)
            if not path and start_id == end_id:
                path = [start_id]
            if path:
                pressure = path_pressure(path, data, settings, zeta_data)
                if pressure > best_pressure:
                    best_pressure = pressure
                    best_path = path
    return best_path


def path_pressure(path, data, settings, zeta_data):
    pressure = 0.0
    ducts = data['ducts']
    for duct_id in path:
        pressure += duct_values(ducts[duct_id], settings).get('friction_pa', 0.0)
    for index in range(len(path) - 1):
        fitting = data['edges'].get((path[index], path[index + 1]))
        if fitting:
            pressure += fitting_pressure(fitting, ducts[path[index]], ducts[path[index + 1]], settings, zeta_data)
    return pressure


def make_rows(path, data, settings, zeta_data):
    rows = []
    fitting_ids = []
    ducts = data['ducts']
    for index in range(len(path)):
        duct_id = path[index]
        row = duct_row(ducts[duct_id], index + 1, settings)
        if index > 0:
            previous_duct = ducts[path[index - 1]]
            fitting = data['edges'].get((path[index - 1], duct_id))
            if fitting:
                add_fitting_to_row(row, fitting, previous_duct, ducts[duct_id], settings, zeta_data)
                fitting_ids.append(fitting.Id.IntegerValue)
        rows.append(row)
    return rows, fitting_ids


def fitting_pressure(fitting, previous_duct, next_duct, settings, zeta_data):
    value = zeta.fitting_zeta(fitting, previous_duct, next_duct, zeta_data)
    return value * dynamic_pressure(next_duct, settings)


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
    note = zeta.format_number(value) + ' ' + (revit_utils.element_name(fitting) or revit_utils.type_name(fitting) or kind)
    if row.get('note'):
        row['note'] += '; ' + note
    else:
        row['note'] = note
