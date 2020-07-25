#!/bin/bash
venv/bin/gunicorn -b :5000 --access-logfile - --error-logfile - opacity_webapp:app
