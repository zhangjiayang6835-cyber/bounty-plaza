FROM python:3.11-slim

WORKDIR /app

# Install required tools and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Principle of Least Privilege: Non-root execution (CWE-276 / OWASP Container Security)
RUN useradd -m -u 1001 sila

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest lxml

COPY . .
RUN chown -R sila:sila /app

USER sila

EXPOSE 50051

HEALTHCHECK --interval=5s --timeout=5s --start-period=3s --retries=3 \
    CMD python -c "import socket, sys; s = socket.socket(); s.settimeout(2); res = s.connect_ex(('127.0.0.1', 50051)); s.close(); sys.exit(0 if res == 0 else 1)"

CMD ["python", "-m", "middleware.sila2_bridge"]
