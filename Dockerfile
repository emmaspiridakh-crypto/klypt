FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Expose Flask port για UptimeRobot
EXPOSE 8080

# Start the bot via Flask app
CMD ["python", "klypt.py"]
