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
    fill_id = solid_fill_id(doc)
    transaction = DB.Transaction(doc, 'VentCalc critical path')
    transaction.Start()
    try:
        color = DB.Color(255, 0, 0)
        for element_id in ids:
            settings = DB.OverrideGraphicSettings()
            apply_color_settings(settings, color, 8, fill_id)
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
    fill_id = solid_fill_id(doc)
    transaction = DB.Transaction(doc, 'VentCalc speed highlight')
    ids = []
    transaction.Start()
    try:
        for duct in ducts:
            velocity = duct_velocity(duct)
            graphic = DB.OverrideGraphicSettings()
            apply_color_settings(graphic, velocity_color(velocity, settings), 6, fill_id)
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


def solid_fill_id(doc):
    try:
        fill = DB.FillPatternElement.GetFillPatternElementByName(doc, DB.FillPatternTarget.Drafting, '<Solid fill>')
        if fill:
            return fill.Id
    except Exception:
        fill = None
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
        for item in collector:
            try:
                pattern = item.GetFillPattern()
                if pattern and pattern.IsSolidFill:
                    return item.Id
            except Exception:
                continue
    except Exception:
        return DB.ElementId.InvalidElementId
    return DB.ElementId.InvalidElementId


def apply_color_settings(settings, color, weight, fill_id):
    try:
        settings.SetProjectionLineColor(color)
    except Exception:
        color = color
    try:
        settings.SetProjectionLineWeight(int(weight))
    except Exception:
        weight = weight
    try:
        if fill_id and fill_id != DB.ElementId.InvalidElementId:
            settings.SetSurfaceForegroundPatternId(fill_id)
            settings.SetSurfaceForegroundPatternColor(color)
    except Exception:
        fill_id = fill_id
    try:
        if fill_id and fill_id != DB.ElementId.InvalidElementId:
            settings.SetCutForegroundPatternId(fill_id)
            settings.SetCutForegroundPatternColor(color)
    except Exception:
        fill_id = fill_id
