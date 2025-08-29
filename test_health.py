from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app()
print('Testing health endpoint...')

with app.test_client() as client:
    response = client.get('/health')
    print('Status:', response.status_code)
    print('Response:', response.get_json())