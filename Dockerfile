FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
RUN pip install uv
COPY requirements.txt /app/
RUN uv pip install --system -r requirements.txt
COPY . /app/
