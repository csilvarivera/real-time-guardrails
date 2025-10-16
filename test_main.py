import json
import pytest
from unittest.mock import MagicMock, patch
from main import app, check_chunk_safety, generate_and_audit_stream

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Tests for check_chunk_safety ---

@patch('main.audit_client.models.generate_content')
def test_check_chunk_safety_safe(mock_generate_content):
    """Test that check_chunk_safety returns True for 'SAFE' response."""
    mock_response = MagicMock()
    mock_response.text = 'SAFE'
    mock_generate_content.return_value = mock_response

    assert check_chunk_safety('some safe text') is True
    mock_generate_content.assert_called_once()

@patch('main.audit_client.models.generate_content')
def test_check_chunk_safety_unsafe(mock_generate_content):
    """Test that check_chunk_safety returns False for 'UNSAFE' response."""
    mock_response = MagicMock()
    mock_response.text = 'UNSAFE'
    mock_generate_content.return_value = mock_response

    assert check_chunk_safety('some unsafe text') is False

@patch('main.audit_client.models.generate_content')
def test_check_chunk_safety_api_error(mock_generate_content):
    """Test that check_chunk_safety returns True (fail-safe) on API error."""
    mock_generate_content.side_effect = Exception('API is down')

    assert check_chunk_safety('any text') is True

# --- Tests for generate_and_audit_stream ---

class MockStreamResponse:
    def __init__(self, text):
        self.text = text

@patch('main.check_chunk_safety')
@patch('main.client.models.generate_content_stream')
def test_generate_and_audit_stream_safe_full_stream(mock_generate_content, mock_check_safety):
    """Test a full stream where all chunks are safe."""
    mock_check_safety.return_value = True
    mock_stream = [
        MockStreamResponse('Hello'),
        MockStreamResponse(' world'),
        MockStreamResponse('!')
    ]
    mock_generate_content.return_value = mock_stream

    generator = generate_and_audit_stream('test prompt')
    results = list(generator)

    assert len(results) == 3
    assert json.loads(results[0].split('data: ')[1]) == {'text': 'Hello'}
    assert json.loads(results[1].split('data: ')[1]) == {'text': ' world'}
    assert json.loads(results[2].split('data: ')[1]) == {'text': '!'}
    assert mock_check_safety.call_count == 3

@patch('main.check_chunk_safety')
@patch('main.client.models.generate_content_stream')
def test_generate_and_audit_stream_stops_on_unsafe(mock_generate_content, mock_check_safety):
    """Test that the stream stops immediately when an unsafe chunk is detected."""
    # The safety check fails on the second chunk
    mock_check_safety.side_effect = [True, False]
    mock_stream = [
        MockStreamResponse('This is safe.'),
        MockStreamResponse(' This is not.'),
        MockStreamResponse(' This should not be sent.')
    ]
    mock_generate_content.return_value = mock_stream

    generator = generate_and_audit_stream('test prompt')
    results = list(generator)

    assert len(results) == 2 # First chunk + STOP signal
    assert json.loads(results[0].split('data: ')[1]) == {'text': 'This is safe.'}
    assert json.loads(results[1].split('data: ')[1]) == {'text': '[STOP]'}
    assert mock_check_safety.call_count == 2

# --- Tests for /chat endpoint ---

@patch('main.generate_and_audit_stream')
def test_chat_endpoint_success(mock_generate_stream, client):
    """Test the /chat endpoint for a successful request."""
    mock_generate_stream.return_value = [
        f"data: {json.dumps({'text': 'response'})}\n\n"
    ]
    response = client.post('/chat', json={'prompt': 'a test prompt'})

    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    mock_generate_stream.assert_called_once_with('a test prompt')

def test_chat_endpoint_no_prompt(client):
    """Test the /chat endpoint when no prompt is provided."""
    response = client.post('/chat', json={})

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Prompt is required'}