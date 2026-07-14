CreateObject("Wscript.Shell").Run "pythonw.exe app\server.py", 0, False
WScript.Sleep 5000
CreateObject("Wscript.Shell").Run "msedge --app=http://127.0.0.1:8080", 1, False