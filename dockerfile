# Use the tiangolo/uwsgi-nginx-flask image with Python 3.9
FROM tiangolo/uwsgi-nginx-flask:python3.9

# Set environment variables to prevent Python from buffering outputs
ENV PYTHONUNBUFFERED=1

# Copy requirements.txt into a temporary location in the container
COPY requirements.txt /tmp/

# Upgrade pip and install Python packages listed in requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

RUN pip install psycopg2-binary
# Copy over the Flask application code to the app directory in the container
COPY ./app /app

# copy .env
COPY .env .env
