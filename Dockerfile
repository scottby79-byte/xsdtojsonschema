FROM python:3.13-slim

RUN python -m pip install --upgrade pip

RUN pip install lxml
RUN pip install Flask
RUN pip install python-dotenv
RUN pip install Werkzeug
RUN pip install gunicorn

WORKDIR /app

COPY webapp.py /app
COPY xsdtojson /app/xsdtojson
COPY templates /app/templates

CMD ["gunicorn","-w", "3", "-t", "3", "-b", "0.0.0.0:8080", "webapp:app"]