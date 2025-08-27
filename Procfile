web: python startup.py && flask db upgrade && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --max-requests 1000 --max-requests-jitter 100
