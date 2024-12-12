FROM python:3.12

RUN apt-get update && \
    apt-get clean

# set working directory
WORKDIR /app

# Copy the entire API directory correctly
COPY . /app/api

# Install dependencies
RUN pip install -r api/requirements.txt

ENV FLASK_ENV PRODUCTION
ENV FLASK_RUN_PORT 5328
EXPOSE 5328

# run flask server
#CMD ["python3", "-m", "flask", "--app", "api.backend.index", "--debug", "run", "-p", "5328"]
#CMD ["python3", "-m", "flask", "--app", "api.backend.index", "run", "--host=0.0.0.0", "--port=5328"]

CMD ["gunicorn", "--workers=1", "--threads=100", "--worker-class=gthread", "api.backend.index:app", "--bind=0.0.0.0:5328"]
