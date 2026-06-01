# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import config


def velocity_color(value, settings):
    min_velocity = config.to_float(settings.get('min_velocity', 3.0), 3.0)
    max_velocity = config.to_float(settings.get('max_velocity', 5.0), 5.0)
    if value < min_velocity:
        return DB.Color(0, 120, 255)
    if value > max_velocity:
        return DB.Color(255, 0, 0)
    return DB.Color(0, 180, 0)


def fitting_color():
    return DB.Color(255, 140, 0)


def end_color():
    return DB.Color(160, 0, 200)


def apply_overrides(doc, view, result_or_rows):
    if isinstance(result_or_rows, dict):
        result = result_or_rows
        rows = result.get('rows', [])
        settings = result.get('settings', {})
        fitting_ids = result.get('critical_fitting_ids', [])
        start_element_id = result.get('start_element_id')
        end_element_id = result.get('end_element_id')
        start_path = result.get('settings_start_path')
    else:
        rows = result_or_rows
        settings = config.load_settings()
        fitting_ids = []
        start_element_id = None
        end_element_id = None
        start_path = None
    transaction = DB.Transaction(doc, 'VentCalc graphics')
    transaction.Start()
    try:
        clear_previous(view, settings)
        if not config.to_bool(settings.get('highlight_critical_path', True), True):
            settings['last_highlight_ids'] = []
            transaction.Commit()
            config.save_settings(settings, start_path)
            return
        current_ids = []
        for row in rows:
            duct_id = row.get('duct_id')
            if duct_id is None:
                continue
            graphic = DB.OverrideGraphicSettings()
            if config.to_bool(settings.get('highlight_by_velocity', True), True):
                graphic.SetProjectionLineColor(velocity_color(row.get('velocity_ms', 0.0), settings))
            else:
                graphic.SetProjectionLineColor(DB.Color(255, 0, 0))
            graphic.SetProjectionLineWeight(7)
            view.SetElementOverrides(DB.ElementId(duct_id), graphic)
            add_unique(current_ids, duct_id)
        for fitting_id in fitting_ids:
            apply_element_color(view, fitting_id, fitting_color(), 8)
            add_unique(current_ids, fitting_id)
        if start_element_id:
            apply_element_color(view, start_element_id, fitting_color(), 8)
            add_unique(current_ids, start_element_id)
        if end_element_id:
            apply_element_color(view, end_element_id, end_color(), 8)
            add_unique(current_ids, end_element_id)
        settings['last_highlight_ids'] = current_ids
        transaction.Commit()
        config.save_settings(settings, start_path)
    except Exception:
        transaction.RollBack()
        raise


def clear_previous(view, settings):
    for element_id in settings.get('last_highlight_ids', []):
        try:
            view.SetElementOverrides(DB.ElementId(int(element_id)), DB.OverrideGraphicSettings())
        except Exception:
            continue


def apply_element_color(view, element_id, color, weight):
    graphic = DB.OverrideGraphicSettings()
    graphic.SetProjectionLineColor(color)
    graphic.SetProjectionLineWeight(weight)
    view.SetElementOverrides(DB.ElementId(int(element_id)), graphic)


def add_unique(values, value):
    try:
        value = int(value)
    except Exception:
        return
    if value not in values:
        values.append(value)
