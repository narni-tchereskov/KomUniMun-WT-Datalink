FROM python:3.11-slim

WORKDIR /app

# Install dependencies, order matters for caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code.
COPY src/ ./src/
COPY .env .

# Create the public keys folder to avoid crashes.
RUN mkdir -p public_keys

# Expose port, match in .env file.
EXPOSE 5000

# Handler runs the server.
CMD ["python", "-m", "src.drivers.handler"]
