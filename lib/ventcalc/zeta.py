# -*- coding: utf-8 -*-
import re
from ventcalc import config
from ventcalc import revit_utils

KEYS = ['z_narrow', 'z_expand', 'z_pass', 'z_branch', 'zeta', 'z']


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


def format_comment(kind, values):
    if kind == 'elbow':
        return 'z=' + format_number(values.get('z', 0.0))
    if kind == 'transition':
        return 'z_narrow=' + format_number(values.get('z_narrow', 0.0)) + '; z_expand=' + format_number(values.get('z_expand', 0.0))
    if kind == 'tee':
        return 'z_pass=' + format_number(values.get('z_pass', 0.0)) + '; z_branch=' + format_number(values.get('z_branch', 0.0))
    if kind == 'cross':
        return 'z_pass=' + format_number(values.get('z_pass', 0.0)) + '; z_branch=' + format_number(values.get('z_branch', 0.0))
    return 'z=' + format_number(values.get('z', 0.0))


def format_number(value):
    text = ('%.3f' % float(value)).rstrip('0').rstrip('.')
    if text == '':
        return '0'
    return text


def fitting_text(fitting):
    parts = [
        revit_utils.param_text(fitting, ['ADSK_Наименование', 'Наименование', 'Name'], ''),
        revit_utils.element_name(fitting),
        revit_utils.type_name(fitting),
        revit_utils.comments(fitting)
    ]
    return ' '.join([part.lower() for part in parts if part])


def fitting_kind(fitting):
    text = fitting_text(fitting)
    if contains_any(text, [u'крест', 'cross']):
        return 'cross'
    if contains_any(text, [u'трой', u'тройник', 'tee', 'wye']):
        return 'tee'
    if contains_any(text, [u'переход', u'редук', 'transition', 'reducer']):
        return 'transition'
    if contains_any(text, [u'отвод', u'колен', 'elbow', 'bend']):
        return 'elbow'
    connector_count = len(revit_utils.connectors(fitting))
    if connector_count >= 4:
        return 'cross'
    if connector_count == 3:
        return 'tee'
    return 'other'


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
        return kind, {'z': zeta_data.get('elbow', {}).get(str(angle), 0.65), 'angle': angle}
    if kind == 'transition':
        values = zeta_data.get('transition', {})
        return kind, {'z_narrow': values.get('z_narrow', 0.35), 'z_expand': values.get('z_expand', 0.25)}
    if kind == 'tee':
        values = zeta_data.get('tee', {})
        return kind, {'z_pass': values.get('z_pass', 0.25), 'z_branch': values.get('z_branch', 1.0)}
    if kind == 'cross':
        values = zeta_data.get('cross', {})
        return kind, {'z_pass': values.get('z_pass', 0.35), 'z_branch': values.get('z_branch', 1.2)}
    values = zeta_data.get('other', {})
    return kind, {'z': values.get('z', 0.5)}


def fitting_zeta(fitting, previous_duct=None, next_duct=None, zeta_data=None):
    kind, recommended = recommended_values(fitting, zeta_data)
    parsed = parse_comment(revit_utils.comments(fitting))
    if parsed.get('z') is not None:
        return parsed.get('z')
    if parsed.get('zeta') is not None:
        return parsed.get('zeta')
    if kind == 'transition':
        return transition_zeta(parsed, recommended, previous_duct, next_duct)
    if kind == 'tee' or kind == 'cross':
        return branch_zeta(fitting, parsed, recommended, previous_duct, next_duct)
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
    if is_pass_direction(fitting, previous_duct, next_duct):
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
            return False
        cos_value = v1.DotProduct(v2) / length
        return cos_value < -0.65
    except Exception:
        return False


def apply_comment(fitting, zeta_data=None):
    kind, values = recommended_values(fitting, zeta_data)
    revit_utils.set_comments(fitting, format_comment(kind, values))
    return kind, values
