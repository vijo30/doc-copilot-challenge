FROM python:3.10-slim
WORKDIR /app
RUN pip install uv
COPY requirements.txt .
RUN uv pip install -r requirements.txt --system
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 8000
EXPOSE 8501
CMD ["echo", "Ready to start services"]