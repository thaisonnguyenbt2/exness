FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We run standard FastAPI; Celery would be spun up in another container using this same image 
# via `celery -A celery_tasks worker` and `celery -A celery_tasks beat`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
