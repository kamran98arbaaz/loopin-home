web: python startup.py && flask db upgrade && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1
