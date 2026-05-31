using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace HelloRevit2025;

[Transaction(TransactionMode.Manual)]
public class HelloRevitCommand : IExternalCommand
{
    public Result Execute(
        ExternalCommandData commandData,
        ref string message,
        ElementSet elements)
    {
        TaskDialog.Show("Hello Revit 2025", "Плагин работает");

        return Result.Succeeded;
    }
}
