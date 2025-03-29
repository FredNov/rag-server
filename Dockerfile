FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for the .env file
RUN mkdir -p /app

# The .env file should be mounted at runtime or passed as environment variables
CMD ["python", "rag_server.py"] 