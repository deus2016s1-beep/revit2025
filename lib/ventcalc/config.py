# -*- coding: utf-8 -*-
import os
import json

DEFAULT_SETTINGS = {
    'air_density': 1.2,
    'dynamic_viscosity': 0.0000181,
    'roughness_mm': 0.1,
    'min_velocity': 3.0,
    'max_velocity': 5.0,
    'reserve_percent': 15.0,
    'highlight_critical_path': True,
    'highlight_by_velocity': True,
    'ask_before_excel': True,
    'last_highlight_ids': [],
    'excel_filename': 'AerodynamicCalculation.xlsx',
    'zeta_filename': 'ventcalc_zeta.json'
}

DEFAULT_ZETA = {
    'elbow': {'15': 0.08, '30': 0.12, '45': 0.18, '60': 0.25, '90': 0.35},
    'transition': {'z_narrow': 0.10, 'z_expand': 0.20},
    'tee': {'z_pass': 0.30, 'z_branch': 1.20},
    'cross': {'z_pass': 0.50, 'z_branch': 1.50},
    'tap': {'z': 1.20},
    'offset': {'z': 0.40},
    'cap': {'z': 0.00},
    'damper': {'z': 0.40},
    'fire_damper': {'z': 0.50},
    'backdraft_damper': {'z': 2.00},
    'inlet': {'z': 0.50},
    'outlet': {'z': 1.00},
    'grille': {'z': 2.00},
    'hood': {'z': 1.30},
    'deflector': {'z': 1.00},
    'equipment': {'z': 0.50},
    'other': {'z': 0.50},
    'unknown': {'z': 0.00}
}


def unicode_text(value):
    try:
        return unicode(value)
    except NameError:
        return str(value)


def extension_root(start_path=None):
    if start_path is None:
        start_path = os.getcwd()
    path = os.path.abspath(start_path)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    while True:
        if path.lower().endswith('.extension'):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.getcwd()
        path = parent


def data_path(filename=None, start_path=None):
    root = extension_root(start_path)
    if filename is None:
        return root
    return os.path.join(root, filename)


def read_json(path, default_value):
    if not os.path.exists(path):
        return copy_dict(default_value)
    stream = None
    try:
        stream = open(path, 'r')
        text = stream.read()
        if not text:
            return copy_dict(default_value)
        data = json.loads(text)
        result = copy_dict(default_value)
        merge_dict(result, data)
        remove_old_settings(result)
        return result
    finally:
        if stream:
            stream.close()


def write_json(path, data):
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    stream = None
    try:
        stream = open(path, 'wb')
        stream.write(text.encode('utf-8'))
    finally:
        if stream:
            stream.close()


def copy_dict(value):
    if isinstance(value, dict):
        result = {}
        for key in value:
            result[key] = copy_dict(value[key])
        return result
    if isinstance(value, list):
        return [copy_dict(item) for item in value]
    return value


def merge_dict(target, source):
    if not isinstance(source, dict):
        return target
    for key in source:
        if isinstance(source[key], dict) and isinstance(target.get(key), dict):
            merge_dict(target[key], source[key])
        else:
            target[key] = source[key]
    return target


def remove_old_settings(settings):
    if isinstance(settings, dict) and 'friction_factor' in settings:
        del settings['friction_factor']
    return settings


def settings_path(start_path=None):
    return data_path('ventcalc_settings.json', start_path)


def zeta_path(start_path=None):
    settings = load_settings(start_path)
    return data_path(settings.get('zeta_filename', 'ventcalc_zeta.json'), start_path)


def load_settings(start_path=None):
    return remove_old_settings(read_json(data_path('ventcalc_settings.json', start_path), DEFAULT_SETTINGS))


def save_settings(settings, start_path=None):
    data = copy_dict(DEFAULT_SETTINGS)
    merge_dict(data, settings)
    remove_old_settings(data)
    write_json(data_path('ventcalc_settings.json', start_path), data)
    return data


def load_zeta(start_path=None):
    return read_json(zeta_path(start_path), DEFAULT_ZETA)


def save_zeta(zeta, start_path=None):
    data = copy_dict(DEFAULT_ZETA)
    merge_dict(data, zeta)
    write_json(zeta_path(start_path), data)
    return data


def to_float(value, default_value=0.0):
    if value is None:
        return default_value
    text = unicode_text(value).strip().replace(',', '.')
    if text == '':
        return default_value
    try:
        return float(text)
    except Exception:
        return default_value


def to_bool(value, default_value=False):
    if value is None:
        return default_value
    if isinstance(value, bool):
        return value
    text = unicode_text(value).strip().lower()
    if text in ['1', 'true', 'yes', 'да', 'y']:
        return True
    if text in ['0', 'false', 'no', 'нет', 'n']:
        return False
    return default_value
