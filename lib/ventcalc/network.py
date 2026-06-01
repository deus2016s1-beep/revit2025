# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import revit_utils

DUCT_CATEGORY = int(DB.BuiltInCategory.OST_DuctCurves)
FITTING_CATEGORY = int(DB.BuiltInCategory.OST_DuctFitting)
ACCESSORY_CATEGORY = int(DB.BuiltInCategory.OST_DuctAccessory)
TERMINAL_CATEGORY = int(DB.BuiltInCategory.OST_DuctTerminal)
EQUIPMENT_CATEGORY = int(DB.BuiltInCategory.OST_MechanicalEquipment)


def element_key(element):
    return element.Id.IntegerValue


def element_category_id(element):
    try:
        if element.Category:
            return element.Category.Id.IntegerValue
    except Exception:
        return None
    return None


def is_duct(element):
    return element_category_id(element) == DUCT_CATEGORY


def is_fitting(element):
    category_id = element_category_id(element)
    return category_id == FITTING_CATEGORY or category_id == ACCESSORY_CATEGORY


def is_terminal(element):
    return element_category_id(element) == TERMINAL_CATEGORY


def is_equipment(element):
    return element_category_id(element) == EQUIPMENT_CATEGORY


def is_network_element(element):
    category_id = element_category_id(element)
    return category_id in [DUCT_CATEGORY, FITTING_CATEGORY, ACCESSORY_CATEGORY, TERMINAL_CATEGORY, EQUIPMENT_CATEGORY]


def network_elements(doc):
    result = []
    seen = set()
    categories = [
        DB.BuiltInCategory.OST_DuctCurves,
        DB.BuiltInCategory.OST_DuctFitting,
        DB.BuiltInCategory.OST_DuctAccessory,
        DB.BuiltInCategory.OST_DuctTerminal,
        DB.BuiltInCategory.OST_MechanicalEquipment
    ]
    for category in categories:
        try:
            elements = revit_utils.collector(doc, category)
        except Exception:
            elements = []
        for element in elements:
            element_id = element_key(element)
            if element_id not in seen:
                seen.add(element_id)
                result.append(element)
    return result


def build_element_graph(doc):
    elements_by_id = {}
    graph = {}
    duct_ids = []
    terminal_ids = []
    fitting_ids = []
    accessory_ids = []
    equipment_ids = []
    for element in network_elements(doc):
        element_id = element_key(element)
        elements_by_id[element_id] = element
        graph[element_id] = []
        category_id = element_category_id(element)
        if category_id == DUCT_CATEGORY:
            duct_ids.append(element_id)
        elif category_id == FITTING_CATEGORY:
            fitting_ids.append(element_id)
        elif category_id == ACCESSORY_CATEGORY:
            accessory_ids.append(element_id)
        elif category_id == TERMINAL_CATEGORY:
            terminal_ids.append(element_id)
        elif category_id == EQUIPMENT_CATEGORY:
            equipment_ids.append(element_id)
    for element_id in elements_by_id:
        element = elements_by_id[element_id]
        for connected in revit_utils.connected_elements(element):
            connected_id = connected.Id.IntegerValue
            if connected_id in elements_by_id and connected_id != element_id:
                add_graph_edge(graph, element_id, connected_id)
    return {
        'elements_by_id': elements_by_id,
        'graph': graph,
        'duct_ids': duct_ids,
        'terminal_ids': terminal_ids,
        'fitting_ids': fitting_ids,
        'accessory_ids': accessory_ids,
        'equipment_ids': equipment_ids
    }


def add_graph_edge(graph, a, b):
    if a not in graph:
        graph[a] = []
    if b not in graph:
        graph[b] = []
    if b not in graph[a]:
        graph[a].append(b)
    if a not in graph[b]:
        graph[b].append(a)


def find_path_between(graph, start_id, end_id):
    if start_id == end_id:
        return [start_id]
    queue = [(start_id, [start_id])]
    visited = set([start_id])
    while queue:
        current, path = queue.pop(0)
        for next_id in graph.get(current, []):
            if next_id in visited:
                continue
            next_path = path + [next_id]
            if next_id == end_id:
                return next_path
            visited.add(next_id)
            queue.append((next_id, next_path))
    return []


def build_network(doc):
    data = build_element_graph(doc)
    ducts = {}
    fittings = {}
    graph = {}
    edges = {}
    for duct_id in data['duct_ids']:
        ducts[duct_id] = data['elements_by_id'][duct_id]
        graph[duct_id] = []
    for element_id in data['fitting_ids'] + data['accessory_ids']:
        element = data['elements_by_id'][element_id]
        linked_ducts = []
        for connected_id in data['graph'].get(element_id, []):
            if connected_id in ducts and connected_id not in linked_ducts:
                linked_ducts.append(connected_id)
        if linked_ducts:
            fittings[element_id] = element
        for i in range(len(linked_ducts)):
            for j in range(i + 1, len(linked_ducts)):
                add_duct_edge(graph, edges, linked_ducts[i], linked_ducts[j], element)
    return {
        'ducts': ducts,
        'fittings': fittings,
        'terminals': dict([(item, data['elements_by_id'][item]) for item in data['terminal_ids'] + data['equipment_ids']]),
        'graph': graph,
        'edges': edges,
        'duct_to_end_elements': duct_to_end_elements(data)
    }


def duct_to_end_elements(data):
    result = {}
    for duct_id in data['duct_ids']:
        result[duct_id] = []
    for element_id in data['terminal_ids'] + data['equipment_ids']:
        for connected_id in data['graph'].get(element_id, []):
            if connected_id in result:
                result[connected_id].append(data['elements_by_id'][element_id])
    return result


def collect_network(doc, selected_ids=None):
    data = build_network(doc)
    if selected_ids:
        ducts = {}
        for duct_id in data['ducts']:
            if duct_id in selected_ids:
                ducts[duct_id] = data['ducts'][duct_id]
        graph = {}
        edges = {}
        for duct_id in ducts:
            graph[duct_id] = []
        for key in data['edges']:
            a, b = key
            if a in ducts and b in ducts:
                add_duct_edge(graph, edges, a, b, data['edges'][key])
        return ducts, data['fittings'], graph, edges
    return data['ducts'], data['fittings'], data['graph'], data['edges']


def add_duct_edge(graph, edges, a, b, fitting):
    if a not in graph:
        graph[a] = []
    if b not in graph:
        graph[b] = []
    if b not in graph[a]:
        graph[a].append(b)
    if a not in graph[b]:
        graph[b].append(a)
    edges[(a, b)] = fitting
    edges[(b, a)] = fitting


def connected_components(graph):
    visited = set()
    result = []
    for node in graph:
        if node in visited:
            continue
        stack = [node]
        component = []
        visited.add(node)
        while stack:
            current = stack.pop()
            component.append(current)
            for next_node in graph.get(current, []):
                if next_node not in visited:
                    visited.add(next_node)
                    stack.append(next_node)
        result.append(component)
    return result


def leaves(graph, component):
    result = []
    for node in component:
        if len(graph.get(node, [])) <= 1:
            result.append(node)
    if not result:
        result = list(component)
    return result


def shortest_path(graph, start, finish):
    return find_path_between(graph, start, finish)


def all_leaf_paths(graph, component):
    result = []
    component_leaves = leaves(graph, component)
    if len(component_leaves) == 1:
        return [[component_leaves[0]]]
    for i in range(len(component_leaves)):
        for j in range(i + 1, len(component_leaves)):
            path = shortest_path(graph, component_leaves[i], component_leaves[j])
            if path:
                result.append(path)
    return result


def endpoint_duct_ids(data, element):
    result = []
    if element is None:
        return result
    element_id = element.Id.IntegerValue
    graph = data.get('graph', {})
    if element_id in data.get('duct_ids', []):
        return [element_id]
    for connected_id in graph.get(element_id, []):
        if connected_id in data.get('duct_ids', []) and connected_id not in result:
            result.append(connected_id)
    return result


def terminal_start_duct_ids(data, end_duct_ids):
    result = []
    for terminal_id in data.get('terminal_ids', []) + data.get('equipment_ids', []):
        for duct_id in endpoint_duct_ids(data, data['elements_by_id'][terminal_id]):
            if duct_id not in end_duct_ids and duct_id not in result:
                result.append(duct_id)
    return result
