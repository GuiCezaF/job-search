FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

RUN mkdir -p logs output

# Você pode rodar "docker run job-search --now" para execuções manuais
ENTRYPOINT ["python", "main.py"]
