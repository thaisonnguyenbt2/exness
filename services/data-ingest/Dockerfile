FROM python:3.12

WORKDIR /app

# Install system dependencies needed for compiling numpy/pandas
RUN apt-get update && apt-get install -y gcc g++ libc-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
