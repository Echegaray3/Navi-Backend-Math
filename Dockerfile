FROM python:3.10-slim

# Instala el solver matemático para PuLP
RUN apt-get update && apt-get install -y coinor-cbc

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Cambia 5000 por el puerto que uses en tu math_api.py
EXPOSE 80

CMD ["python", "math_api.py"]
