FROM python:3.10-slim
WORKDIR /app
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --no-cache-dir --system -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]