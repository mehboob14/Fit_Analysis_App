#!/usr/bin/env bash
# Install Playwright browsers if not already installed
npx playwright install --with-deps

# Start Gunicorn
gunicorn app:app
