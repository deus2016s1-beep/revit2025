# -*- coding: utf-8 -*-
import os
import clr
clr.AddReference('Microsoft.Office.Interop.Excel')
from Microsoft.Office.Interop import Excel
from System.Runtime.InteropServices import Marshal
from ventcalc import config


def export_calculation(result, path=None):
    if path is None:
        filename = result.get('settings', {}).get('excel_filename', 'AerodynamicCalculation.xlsx')
        path = config.data_path(filename)
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    app = Excel.ApplicationClass()
    app.Visible = False
    workbook = None
    try:
        workbook = app.Workbooks.Add()
        sheet = workbook.Worksheets[1]
        sheet.Name = u'Аэродинамический расчет'
        write_sheet(sheet, result)
        workbook.SaveAs(path)
        return path
    finally:
        if workbook:
            workbook.Close(False)
            Marshal.ReleaseComObject(workbook)
        app.Quit()
        Marshal.ReleaseComObject(app)


def write_sheet(sheet, result):
    headers = [
        u'№ участка',
        u'Система',
        u'Наименование участка',
        u'L, м',
        u'Q, м³/с',
        u'F, м²',
        u'v, м/с',
        u'dэкв, м',
        u'R·l, Па',
        u'Σζ',
        u'Z, Па',
        u'Σ(R·l+Z), Па',
        u'С запасом, Па'
    ]
    sheet.Cells(1, 1).Value2 = u'Аэродинамический расчет системы вентиляции'
    title = sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, len(headers)))
    title.Merge()
    title.Font.Bold = True
    title.Font.Size = 14
    title.HorizontalAlignment = Excel.XlHAlign.xlHAlignCenter
    for index, header in enumerate(headers):
        cell = sheet.Cells(3, index + 1)
        cell.Value2 = header
        cell.Font.Bold = True
        cell.Interior.Color = 14277081
        cell.Borders.LineStyle = 1
        cell.HorizontalAlignment = Excel.XlHAlign.xlHAlignCenter
    row_number = 4
    for row in result.get('rows', []):
        values = [
            row.get('index', 0),
            row.get('system', ''),
            row.get('name', ''),
            round_value(row.get('length_m', 0.0)),
            round_value(row.get('flow_m3s', 0.0)),
            round_value(row.get('area_m2', 0.0)),
            round_value(row.get('velocity_ms', 0.0)),
            round_value(row.get('diameter_m', 0.0)),
            round_value(row.get('friction_pa', 0.0)),
            round_value(row.get('local_zeta', 0.0)),
            round_value(row.get('local_pa', 0.0)),
            round_value(row.get('total_pa', 0.0)),
            round_value(row.get('total_with_reserve_pa', 0.0))
        ]
        for column, value in enumerate(values):
            cell = sheet.Cells(row_number, column + 1)
            cell.Value2 = value
            cell.Borders.LineStyle = 1
        row_number += 1
    totals = result.get('totals', {})
    sheet.Cells(row_number, 8).Value2 = u'Итого'
    sheet.Cells(row_number, 8).Font.Bold = True
    sheet.Cells(row_number, 9).Value2 = round_value(totals.get('friction_pa', 0.0))
    sheet.Cells(row_number, 11).Value2 = round_value(totals.get('local_pa', 0.0))
    sheet.Cells(row_number, 12).Value2 = round_value(totals.get('total_pa', 0.0))
    sheet.Cells(row_number, 13).Value2 = round_value(totals.get('total_with_reserve_pa', 0.0))
    for column in range(8, 14):
        cell = sheet.Cells(row_number, column)
        cell.Font.Bold = True
        cell.Interior.Color = 13434879
        cell.Borders.LineStyle = 1
    note_row = row_number + 2
    sheet.Cells(note_row, 1).Value2 = u'Запас, %'
    sheet.Cells(note_row, 2).Value2 = round_value(totals.get('reserve_percent', 0.0))
    sheet.Range(sheet.Cells(1, 1), sheet.Cells(note_row, len(headers))).Font.Name = 'Arial'
    sheet.Range(sheet.Cells(1, 1), sheet.Cells(note_row, len(headers))).Font.Size = 10
    sheet.Columns.AutoFit()
    sheet.PageSetup.Orientation = Excel.XlPageOrientation.xlLandscape
    sheet.PageSetup.Zoom = False
    sheet.PageSetup.FitToPagesWide = 1
    sheet.PageSetup.FitToPagesTall = False


def round_value(value):
    try:
        return round(float(value), 3)
    except Exception:
        return value
