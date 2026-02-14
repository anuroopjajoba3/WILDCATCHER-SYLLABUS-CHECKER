import pytest
import json
import sys
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestHomeRoute:
    def test_home_status(self, client):
        r = client.get('/')
        assert r.status_code == 200

class TestUploadRoute:
    def test_upload_no_file(self, client):
        r = client.post('/upload')
        assert r.status_code == 400

class TestAskRoute:
    def test_ask(self, client):
        r = client.post('/ask', 
            data=json.dumps({'message': 'help'}),
            content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert 'response' in data
