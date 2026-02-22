Option Explicit

Dim fso, shell, root, runGui, pyw, py, cmd, ok
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
runGui = root & "\run_gui.py"
pyw = root & "\python\pythonw.exe"
py = root & "\python\python.exe"
ok = False

If Not fso.FileExists(runGui) Then
    MsgBox "run_gui.py not found:" & vbCrLf & runGui, vbCritical, "PrimeRL launcher"
    WScript.Quit 1
End If

shell.CurrentDirectory = root

On Error Resume Next

' Preferred: bundled pythonw
If fso.FileExists(pyw) Then
    cmd = """" & pyw & """" & " " & """" & runGui & """"
    shell.Run cmd, 0, False
    If Err.Number = 0 Then ok = True
    Err.Clear
End If

' Fallback: first real pythonw on PATH (skip WindowsApps stubs)
If Not ok Then
    pyw = ResolveFromWhere("pythonw")
    If pyw <> "" Then
        cmd = """" & pyw & """" & " " & """" & runGui & """"
        shell.Run cmd, 0, False
        If Err.Number = 0 Then ok = True
        Err.Clear
    End If
End If

' Last fallback: first real python on PATH with visible console
If Not ok Then
    If fso.FileExists(py) Then
        cmd = """" & py & """" & " " & """" & runGui & """"
    Else
        py = ResolveFromWhere("python")
        If py <> "" Then
            cmd = """" & py & """" & " " & """" & runGui & """"
        Else
            cmd = ""
        End If
    End If
    If cmd <> "" Then
        shell.Run cmd, 1, False
        If Err.Number = 0 Then ok = True
        Err.Clear
    End If
End If

On Error GoTo 0

If Not ok Then
    MsgBox "Could not start PrimeRL." & vbCrLf & _
           "Install Python or check PATH/python folder in this workspace.", _
           vbCritical, "PrimeRL launcher"
    WScript.Quit 2
End If

Function ResolveFromWhere(exeName)
    Dim execObj, line, candidate, best
    best = ""
    On Error Resume Next
    Set execObj = shell.Exec("cmd /c where " & exeName)
    If Err.Number <> 0 Then
        Err.Clear
        ResolveFromWhere = ""
        Exit Function
    End If
    On Error GoTo 0

    Do While Not execObj.StdOut.AtEndOfStream
        line = Trim(execObj.StdOut.ReadLine())
        If line <> "" Then
            candidate = LCase(line)
            ' Ignore Windows Store stubs which often lack installed packages.
            If InStr(candidate, "\windowsapps\") = 0 Then
                best = line
                Exit Do
            End If
            If best = "" Then
                best = line
            End If
        End If
    Loop

    ResolveFromWhere = best
End Function
