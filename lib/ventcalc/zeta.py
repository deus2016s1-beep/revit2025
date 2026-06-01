# -*- coding: utf-8 -*-
import re
from ventcalc import config
from ventcalc import revit_utils

KEYS = ['z_narrow', 'z_expand', 'z_pass', 'z_branch', 'zeta', 'z']
SIMPLE_KINDS = ['tap', 'offset', 'cap', 'damper', 'fire_damper', 'backdraft_damper', 'inlet', 'outlet', 'grille', 'hood', 'deflector', 'other', 'unknown']


def parse_comment(text):
    result = {}
    if not text:
        return result
    for key in KEYS:
        pattern = r'(^|[^A-Za-z_])' + key + r'\s*=\s*([-+]?[0-9]+([\.,][0-9]+)?)'
        match = re.search(pattern, text, re.I)
        if match:
            result[key] = config.to_float(match.group(2), 0.0)
    return result


def has_zeta_values(element):
    values = parse_comment(revit_utils.comments(element))
    for key in KEYS:
        if key in values:
            return True
    return False


def format_comment(kind, values):
    if kind == 'transition':
        return 'z_narrow=' + format_number(values.get('z_narrow', 0.0)) + '; z_expand=' + format_number(values.get('z_expand', 0.0))
    if kind == 'tee' or kind == 'cross':
        return 'z_pass=' + format_number(values.get('z_pass', 0.0)) + '; z_branch=' + format_number(values.get('z_branch', 0.0))
    return 'z=' + format_number(values.get('z', 0.0))


def format_number(value):
    try:
        text = ('%.3f' % float(value)).rstrip('0').rstrip('.')
    except Exception:
        text = '0'
    if text == '' or text == '-0':
        return '0'
    return text


def fitting_text(fitting):
    parts = [
        revit_utils.param_text(fitting, ['ADSK_Наименование', 'Наименование', 'Name'], ''),
        revit_utils.element_name(fitting),
        revit_utils.type_name(fitting),
        revit_utils.family_name(fitting),
        revit_utils.category_name(fitting),
        revit_utils.comments(fitting)
    ]
    return ' '.join([part.lower() for part in parts if part])


def fitting_kind(fitting):
    text = fitting_text(fitting)
    if contains_any(text, [u'крест', 'cross']):
        return 'cross'
    if contains_any(text, [u'трой', u'тройник', 'tee', 'wye']):
        return 'tee'
    if contains_any(text, [u'переход', u'редук', u'сужен', u'расшир', 'transition', 'reducer']):
        return 'transition'
    if contains_any(text, [u'отвод', u'колен', 'elbow', 'bend']):
        return 'elbow'
    if contains_any(text, [u'врез', 'tap']):
        return 'tap'
    if contains_any(text, [u'утк', 'offset']):
        return 'offset'
    if contains_any(text, [u'заглуш', 'cap', 'plug']):
        return 'cap'
    if contains_any(text, [u'противопожар', u'огнезадерж', 'fire damper', 'fire-damper']):
        return 'fire_damper'
    if contains_any(text, [u'обратн', 'backdraft', 'back draft', 'check valve']):
        return 'backdraft_damper'
    if contains_any(text, [u'дросс', u'клапан', 'damper', 'valve']):
        return 'damper'
    if contains_any(text, [u'решет', u'решёт', u'диффуз', 'diffuser', 'grille', 'grill', 'register']):
        return 'grille'
    if contains_any(text, [u'зонт', 'hood']):
        return 'hood'
    if contains_any(text, [u'дефлект', 'deflector']):
        return 'deflector'
    if contains_any(text, [u'вход', 'inlet', 'intake']):
        return 'inlet'
    if contains_any(text, [u'выход', u'выпуск', 'outlet', 'exhaust']):
        return 'outlet'
    try:
        category_name = revit_utils.category_name(fitting).lower()
        if u'оборуд' in category_name or 'equipment' in category_name:
            return 'equipment'
    except Exception:
        category_name = ''
    connector_count = len(revit_utils.connectors(fitting))
    if connector_count >= 4:
        return 'cross'
    if connector_count == 3:
        return 'tee'
    if connector_count == 2:
        return 'other'
    return 'unknown'


def contains_any(text, values):
    for value in values:
        if value in text:
            return True
    return False


def elbow_angle(fitting):
    value = revit_utils.param_double(fitting, ['ADSK_Размер_УголПоворота', 'Угол', 'Angle'], None)
    angle = revit_utils.round_angle(value)
    if angle:
        return angle
    text = fitting_text(fitting)
    for item in [15, 30, 45, 60, 90]:
        if str(item) in text:
            return item
    return 90


def recommended_values(fitting, zeta_data=None):
    if zeta_data is None:
        zeta_data = config.DEFAULT_ZETA
    kind = fitting_kind(fitting)
    if kind == 'elbow':
        angle = elbow_angle(fitting)
        return kind, {'z': zeta_data.get('elbow', {}).get(str(angle), config.DEFAULT_ZETA['elbow'].get(str(angle), 0.35)), 'angle': angle}
    if kind == 'transition':
        values = zeta_data.get('transition', {})
        defaults = config.DEFAULT_ZETA.get('transition', {})
        return kind, {'z_narrow': values.get('z_narrow', defaults.get('z_narrow', 0.10)), 'z_expand': values.get('z_expand', defaults.get('z_expand', 0.20))}
    if kind == 'tee':
        values = zeta_data.get('tee', {})
        defaults = config.DEFAULT_ZETA.get('tee', {})
        return kind, {'z_pass': values.get('z_pass', defaults.get('z_pass', 0.30)), 'z_branch': values.get('z_branch', defaults.get('z_branch', 1.20))}
    if kind == 'cross':
        values = zeta_data.get('cross', {})
        defaults = config.DEFAULT_ZETA.get('cross', {})
        return kind, {'z_pass': values.get('z_pass', defaults.get('z_pass', 0.50)), 'z_branch': values.get('z_branch', defaults.get('z_branch', 1.50))}
    values = zeta_data.get(kind, {})
    defaults = config.DEFAULT_ZETA.get(kind, config.DEFAULT_ZETA.get('other', {}))
    return kind, {'z': values.get('z', defaults.get('z', 0.0))}


def fitting_zeta(fitting, previous_duct=None, next_duct=None, zeta_data=None):
    kind, recommended = recommended_values(fitting, zeta_data)
    parsed = parse_comment(revit_utils.comments(fitting))
    if kind == 'transition':
        if 'z_narrow' in parsed or 'z_expand' in parsed:
            return transition_zeta(parsed, recommended, previous_duct, next_duct)
        if 'z' in parsed:
            return parsed.get('z')
        if 'zeta' in parsed:
            return parsed.get('zeta')
        return transition_zeta(parsed, recommended, previous_duct, next_duct)
    if kind == 'tee' or kind == 'cross':
        if 'z_pass' in parsed or 'z_branch' in parsed:
            return branch_zeta(fitting, parsed, recommended, previous_duct, next_duct)
        if 'z' in parsed:
            return parsed.get('z')
        if 'zeta' in parsed:
            return parsed.get('zeta')
        return branch_zeta(fitting, parsed, recommended, previous_duct, next_duct)
    if 'z' in parsed:
        return parsed.get('z')
    if 'zeta' in parsed:
        return parsed.get('zeta')
    return recommended.get('z', 0.0)


def transition_zeta(parsed, recommended, previous_duct, next_duct):
    z_narrow = parsed.get('z_narrow', recommended.get('z_narrow', 0.0))
    z_expand = parsed.get('z_expand', recommended.get('z_expand', 0.0))
    if previous_duct is None or next_duct is None:
        return max(z_narrow, z_expand)
    area1 = revit_utils.duct_area_m2(previous_duct)
    area2 = revit_utils.duct_area_m2(next_duct)
    if area1 > area2:
        return z_narrow
    if area2 > area1:
        return z_expand
    return min(z_narrow, z_expand)


def branch_zeta(fitting, parsed, recommended, previous_duct, next_duct):
    z_pass = parsed.get('z_pass', recommended.get('z_pass', 0.0))
    z_branch = parsed.get('z_branch', recommended.get('z_branch', 0.0))
    if previous_duct is None or next_duct is None:
        return max(z_pass, z_branch)
    direction = is_pass_direction(fitting, previous_duct, next_duct)
    if direction is None:
        return max(z_pass, z_branch)
    if direction:
        return z_pass
    return z_branch


def is_pass_direction(fitting, previous_duct, next_duct):
    center = revit_utils.element_center(fitting)
    p1 = revit_utils.element_center(previous_duct)
    p2 = revit_utils.element_center(next_duct)
    v1 = p1.Subtract(center)
    v2 = p2.Subtract(center)
    try:
        length = v1.GetLength() * v2.GetLength()
        if length <= 0:
            return None
        cos_value = v1.DotProduct(v2) / length
        return cos_value < -0.65
    except Exception:
        return None



def is_normal_terminal(element):
    kind = fitting_kind(element)
    if kind in ['cap', 'inlet', 'outlet', 'grille', 'hood', 'deflector', 'equipment']:
        return True
    try:
        category_name = revit_utils.category_name(element).lower()
        if u'терминал' in category_name or 'terminal' in category_name:
            return True
        if u'оборуд' in category_name or 'equipment' in category_name:
            return True
    except Exception:
        return False
    return False

def zero_allowed(fitting):
    return fitting_kind(fitting) == 'cap'


def apply_comment(fitting, zeta_data=None):
    kind, values = recommended_values(fitting, zeta_data)
    revit_utils.set_comments(fitting, format_comment(kind, values))
    return kind, values
