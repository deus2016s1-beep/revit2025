# -*- coding: utf-8 -*-
import os
import zipfile
import datetime
from xml.sax.saxutils import escape
from ventcalc import config

try:
    unicode
except NameError:
    unicode = str
try:
    long
except NameError:
    long = int

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
WORKBOOK = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Аэродинамический расчет" sheetId="1" r:id="rId1"/></sheets></workbook>'''
WORKBOOK_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="4"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font><font><b/><sz val="14"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font></fonts><fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color auto="1"/></left><right style="thin"><color auto="1"/></right><top style="thin"><color auto="1"/></top><bottom style="thin"><color auto="1"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
APP_PROPS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>VentCalc</Application></Properties>'''
CORE_PROPS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Аэродинамический расчет</dc:title><dc:creator>VentCalc</dc:creator></cp:coreProperties>'''


def export_calculation(result, path=None):
    if path is None:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        path = os.path.join(desktop, default_filename())
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    try:
        write_xlsx(result, path)
        return path
    except Exception:
        csv_path = csv_fallback_path(path)
        write_csv(result, csv_path)
        return csv_path


def save_xlsx(result, path=None):
    return export_calculation(result, path)


def default_filename():
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return u'VentCalc_Аэродинамический_расчет_' + stamp + '.xlsx'


def write_xlsx(result, path):
    archive = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    try:
        write_part(archive, '[Content_Types].xml', CONTENT_TYPES)
        write_part(archive, '_rels/.rels', ROOT_RELS)
        write_part(archive, 'xl/workbook.xml', WORKBOOK)
        write_part(archive, 'xl/_rels/workbook.xml.rels', WORKBOOK_RELS)
        write_part(archive, 'xl/styles.xml', STYLES)
        write_part(archive, 'docProps/app.xml', APP_PROPS)
        write_part(archive, 'docProps/core.xml', CORE_PROPS)
        write_part(archive, 'xl/worksheets/sheet1.xml', worksheet_xml(result))
    finally:
        archive.close()


def write_part(archive, name, text):
    if isinstance(text, unicode):
        text = text.encode('utf-8')
    archive.writestr(name, text)


def csv_fallback_path(path):
    root, ext = os.path.splitext(path)
    return root + '.csv'


def worksheet_xml(result):
    rows = []
    headers = headers_list()
    rows.append(row_xml(1, [u'Аэродинамический расчет системы вентиляции'], 1))
    rows.append(row_xml(2, headers, 2))
    row_number = 3
    for row in result.get('rows', []):
        rows.append(row_xml(row_number, row_values(row), 3))
        row_number += 1
    rows.append(row_xml(row_number, total_values(result), 4))
    dimension = 'A1:R' + str(row_number)
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    xml.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    xml.append('<dimension ref="' + dimension + '"/>')
    xml.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    xml.append(columns_xml())
    xml.append('<sheetData>')
    xml.extend(rows)
    xml.append('</sheetData>')
    xml.append('<autoFilter ref="A2:R' + str(row_number) + '"/>')
    xml.append('<mergeCells count="1"><mergeCell ref="A1:R1"/></mergeCells>')
    xml.append('<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>')
    xml.append('<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>')
    xml.append('</worksheet>')
    return '\n'.join(xml)


def columns_xml():
    widths = [6, 10, 26, 14, 13, 10, 12, 10, 12, 12, 9, 10, 10, 10, 8, 10, 10, 42]
    parts = ['<cols>']
    for index in range(len(widths)):
        col = str(index + 1)
        parts.append('<col min="' + col + '" max="' + col + '" width="' + str(widths[index]) + '" customWidth="1"/>')
    parts.append('</cols>')
    return ''.join(parts)


def row_xml(row_number, values, style_index):
    cells = []
    for index in range(len(values)):
        cells.append(cell_xml(row_number, index + 1, values[index], style_index))
    return '<row r="' + str(row_number) + '">' + ''.join(cells) + '</row>'


def cell_xml(row_number, column_number, value, style_index):
    ref = column_name(column_number) + str(row_number)
    style = ''
    if style_index > 0:
        style = ' s="' + str(style_index) + '"'
    if value is None or value == '':
        return '<c r="' + ref + '"' + style + '/>'
    if is_number(value):
        return '<c r="' + ref + '"' + style + '><v>' + number_text(value) + '</v></c>'
    text = escape(config.unicode_text(value))
    return '<c r="' + ref + '" t="inlineStr"' + style + '><is><t>' + text + '</t></is></c>'


def column_name(number):
    result = ''
    while number > 0:
        number -= 1
        result = chr(65 + number % 26) + result
        number = number // 26
    return result


def is_number(value):
    return isinstance(value, int) or isinstance(value, long) or isinstance(value, float)


def number_text(value):
    return ('%.6f' % float(value)).rstrip('0').rstrip('.')


def headers_list():
    return [u'№', u'Участок', u'Наименование', u'Размер', u'Расход, м³/ч', u'Длина, м', u'Площадь, м²', u'dэкв, м', u'Скорость, м/с', u'Re', u'λ', u'Pv, Па', u'R, Па/м', u'R·l, Па', u'Σζ', u'Z, Па', u'ΔP, Па', u'Примечание']


def row_values(row):
    return [row.get('index', 0), row.get('section', ''), row.get('name', ''), row.get('size', ''), round_value(row.get('flow_m3h', 0.0), 0), round_value(row.get('length_m', 0.0), 2), round_value(row.get('area_m2', 0.0), 4), round_value(row.get('diameter_m', 0.0), 3), round_value(row.get('velocity_ms', 0.0), 2), round_value(row.get('re', 0.0), 0), round_value(row.get('lambda', 0.0), 4), round_value(row.get('pv_pa', 0.0), 2), round_value(row.get('r_pa_m', 0.0), 2), round_value(row.get('friction_pa', 0.0), 2), round_value(row.get('local_zeta', 0.0), 3), round_value(row.get('local_pa', 0.0), 2), round_value(row.get('total_pa', 0.0), 2), row.get('note', '')]


def total_values(result):
    totals = result.get('totals', {})
    reserve = round_value(totals.get('reserve_percent', 0.0))
    return ['', u'ИТОГО', '', '', '', round_value(totals.get('length_m', 0.0), 2), '', '', '', '', '', '', '', round_value(totals.get('friction_pa', 0.0), 2), '', round_value(totals.get('local_pa', 0.0), 2), round_value(totals.get('total_pa', 0.0), 2), u'с запасом ' + str(reserve) + u'%: ' + str(round_value(totals.get('total_with_reserve_pa', 0.0), 2)) + u' Па']


def write_csv(result, path):
    stream = open(path, 'wb')
    try:
        stream.write('\xef\xbb\xbf'.encode('latin1'))
        write_csv_line(stream, headers_list())
        for row in result.get('rows', []):
            write_csv_line(stream, row_values(row))
        write_csv_line(stream, total_values(result))
    finally:
        stream.close()


def write_csv_line(stream, values):
    parts = []
    for value in values:
        text = config.unicode_text(value).replace('"', '""')
        parts.append('"' + text + '"')
    stream.write((';'.join(parts) + '\r\n').encode('utf-8'))


def round_value(value, digits=3):
    try:
        if digits == 0:
            return int(round(float(value), 0))
        return round(float(value), digits)
    except Exception:
        return value
