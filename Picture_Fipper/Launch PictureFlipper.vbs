' Launch PictureFlipper without showing a console window
Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
oShell.Run "pythonw.exe main.py", 0, False
