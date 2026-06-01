# -*- coding: utf-8 -*-
import math
import Autodesk.Revit.DB as DB

DUCT_CATEGORY = DB.BuiltInCategory.OST_DuctCurves
FITTING_CATEGORY = DB.BuiltInCategory.OST_DuctFitting
AIR_ELEMENT_CATEGORIES = [
    DB.BuiltInCategory.OST_DuctFitting,
    DB.BuiltInCategory.OST_DuctAccessory,
    DB.BuiltInCategory.OST_DuctTerminal,
    DB.BuiltInCategory.OST_MechanicalEquipment
]


def get_param(element, names):
    if not isinstance(names, list) and not isinstance(names, tuple):
        names = [names]
    for name in names:
        param = element.LookupParameter(name)
        if param:
            return param
    return None


def param_text(element, names, default_value=''):
    param = get_param(element, names)
    if not param:
        return default_value
    value = param.AsString()
    if value is None:
        value = param.AsValueString()
    if value is None:
        return default_value
    return value


def param_double(element, names, default_value=0.0):
    param = get_param(element, names)
    if not param:
        return default_value
    try:
        return param.AsDouble()
    except Exception:
        text = param.AsValueString()
        if text:
            text = text.replace(',', '.')
            number = ''
            for char in text:
                if char in '0123456789.-':
                    number += char
            try:
                return float(number)
            except Exception:
                return default_value
    return default_value


def set_param_text(element, names, value):
    param = get_param(element, names)
    if not param or param.IsReadOnly:
        return False
    param.Set(value)
    return True


def element_name(element):
    try:
        name = element.Name
        if name:
            return name
    except Exception:
        name = ''
    try:
        type_element = element.Document.GetElement(element.GetTypeId())
        if type_element:
            return type_element.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except Exception:
        return ''
    return ''


def type_name(element):
    try:
        type_element = element.Document.GetElement(element.GetTypeId())
        if type_element:
            param = type_element.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
            if param:
                value = param.AsString()
                if value:
                    return value
            return type_element.Name
    except Exception:
        return ''
    return ''


def family_name(element):
    try:
        type_element = element.Document.GetElement(element.GetTypeId())
        if type_element and hasattr(type_element, 'FamilyName'):
            value = type_element.FamilyName
            if value:
                return value
    except Exception:
        type_element = None
    try:
        type_element = element.Document.GetElement(element.GetTypeId())
        if type_element and hasattr(type_element, 'Family') and type_element.Family:
            return type_element.Family.Name
    except Exception:
        return ''
    return ''


def category_name(element):
    try:
        if element.Category:
            return element.Category.Name
    except Exception:
        return ''
    return ''


def comments(element):
    return param_text(element, ['Комментарии', 'Comment', 'Comments'], '')


def set_comments(element, value):
    return set_param_text(element, ['Комментарии', 'Comment', 'Comments'], value)


def feet_to_m(value):
    return value * 0.3048


def sqft_to_m2(value):
    return value * 0.09290304


def cfm_to_m3s(value):
    return value * 0.00047194745


def cfs_to_m3s(value):
    return value * 0.028316846592


def internal_flow_to_m3s(value):
    return cfs_to_m3s(value)


def angle_to_degrees(value):
    if value is None:
        return None
    if abs(value) <= 6.4:
        return abs(value) * 180.0 / math.pi
    return abs(value)


def round_angle(value):
    if value is None:
        return None
    degrees = angle_to_degrees(value)
    variants = [15, 30, 45, 60, 90]
    best = variants[0]
    diff = abs(degrees - best)
    for item in variants:
        item_diff = abs(degrees - item)
        if item_diff < diff:
            best = item
            diff = item_diff
    if diff <= 10:
        return best
    return None


def collector(doc, category):
    return DB.FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType().ToElements()


def ducts(doc):
    return collector(doc, DUCT_CATEGORY)


def fittings(doc):
    return collector(doc, FITTING_CATEGORY)


def air_network_elements(doc):
    result = []
    seen = set()
    for category in AIR_ELEMENT_CATEGORIES:
        try:
            elements = collector(doc, category)
        except Exception:
            elements = []
        for element in elements:
            element_id_value = element.Id.IntegerValue
            if element_id_value not in seen:
                seen.add(element_id_value)
                result.append(element)
    return result


def is_duct(element):
    try:
        return element.Category and element.Category.Id.IntegerValue == int(DUCT_CATEGORY)
    except Exception:
        return False


def is_air_network_element(element):
    try:
        category_value = element.Category.Id.IntegerValue
    except Exception:
        return False
    for category in AIR_ELEMENT_CATEGORIES:
        if category_value == int(category):
            return True
    return False


def connectors(element):
    result = []
    manager = None
    try:
        manager = element.ConnectorManager
    except Exception:
        manager = None
    if manager is None:
        try:
            manager = element.MEPModel.ConnectorManager
        except Exception:
            manager = None
    if manager is None:
        return result
    try:
        iterator = manager.Connectors.ForwardIterator()
        while iterator.MoveNext():
            result.append(iterator.Current)
    except Exception:
        for connector in manager.Connectors:
            result.append(connector)
    return result


def connected_elements(element):
    result = []
    seen = set()
    for connector in connectors(element):
        try:
            refs = connector.AllRefs
        except Exception:
            refs = []
        for ref in refs:
            owner = ref.Owner
            if owner and owner.Id.IntegerValue != element.Id.IntegerValue and owner.Id.IntegerValue not in seen:
                seen.add(owner.Id.IntegerValue)
                result.append(owner)
    return result


def distance(p1, p2):
    return p1.DistanceTo(p2)


def element_center(element):
    try:
        location = element.Location
        if hasattr(location, 'Curve') and location.Curve:
            return location.Curve.Evaluate(0.5, True)
        if hasattr(location, 'Point') and location.Point:
            return location.Point
    except Exception:
        location = None
    bbox = element.get_BoundingBox(None)
    if bbox:
        return DB.XYZ((bbox.Min.X + bbox.Max.X) / 2.0, (bbox.Min.Y + bbox.Max.Y) / 2.0, (bbox.Min.Z + bbox.Max.Z) / 2.0)
    return DB.XYZ(0, 0, 0)


def nearest_connected_duct(fitting, duct_ids=None):
    best = None
    best_distance = None
    center = element_center(fitting)
    for element in connected_elements(fitting):
        if is_duct(element):
            if duct_ids and element.Id.IntegerValue not in duct_ids:
                continue
            item_distance = distance(center, element_center(element))
            if best is None or item_distance < best_distance:
                best = element
                best_distance = item_distance
    return best


def connected_ducts(element, allowed_ids=None):
    result = []
    seen = set()
    for connected in connected_elements(element):
        if is_duct(connected):
            element_id_value = connected.Id.IntegerValue
            if allowed_ids and element_id_value not in allowed_ids:
                continue
            if element_id_value not in seen:
                seen.add(element_id_value)
                result.append(connected)
    return result


def duct_area_m2(duct):
    value = param_double(duct, ['Площадь', 'ADSK_Площадь', 'Area'], 0.0)
    if value > 0:
        return sqft_to_m2(value)
    width = param_double(duct, ['Ширина', 'Width'], 0.0)
    height = param_double(duct, ['Высота', 'Height'], 0.0)
    diameter = param_double(duct, ['Диаметр', 'Diameter'], 0.0)
    if diameter > 0:
        d = feet_to_m(diameter)
        return math.pi * d * d / 4.0
    if width > 0 and height > 0:
        return feet_to_m(width) * feet_to_m(height)
    return 0.0


def duct_length_m(duct):
    value = param_double(duct, ['Длина', 'Length'], 0.0)
    if value > 0:
        return feet_to_m(value)
    try:
        return feet_to_m(duct.Location.Curve.Length)
    except Exception:
        return 0.0


def duct_flow_m3s(duct):
    value = param_double(duct, ['Расход', 'ADSK_Расход воздуха', 'Flow'], 0.0)
    if value > 0:
        return internal_flow_to_m3s(value)
    return 0.0


def hydraulic_diameter_m(duct):
    area = duct_area_m2(duct)
    width = param_double(duct, ['Ширина', 'Width'], 0.0)
    height = param_double(duct, ['Высота', 'Height'], 0.0)
    diameter = param_double(duct, ['Диаметр', 'Diameter'], 0.0)
    if diameter > 0:
        return feet_to_m(diameter)
    if width > 0 and height > 0:
        w = feet_to_m(width)
        h = feet_to_m(height)
        if w + h > 0:
            return 2.0 * w * h / (w + h)
    if area > 0:
        return math.sqrt(4.0 * area / math.pi)
    return 0.0


def element_id(element):
    return element.Id.IntegerValue


def system_name(element):
    return param_text(element, ['Имя системы', 'System Name', 'System Classification'], '')


def duct_size_text(duct):
    diameter = param_double(duct, ['Диаметр', 'Diameter'], 0.0)
    width = param_double(duct, ['Ширина', 'Width'], 0.0)
    height = param_double(duct, ['Высота', 'Height'], 0.0)
    if diameter > 0:
        return unicode_mm(feet_to_m(diameter) * 1000.0)
    if width > 0 and height > 0:
        return unicode_mm(feet_to_m(width) * 1000.0) + 'x' + unicode_mm(feet_to_m(height) * 1000.0)
    return param_text(duct, ['Размер', 'Size'], '')


def unicode_mm(value):
    try:
        return str(int(round(value)))
    except Exception:
        return ''
