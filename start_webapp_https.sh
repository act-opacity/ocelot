#!/bin/bash
venv/bin/gunicorn --certfile app/certs/cert.pem --keyfile app/certs/key.pem -b :5000 --access-logfile - --error-logfile - opacity_webapp:app
