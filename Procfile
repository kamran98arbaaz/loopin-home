web: python test_import.py && flask db upgrade && gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300
