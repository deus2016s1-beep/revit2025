# -*- coding: utf-8 -*-
import os
import sys

extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
lib_path = os.path.join(extension_root, 'lib')
if lib_path not in sys.path:
    sys.path.append(lib_path)

from pyrevit import revit, forms
from ventcalc import revit_utils
from ventcalc import zeta


def main():
    ducts = revit_utils.ducts(revit.doc)
    fittings = revit_utils.fittings(revit.doc)
    without_flow = []
    without_zeta = []
    for duct in ducts:
        if revit_utils.duct_flow_m3s(duct) <= 0:
            without_flow.append(str(duct.Id.IntegerValue))
    for fitting in fittings:
        values = zeta.parse_comment(revit_utils.comments(fitting))
        if not values:
            without_zeta.append(str(fitting.Id.IntegerValue))
    message = u'Воздуховодов: ' + str(len(ducts)) + u'\nФитингов: ' + str(len(fittings))
    if without_flow:
        message += u'\nБез расхода: ' + ', '.join(without_flow[:30])
    if without_zeta:
        message += u'\nБез zeta в комментариях: ' + ', '.join(without_zeta[:30])
    forms.alert(message)


main()
