# Web and ngrok Deployment

## Local Web Application

Use Python 3.10-3.12 and install `requirements.txt`. Generate a private random bearer token with at least 32 characters, then start the loopback server:

```powershell
$env:NLVE_WEB_API_TOKEN = "private-random-value-with-at-least-32-characters"
.\scripts\start-web.ps1 -Port 8765
```

In a source checkout where `python` is not the supported interpreter, pass `-PythonExecutable C:\path\to\python.exe`. In the standalone release the scripts automatically use `NLVE-Operator.exe`.

Open `http://127.0.0.1:8765`. The API and static web assets run in one Uvicorn worker over the same SQLite database as the desktop application. Do not run multiple writers against a database copied to a network share.

## ngrok HTTPS Tunnel

Install and authorize the official ngrok client separately. Keep the application bound to `127.0.0.1`; do not set `NLVE_WEB_ALLOW_NON_LOOPBACK` for normal cloud access.

```powershell
$env:NLVE_WEB_API_TOKEN = "private-random-value-with-at-least-32-characters"
.\scripts\start-ngrok.ps1 -Port 8765
```

The script starts hidden child processes, waits for local health, discovers an HTTPS tunnel, verifies public health, and only then writes ignored `data/web-runtime.json`. Logs are written under ignored `logs/`. If startup fails, the script stops only the processes it created and removes stale runtime state.

For a reserved ngrok domain, pass `-Domain your-domain.ngrok.app` and include that hostname in `NLVE_WEB_TRUSTED_HOSTS` when it does not match the default ngrok suffixes.

## Security Notes

- Use a dedicated random token, not an NLvoorelkaar password or Google credential.
- Share the URL and token through separate private channels and rotate the token after an access incident.
- Browser tokens live only in session storage. Disconnect after use on a shared device.
- Public tunnel access does not authorize provider automation. Live provider actions still require feature flags and the private written-approval record.
- The HAI bridge may read the feed through the tunnel, but HAI has no approval, send, retention, or Safety Stop authority.

Stop the web and ngrok process IDs recorded in `data/web-runtime.json` when the session is finished, then remove that ignored runtime file.
