# -*- coding: utf-8 -*-
import Autodesk.Revit.DB as DB


def color_for_pressure(value, maximum):
    if maximum <= 0:
        return DB.Color(0, 180, 0)
    ratio = value / maximum
    if ratio < 0:
        ratio = 0
    if ratio > 1:
        ratio = 1
    red = int(255 * ratio)
    green = int(180 * (1 - ratio))
    return DB.Color(red, green, 0)


def apply_overrides(doc, view, rows):
    maximum = 0.0
    for row in rows:
        if row.get('total_pa', 0.0) > maximum:
            maximum = row.get('total_pa', 0.0)
    transaction = DB.Transaction(doc, 'VentCalc graphics')
    transaction.Start()
    try:
        for row in rows:
            element_id = DB.ElementId(row.get('duct_id'))
            settings = DB.OverrideGraphicSettings()
            settings.SetProjectionLineColor(color_for_pressure(row.get('total_pa', 0.0), maximum))
            settings.SetProjectionLineWeight(6)
            view.SetElementOverrides(element_id, settings)
        transaction.Commit()
    except Exception:
        transaction.RollBack()
        raise
