# Минимальный плагин Autodesk Revit 2025 на C#

Это первый учебный этап: минимальный Revit 2025 add-in без Dynamo, Python, WPF, сложной архитектуры и аэродинамического расчёта. Цель этапа — собрать `.dll`, подключить её через `.addin` и увидеть в Revit окно **«Плагин работает»**.

## Что входит в проект

| Файл | Зачем нужен |
| --- | --- |
| `HelloRevit2025.csproj` | Файл проекта C# под `.NET 8` и Revit API 2025. |
| `HelloRevitCommand.cs` | Команда Revit, которая реализует `IExternalCommand` и показывает `TaskDialog`. |
| `HelloRevit2025.addin` | Манифест, по которому Revit находит и загружает плагин. |

## Требования

1. Установленный **Autodesk Revit 2025**.
2. Установленная **Visual Studio 2022** с workload **.NET desktop development**.
3. Установленный **.NET 8 SDK**.
4. Проект должен собираться под `net8.0-windows`.

## Структура проекта

```text
HelloRevit2025/
├── HelloRevit2025.csproj
├── HelloRevitCommand.cs
├── HelloRevit2025.addin
└── README.md
```

## 1. Файл проекта `.csproj`

`HelloRevit2025.csproj` использует `net8.0-windows` и подключает две DLL из папки установленного Revit 2025:

- `RevitAPI.dll` — основное пространство имён `Autodesk.Revit.DB`;
- `RevitAPIUI.dll` — пространство имён `Autodesk.Revit.UI`, включая `IExternalCommand` и `TaskDialog`.

По умолчанию проект ожидает Revit API здесь:

```text
C:\Program Files\Autodesk\Revit 2025\
```

Если Revit установлен в другую папку, измените значение `RevitInstallDir` в `HelloRevit2025.csproj` или передайте путь при сборке через параметр MSBuild.

Пример сборки с другим путём:

```powershell
dotnet build -p:RevitInstallDir="D:\Autodesk\Revit 2025\"
```

## 2. Команда Revit

Класс `HelloRevitCommand` реализует `IExternalCommand`. Когда пользователь запускает команду из Revit, метод `Execute` показывает стандартное окно Revit:

```csharp
TaskDialog.Show("Hello Revit 2025", "Плагин работает");
```

Если окно появилось, значит Revit смог найти `.addin`, загрузить `.dll`, найти класс команды и выполнить метод `Execute`.

## 3. Файл `.addin`

Файл `HelloRevit2025.addin` сообщает Revit:

- что это внешняя команда (`Type="Command"`);
- как она называется (`Name`);
- где лежит собранная `.dll` (`Assembly`);
- какой класс запускать (`FullClassName`);
- какой уникальный идентификатор у плагина (`AddInId`).

Главная строка, которую нужно заменить под ваш компьютер:

```xml
<Assembly>C:\RevitPlugins\HelloRevit2025\HelloRevit2025.dll</Assembly>
```

Укажите здесь полный путь к собранному файлу `HelloRevit2025.dll`.

## 4. Куда должна собираться `.dll`

После обычной Debug-сборки DLL появится в папке:

```text
<папка проекта>\bin\Debug\net8.0-windows\HelloRevit2025.dll
```

Например, если проект лежит здесь:

```text
C:\Users\Ivan\source\repos\HelloRevit2025\
```

то DLL будет здесь:

```text
C:\Users\Ivan\source\repos\HelloRevit2025\bin\Debug\net8.0-windows\HelloRevit2025.dll
```

Именно этот путь можно указать в теге `Assembly` файла `.addin`.

Альтернативный простой вариант для новичка:

1. Создайте папку `C:\RevitPlugins\HelloRevit2025\`.
2. После сборки скопируйте туда `HelloRevit2025.dll` из `bin\Debug\net8.0-windows\`.
3. Оставьте в `.addin` строку:

```xml
<Assembly>C:\RevitPlugins\HelloRevit2025\HelloRevit2025.dll</Assembly>
```

## 5. Куда положить `.addin` файл

Для Revit 2025 положите файл `HelloRevit2025.addin` в одну из стандартных папок Revit add-ins.

### Вариант для текущего пользователя

```text
%APPDATA%\Autodesk\Revit\Addins\2025\
```

Обычно это раскрывается в путь вида:

```text
C:\Users\<ВашПользователь>\AppData\Roaming\Autodesk\Revit\Addins\2025\
```

### Вариант для всех пользователей компьютера

```text
%PROGRAMDATA%\Autodesk\Revit\Addins\2025\
```

Обычно это:

```text
C:\ProgramData\Autodesk\Revit\Addins\2025\
```

Для первого теста проще использовать папку текущего пользователя `%APPDATA%\Autodesk\Revit\Addins\2025\`.

## 6. Как собрать проект

### Через Visual Studio

1. Откройте Visual Studio 2022.
2. Выберите **Open a project or solution**.
3. Откройте файл `HelloRevit2025.csproj`.
4. Убедитесь, что конфигурация стоит **Debug**.
5. Нажмите **Build → Build Solution**.
6. Проверьте, что появился файл:

```text
bin\Debug\net8.0-windows\HelloRevit2025.dll
```

### Через командную строку

В папке проекта выполните:

```powershell
dotnet build
```

Если Revit установлен не в стандартную папку:

```powershell
dotnet build -p:RevitInstallDir="D:\Autodesk\Revit 2025\"
```

## 7. Как проверить плагин в Revit 2025

1. Соберите проект и получите `HelloRevit2025.dll`.
2. Откройте `HelloRevit2025.addin` в текстовом редакторе.
3. В теге `Assembly` укажите полный путь к вашей `HelloRevit2025.dll`.
4. Скопируйте `HelloRevit2025.addin` в `%APPDATA%\Autodesk\Revit\Addins\2025\`.
5. Полностью закройте Revit, если он был открыт.
6. Запустите **Autodesk Revit 2025** заново.
7. Откройте любой проект или создайте новый пустой проект.
8. Перейдите на вкладку **Add-Ins**.
9. Найдите команду **External Tools**.
10. Запустите команду **Hello Revit 2025**.
11. Должно появиться окно **«Плагин работает»**.

## Простыми словами

### Что такое `.dll`

`.dll` — это скомпилированная библиотека с вашим C# кодом. Вы пишете файл `.cs`, Visual Studio или `dotnet build` компилирует его, и на выходе получается `HelloRevit2025.dll`. Revit загружает эту DLL и выполняет класс команды внутри неё.

### Что такое `.addin`

`.addin` — это маленький XML-файл-манифест. В нём нет логики плагина. Он только говорит Revit: «загрузи вот эту DLL и запусти вот этот класс».

### Почему Revit видит плагин

При старте Revit проверяет специальные папки `Addins\2025`. Если там лежит `.addin` файл, Revit читает его, берёт путь из тега `Assembly`, загружает DLL и ищет класс из тега `FullClassName`. В этом проекте это класс `HelloRevit2025.HelloRevitCommand`.

### Что делать, если плагин не появился

1. Проверьте, что `.addin` лежит именно в папке `Addins\2025`, а не `Addins\2024` или другой версии.
2. Проверьте, что путь в теге `Assembly` полный и ведёт к существующему файлу `.dll`.
3. Проверьте, что DLL была пересобрана после изменений.
4. Полностью перезапустите Revit.
5. Проверьте, что `FullClassName` в `.addin` совпадает с namespace и именем класса: `HelloRevit2025.HelloRevitCommand`.
6. Проверьте, что проект собирается под `net8.0-windows`, а не под старую версию .NET Framework.
7. Проверьте, что подключены правильные Revit API DLL именно от Revit 2025.

### Типовые ошибки

| Ошибка | Причина | Как исправить |
| --- | --- | --- |
| Команда не появилась в Revit | `.addin` лежит не в той папке | Положить файл в `%APPDATA%\Autodesk\Revit\Addins\2025\`. |
| Revit показывает ошибку загрузки DLL | Неверный путь в `Assembly` | Указать полный путь к существующей `HelloRevit2025.dll`. |
| Ошибка компиляции: не найден `Autodesk.Revit.UI` | Не найден `RevitAPIUI.dll` | Проверить путь `RevitInstallDir` в `.csproj`. |
| Ошибка компиляции: не найден `Autodesk.Revit.DB` | Не найден `RevitAPI.dll` | Проверить, установлен ли Revit 2025 и верен ли путь к его папке. |
| Команда есть, но не запускается | Не совпадает `FullClassName` | Должно быть `HelloRevit2025.HelloRevitCommand`. |
| Изменения в коде не видны | Revit использует старую DLL | Пересобрать проект, скопировать новую DLL и перезапустить Revit. |

## Важно для следующего этапа

Пока этот минимальный плагин не запустится и не покажет **«Плагин работает»**, не нужно переходить к аэродинамическому расчёту, графам сети или WPF-интерфейсу. Сначала нужно убедиться, что базовая связка `C# → DLL → .addin → Revit 2025` работает.
