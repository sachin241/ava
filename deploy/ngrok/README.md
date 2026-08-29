# Local Mobile HTTPS With Ngrok

Ngrok is the quickest way to test AVA from a phone because it gives your local Django server a public HTTPS URL.

## 1. Start Django

```powershell
python manage.py runserver 127.0.0.1:8000
```

## 2. Start Ngrok

If `ngrok` is available in a fresh terminal:

```powershell
ngrok http 8000
```

If PowerShell has not picked up the new PATH yet, use the installed executable directly:

```powershell
& "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe" http 8000
```

## 3. Add Your Auth Token If Ngrok Asks

Copy your token from the ngrok dashboard, then run:

```powershell
ngrok config add-authtoken <your-ngrok-token>
```

Or with the full path:

```powershell
& "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe" config add-authtoken <your-ngrok-token>
```

## 4. Open On Mobile

Open the `https://...ngrok-free.app` URL on your phone. Then tap:

1. `CONNECT CAMERA`
2. `ENABLE AVA VOICE` or `ASK AVA`

Do not use the `http://` forwarding URL for mobile camera/microphone testing.
