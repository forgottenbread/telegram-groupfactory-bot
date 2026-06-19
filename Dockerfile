FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh && \
    adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER 1000:1000

CMD ["./entrypoint.sh"]
