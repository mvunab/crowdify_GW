FROM python:3.11-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY app ./app
EXPOSE 8000
