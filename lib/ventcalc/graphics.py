# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB
from ventcalc import config


def velocity_color(value, settings):
    min_velocity = config.to_float(settings.get('min_velocity', 2.0), 2.0)
    max_velocity = config.to_float(settings.get('max_velocity', 8.0), 8.0)
    if value < min_velocity:
        return DB.Color(0, 120, 255)
    if value > max_velocity:
        return DB.Color(255, 0, 0)
    return DB.Color(0, 180, 0)


def fitting_color():
    return DB.Color(255, 140, 0)


def apply_overrides(doc, view, result_or_rows):
    if isinstance(result_or_rows, dict):
        result = result_or_rows
        rows = result.get('rows', [])
        settings = result.get('settings', {})
        fitting_ids = result.get('critical_fitting_ids', [])
    else:
        rows = result_or_rows
        settings = config.load_settings()
        fitting_ids = []
    if not config.to_bool(settings.get('highlight_critical_path', True), True):
        return
    transaction = DB.Transaction(doc, 'VentCalc graphics')
    transaction.Start()
    try:
        for row in rows:
            element_id = DB.ElementId(row.get('duct_id'))
            graphic = DB.OverrideGraphicSettings()
            if config.to_bool(settings.get('highlight_by_velocity', True), True):
                graphic.SetProjectionLineColor(velocity_color(row.get('velocity_ms', 0.0), settings))
            else:
                graphic.SetProjectionLineColor(DB.Color(255, 0, 0))
            graphic.SetProjectionLineWeight(7)
            view.SetElementOverrides(element_id, graphic)
        for fitting_id in fitting_ids:
            graphic = DB.OverrideGraphicSettings()
            graphic.SetProjectionLineColor(fitting_color())
            graphic.SetProjectionLineWeight(8)
            view.SetElementOverrides(DB.ElementId(fitting_id), graphic)
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
