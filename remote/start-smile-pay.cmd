@echo off
cd /d C:\Users\user\smile-pay
set PYTHONUNBUFFERED=1
set HOST=0.0.0.0
set PORT=8767
set USE_HTTPS=true
set SSL_CERTFILE=certs\cert.pem
set SSL_KEYFILE=certs\key.pem
.venv\Scripts\python.exe -m app.main
