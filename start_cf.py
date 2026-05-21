import urllib.request
import subprocess
import re
import sys
import os

print("Descargando Cloudflared (Túnel robusto)...")
if not os.path.exists("cloudflared.exe"):
    try:
        urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe", "cloudflared.exe")
    except Exception as e:
        print("Error descargando:", e)
        sys.exit(1)
        
print("Descarga completa. Levantando túnel permanente a localhost:8000...")
sys.stdout.flush()

# Ejecutar el tunel conectando puerto 8000 (donde está tu app FastAPI)
process = subprocess.Popen(["cloudflared.exe", "tunnel", "--url", "http://localhost:8000"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')

url_found = False
for line in process.stdout:
    # Print the cloudflared output line-by-line and flush immediately to keep log updated
    print(line.strip())
    sys.stdout.flush()
    
    if "trycloudflare.com" in line and not url_found:
        url_match = re.search(r'https://[^\s]+\.trycloudflare\.com', line)
        if url_match:
            url = url_match.group(0)
            print(f"\n[URL_TUNEL_LISTA] {url}\n")
            sys.stdout.flush()
            # Escribir la URL a un archivo
            with open("tunnel_url.txt", "w", encoding="utf-8") as f:
                f.write(url)
            url_found = True

try:
    process.wait()
except KeyboardInterrupt:
    process.terminate()
