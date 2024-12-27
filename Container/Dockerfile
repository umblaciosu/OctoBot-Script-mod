# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy application files into the container
COPY app.py /app
COPY requirements.txt /app
#COPY templates /app/templates

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the Flask app will run on
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]