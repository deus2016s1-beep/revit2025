# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import config
from ventcalc import revit_utils


def clear_ids(doc, view, ids):
    transaction = DB.Transaction(doc, 'VentCalc clear graphics')
    transaction.Start()
    try:
        for element_id in ids:
            try:
                view.SetElementOverrides(DB.ElementId(int(element_id)), DB.OverrideGraphicSettings())
            except Exception:
                continue
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise


def apply_critical_path(doc, view, ids):
    transaction = DB.Transaction(doc, 'VentCalc critical path')
    transaction.Start()
    try:
        color = DB.Color(255, 0, 0)
        for element_id in ids:
            settings = DB.OverrideGraphicSettings()
            settings.SetProjectionLineColor(color)
            settings.SetProjectionLineWeight(8)
            view.SetElementOverrides(DB.ElementId(int(element_id)), settings)
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise


def toggle_critical_path(doc, view, last_result, start_path=None):
    settings = config.load_settings(start_path)
    previous_ids = settings.get('critical_highlight_ids', [])
    if previous_ids:
        clear_ids(doc, view, previous_ids)
    if config.to_bool(settings.get('critical_highlight_enabled', False), False):
        settings['critical_highlight_enabled'] = False
        settings['critical_highlight_ids'] = []
        config.save_settings(settings, start_path)
        return False, []
    ids = last_result.get('critical_path_ids', [])
    apply_critical_path(doc, view, ids)
    settings['critical_highlight_enabled'] = True
    settings['critical_highlight_ids'] = ids
    config.save_settings(settings, start_path)
    return True, ids


def velocity_color(value, settings):
    min_velocity = config.to_float(settings.get('min_velocity', 3.0), 3.0)
    max_velocity = config.to_float(settings.get('max_velocity', 5.0), 5.0)
    if value <= 0:
        return DB.Color(160, 160, 160)
    if value < min_velocity:
        return DB.Color(0, 120, 255)
    if value > max_velocity:
        return DB.Color(255, 0, 0)
    return DB.Color(0, 180, 0)


def apply_speed_highlight(doc, view, ducts, settings):
    transaction = DB.Transaction(doc, 'VentCalc speed highlight')
    ids = []
    transaction.Start()
    try:
        for duct in ducts:
            velocity = duct_velocity(duct)
            graphic = DB.OverrideGraphicSettings()
            graphic.SetProjectionLineColor(velocity_color(velocity, settings))
            graphic.SetProjectionLineWeight(6)
            view.SetElementOverrides(duct.Id, graphic)
            ids.append(duct.Id.IntegerValue)
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
    return ids


def clear_speed_highlight(doc, view, start_path=None):
    settings = config.load_settings(start_path)
    clear_ids(doc, view, settings.get('speed_highlight_ids', []))
    settings['speed_highlight_ids'] = []
    config.save_settings(settings, start_path)


def duct_velocity(duct):
    flow = revit_utils.duct_flow_m3s(duct)
    area = revit_utils.duct_area_m2(duct)
    if area <= 0:
        return 0.0
    return flow / area
