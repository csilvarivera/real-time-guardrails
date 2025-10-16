from flask import Flask, request, Response, jsonify, stream_with_context
from flask_cors import CORS
import json
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from google.genai.types import HttpOptions

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for the /chat endpoint
CORS(app, resources={r"/chat": {"origins": "*"}})

# --- Vertex AI Configuration ---
# Configure the application to use Vertex AI
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'True'
# Replace with your Google Cloud project ID
os.environ['GOOGLE_CLOUD_PROJECT'] = 'your-project-id' 
# Specify the region for Vertex AI
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1' 

# --- Gemini Model Configuration ---
# Create a client for the Vertex AI API
client = genai.Client(http_options=HttpOptions(api_version="v1"))
audit_client = genai.Client(http_options=HttpOptions(api_version="v1"))
# Specify the Gemini model to use
MODEL_NAME = "gemini-2.5-flash"

def check_chunk_safety(full_response_context):
    """
    Checks the safety of the given text using the audit model.

    Args:
        full_response_context: The full response context to be audited.

    Returns:
        True if the content is safe, False otherwise.
    """
    # System prompt for the safety auditor model
    system_prompt = """
    You are a very strict AI safety auditor. Your only task is to determine if the given text is safe or unsafe. Respond with ONLY the word "SAFE" or "UNSAFE". Do not provide any other explanation.

    Unsafe content includes, but is not limited to:
    - Hate speech, harassment, insults, or bullying.
    - Any form of violence, gore, or discussion of weapons.
    - Self-harm or encouragement of dangerous acts.
    - Explicit or suggestive material.
    - Instructions or descriptions of illegal or ethically questionable activities (e.g., surveillance, hacking).

    **If you are even slightly unsure, you must classify the content as UNSAFE.** Be extremely cautious.
    """
    try:
        # Configuration for the audit model
        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=1,
            seed=0,
            system_instruction=[types.Part.from_text(text=system_prompt)],
        )
        app.logger.debug(f"IN AUDIT DECISION:")
        # Call the audit model to check the safety of the content
        response = audit_client.models.generate_content(
            model=MODEL_NAME,
            contents=full_response_context,
            config=config
        )
        # Get the decision from the audit model
        decision = response.text.strip().upper()
        app.logger.debug(f"AUDIT DECISION: {decision}")
        # Return True if the content is safe, False otherwise
        return decision == "SAFE"
    except Exception as e:
        app.logger.error(f"Error during safety check: {e}")
        # Fail-safe: If the audit fails, default to safe
        return True

def generate_and_audit_stream(prompt):
    """
    Generates a response stream and audits it in real-time.

    Args:
        prompt: The user's prompt.

    Yields:
        Server-Sent Events (SSE) with the generated text or a stop signal.
    """
    # Initialize the full response context
    full_response_context = ""
    # Generate a streaming response from the main model
    responses = client.models.generate_content_stream(model=MODEL_NAME, contents=prompt)

    # Iterate over the streaming response
    for response in responses:
        # Get the text from the response chunk
        chunk_text = response.text
        app.logger.debug(f"MAIN MODEL CHUNK: {chunk_text}")
        # Append the chunk to the full response context
        full_response_context += chunk_text

        # Check the safety of the full response context
        if not check_chunk_safety(full_response_context):
            # If the content is unsafe, send a stop signal and terminate the stream
            yield f"data: {json.dumps({'text': '[STOP]'})}\n\n"
            return

        # If the content is safe, send the chunk to the frontend
        yield f"data: {json.dumps({'text': chunk_text})}\n\n"

@app.route("/chat", methods=["POST"])
def chat():
    """
    Handles the chat requests.

    Returns:
        A streaming response with the generated text or an error message.
    """
    # Get the prompt from the request body
    data = request.get_json()
    prompt = data.get("prompt")

    # Return an error if the prompt is missing
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # Return a streaming response with the generated text
    return Response(stream_with_context(generate_and_audit_stream(prompt)), mimetype="text/event-stream")

if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True, port=5001)