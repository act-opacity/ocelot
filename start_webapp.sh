#!/bin/bash
# this script is used to boot a Docker container
venv/bin/gunicorn -b :5000 --access-logfile - --error-logfile - opacity_webapp:app
