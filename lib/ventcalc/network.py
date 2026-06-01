# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import revit_utils


def element_key(element):
    return element.Id.IntegerValue


def is_duct(element):
    return element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DuctCurves)


def is_fitting(element):
    return element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DuctFitting)


def collect_network(doc, selected_ids=None):
    ducts = {}
    fittings = {}
    for duct in revit_utils.ducts(doc):
        if selected_ids and duct.Id.IntegerValue not in selected_ids:
            continue
        ducts[element_key(duct)] = duct
    for fitting in revit_utils.fittings(doc):
        fittings[element_key(fitting)] = fitting
    graph = {}
    edges = {}
    for duct_id in ducts:
        graph[duct_id] = []
    for fitting_id in fittings:
        fitting = fittings[fitting_id]
        linked_ducts = []
        for element in revit_utils.connected_elements(fitting):
            if is_duct(element) and element.Id.IntegerValue in ducts:
                linked_ducts.append(element.Id.IntegerValue)
        for i in range(len(linked_ducts)):
            for j in range(i + 1, len(linked_ducts)):
                a = linked_ducts[i]
                b = linked_ducts[j]
                if b not in graph[a]:
                    graph[a].append(b)
                if a not in graph[b]:
                    graph[b].append(a)
                edges[(a, b)] = fitting
                edges[(b, a)] = fitting
    return ducts, fittings, graph, edges


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
