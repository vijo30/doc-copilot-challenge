# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install uv first, as it's not a standard package
RUN pip install uv

# Copy the requirements file into the working directory
COPY requirements.txt .

# Use uv to install the needed packages
RUN uv pip install -r requirements.txt --system

# Copy the rest of the application code into the container
COPY . /app

# Set the Python Path to include the project's root
ENV PYTHONPATH=/app

# Expose the ports the app runs on
EXPOSE 8000
EXPOSE 8501

# Define the command to run the backend and frontend (this will be overridden by docker-compose)
CMD ["echo", "Ready to start services"]