FROM python:3.11-slim

# Instalar dependencias del sistema requeridas para CBC/PuLP
RUN apt-get update && apt-get install -y \
    coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Exponer el puerto por defecto de Easypanel (5000)
EXPOSE 5000

# Comando para ejecutar el microservicio
CMD ["uvicorn", "math_api:app", "--host", "0.0.0.0", "--port", "5000"]
