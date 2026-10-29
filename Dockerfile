FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt* /app/
RUN pip install --no-cache-dir pytest

COPY . /app

CMD ["python", "scripts/bounty1_chipseq_pace.py"]
