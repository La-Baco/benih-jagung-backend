# Layanan Flask untuk VPS. Versi Python sama dengan Tabel 3.11 (3.10.6).
FROM python:3.10.6-slim

WORKDIR /app
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

COPY . .
RUN useradd --uid 10001 --create-home layanan \
    && chmod +x mulai_server.sh
USER layanan

ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg
EXPOSE 5000
CMD ["./mulai_server.sh"]
