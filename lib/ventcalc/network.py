# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import revit_utils
from ventcalc import zeta


def element_key(element):
    return element.Id.IntegerValue


def is_duct(element):
    return revit_utils.is_duct(element)


def is_network_element(element):
    return revit_utils.is_air_network_element(element)


def build_network(doc):
    ducts = {}
    fittings = {}
    terminals = {}
    graph = {}
    edges = {}
    duct_to_end_elements = {}
    for duct in revit_utils.ducts(doc):
        duct_id = element_key(duct)
        ducts[duct_id] = duct
        graph[duct_id] = []
        duct_to_end_elements[duct_id] = []
    for element in revit_utils.air_network_elements(doc):
        element_id = element_key(element)
        linked_ducts = []
        for connected in revit_utils.connected_elements(element):
            if is_duct(connected) and connected.Id.IntegerValue in ducts:
                duct_id = connected.Id.IntegerValue
                if duct_id not in linked_ducts:
                    linked_ducts.append(duct_id)
        if len(linked_ducts) <= 1:
            terminals[element_id] = element
            for duct_id in linked_ducts:
                duct_to_end_elements.setdefault(duct_id, []).append(element)
        else:
            fittings[element_id] = element
            for i in range(len(linked_ducts)):
                for j in range(i + 1, len(linked_ducts)):
                    add_edge(graph, edges, linked_ducts[i], linked_ducts[j], element)
    return {
        'ducts': ducts,
        'fittings': fittings,
        'terminals': terminals,
        'graph': graph,
        'edges': edges,
        'duct_to_end_elements': duct_to_end_elements
    }


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
                add_edge(graph, edges, a, b, data['edges'][key])
        return ducts, data['fittings'], graph, edges
    return data['ducts'], data['fittings'], data['graph'], data['edges']


def add_edge(graph, edges, a, b, fitting):
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
    queue = [(start, [start])]
    visited = set([start])
    while queue:
        current, path = queue.pop(0)
        if current == finish:
            return path
        for next_node in graph.get(current, []):
            if next_node not in visited:
                visited.add(next_node)
                queue.append((next_node, path + [next_node]))
    return []


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
    if is_duct(element):
        return [element.Id.IntegerValue]
    for connected in revit_utils.connected_elements(element):
        if is_duct(connected) and connected.Id.IntegerValue in data['ducts']:
            duct_id = connected.Id.IntegerValue
            if duct_id not in result:
                result.append(duct_id)
    return result


def terminal_start_duct_ids(data, end_duct_ids):
    result = []
    for duct_id in data['ducts']:
        if duct_id in end_duct_ids:
            continue
        end_elements = data['duct_to_end_elements'].get(duct_id, [])
        if end_elements:
            for element in end_elements:
                if zeta.is_normal_terminal(element):
                    result.append(duct_id)
                    break
        elif len(data['graph'].get(duct_id, [])) <= 1:
            result.append(duct_id)
    unique = []
    for duct_id in result:
        if duct_id not in unique:
            unique.append(duct_id)
    return unique
