# -*- coding: utf-8 -*-
from ventcalc import config
from ventcalc import network
from ventcalc import revit_utils
from ventcalc import zeta


def dynamic_pressure(duct, settings):
    density = config.to_float(settings.get('air_density', 1.2), 1.2)
    flow = revit_utils.duct_flow_m3s(duct)
    area = revit_utils.duct_area_m2(duct)
    if area <= 0:
        return 0.0
    velocity = flow / area
    return density * velocity * velocity / 2.0


def duct_row(duct, index, settings):
    length = revit_utils.duct_length_m(duct)
    flow = revit_utils.duct_flow_m3s(duct)
    area = revit_utils.duct_area_m2(duct)
    velocity = 0.0
    if area > 0:
        velocity = flow / area
    diameter = revit_utils.hydraulic_diameter_m(duct)
    friction_factor = config.to_float(settings.get('friction_factor', 0.02), 0.02)
    density = config.to_float(settings.get('air_density', 1.2), 1.2)
    friction = 0.0
    if diameter > 0:
        friction = friction_factor * length / diameter * density * velocity * velocity / 2.0
    return {
        'index': index,
        'duct_id': duct.Id.IntegerValue,
        'name': revit_utils.element_name(duct) or revit_utils.type_name(duct),
        'system': revit_utils.system_name(duct),
        'length_m': length,
        'flow_m3s': flow,
        'area_m2': area,
        'velocity_ms': velocity,
        'diameter_m': diameter,
        'friction_pa': friction,
        'local_zeta': 0.0,
        'local_pa': 0.0,
        'fittings': [],
        'total_pa': friction
    }


def calculate(doc, selected_ids=None):
    settings = config.load_settings()
    zeta_data = config.load_zeta()
    ducts, fittings, graph, edges = network.collect_network(doc, selected_ids)
    rows_by_id = {}
    ordered_ids = sorted(ducts.keys())
    for index, duct_id in enumerate(ordered_ids):
        rows_by_id[duct_id] = duct_row(ducts[duct_id], index + 1, settings)
    used_fittings = set()
    for component in network.connected_components(graph):
        critical_path = find_critical_path(component, graph, edges, ducts, rows_by_id, settings, zeta_data)
        apply_path_locals(critical_path, edges, ducts, rows_by_id, settings, zeta_data, used_fittings)
    for fitting_id in fittings:
        if fitting_id in used_fittings:
            continue
        fitting = fittings[fitting_id]
        nearest = revit_utils.nearest_connected_duct(fitting, ducts)
        if nearest:
            add_fitting_to_row(rows_by_id[nearest.Id.IntegerValue], fitting, None, nearest, settings, zeta_data)
            used_fittings.add(fitting_id)
    rows = [rows_by_id[duct_id] for duct_id in ordered_ids]
    reserve_percent = config.to_float(settings.get('reserve_percent', 10.0), 10.0)
    for row in rows:
        row['total_pa'] = row['friction_pa'] + row['local_pa']
        row['total_with_reserve_pa'] = row['total_pa'] * (1.0 + reserve_percent / 100.0)
    totals = {
        'friction_pa': sum([row['friction_pa'] for row in rows]),
        'local_pa': sum([row['local_pa'] for row in rows]),
        'total_pa': sum([row['total_pa'] for row in rows]),
        'total_with_reserve_pa': sum([row['total_with_reserve_pa'] for row in rows]),
        'reserve_percent': reserve_percent
    }
    return {'rows': rows, 'totals': totals, 'settings': settings}


def find_critical_path(component, graph, edges, ducts, rows_by_id, settings, zeta_data):
    best_path = list(component)
    best_pressure = -1.0
    paths = network.all_leaf_paths(graph, component)
    for path in paths:
        pressure = path_pressure(path, edges, ducts, rows_by_id, settings, zeta_data)
        if pressure > best_pressure:
            best_path = path
            best_pressure = pressure
    return best_path


def path_pressure(path, edges, ducts, rows_by_id, settings, zeta_data):
    pressure = 0.0
    for duct_id in path:
        pressure += rows_by_id[duct_id]['friction_pa']
    for index in range(len(path) - 1):
        fitting = edges.get((path[index], path[index + 1]))
        if fitting:
            duct = ducts[path[index + 1]]
            pressure += zeta.fitting_zeta(fitting, ducts[path[index]], ducts[path[index + 1]], zeta_data) * dynamic_pressure(duct, settings)
    return pressure


def apply_path_locals(path, edges, ducts, rows_by_id, settings, zeta_data, used_fittings):
    for index in range(len(path) - 1):
        fitting = edges.get((path[index], path[index + 1]))
        if fitting:
            target_duct = ducts[path[index + 1]]
            add_fitting_to_row(rows_by_id[target_duct.Id.IntegerValue], fitting, ducts[path[index]], target_duct, settings, zeta_data)
            used_fittings.add(fitting.Id.IntegerValue)


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
