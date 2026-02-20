Get-Process -Name python,uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Write-Host "All python/uvicorn processes killed."
Write-Host "Now run START_WEB.bat to restart with the new api.py"
