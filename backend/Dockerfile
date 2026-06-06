# Use the stable 'bookworm' release to prevent random Linux package name changes
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install WeasyPrint system dependencies (Updated package names)
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install gunicorn for production-grade server running
RUN pip install gunicorn

# Copy the rest of your backend code into the container
COPY . .

# Expose port 5000
EXPOSE 5000

# Command to run the Flask app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]