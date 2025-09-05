# Developer convenience runner
Start-Process powershell -ArgumentList "uvicorn services.asr.app:app --reload --port 7031"
Start-Process powershell -ArgumentList "uvicorn services.redaction.app:app --reload --port 7032"
Start-Process powershell -ArgumentList "uvicorn services.insights_bridge.app:app --reload --port 7033"
Write-Host "Started FastAPI services on 7031/7032/7033"