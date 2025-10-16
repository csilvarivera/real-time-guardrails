Project Instructions: Build a Streaming Chatbot with Real-Time Safety Audits via Vertex AI (v3.5)
1. Project Goal
Your primary task is to create a web-based chatbot application. The application will feature a Python backend that streams responses from a Gemini 2.5 Flash model on Vertex AI. The key feature is a real-time, context-aware safety audit: each piece of the generated response must be evaluated along with the full preceding context by a second "auditor" Gemini model. If the cumulative response is deemed unsafe, the stream to the user must be immediately terminated.

2. Core Architecture
The application will be split into two main components: a Python backend and an HTML/JavaScript frontend.

Python Backend (Flask): This server will handle all interactions with Vertex AI. It will expose a single API endpoint that the frontend calls. It is responsible for both generating the chat response and performing the safety audit.

Frontend (HTML/JS): A single, self-contained HTML file that provides the user interface. It will communicate with the backend using Server-Sent Events (SSE) to display the streaming response in real-time.

3. Backend Implementation (main.py)
You will create a Python file named main.py using the Flask web framework.

3.1. Dependencies
The backend requires the following Python libraries. Instruct the user on how to install them.

Flask

flask-cors

google-cloud-aiplatform

3.2. Server Setup
Initialize a standard Flask application.

Enable CORS to allow requests from the frontend.

Initialize the Vertex AI client: vertexai.init(project="<YOUR_PROJECT_ID>", location="<YOUR_LOCATION>").

Instantiate the Gemini model you will use for chat and audit: GenerativeModel("gemini-2.5-flash-preview-05-20").

3.3. API Endpoint: /chat
Create a single route /chat that accepts POST requests.

The endpoint should expect a JSON body with a single key: "prompt".

The response from this endpoint must be a streaming response with the mimetype text/event-stream.

This endpoint's core logic will be a Python generator function (e.g., generate_and_audit_stream).

3.4. Generator Function (generate_and_audit_stream)
This is the core logic of the backend. To ensure the safety audit is context-aware, you must accumulate the full response as it's generated.

Initialize Context: Before the loop, create an empty string variable to hold the cumulative response, e.g., full_response_context = "".

Initiate Streaming Call: Use the Vertex AI SDK to make a streaming call to the Gemini model for the main chat response.

model = GenerativeModel("gemini-2.5-flash-preview-05-20")
responses = model.generate_content(prompt, stream=True)

Iterate, Accumulate, and Audit: Loop through each response chunk from the responses stream.

Accumulate: Append the new chunk.text to your full_response_context variable.

Safety Check: Call a separate function check_chunk_safety(full_response_context). Notice you are passing the entire accumulated context, not just the latest chunk.

Conditional Yield:

If check_chunk_safety returns False: The content is unsafe. Immediately yield a special stop signal in SSE format: data: [STOP]\n\n. After yielding, return to terminate the generator and stop the stream.

If check_chunk_safety returns True: The content is safe. yield the original chunk.text (not the full context) to the frontend, formatted as a JSON object within an SSE message: data: {"text": "..."}\n\n.

3.5. Safety Audit Function (check_chunk_safety)
This function will call a Gemini model to act as a safety auditor, now evaluating the full text.

Define the System Prompt: Create a very specific, non-negotiable system prompt for the auditor model. It must be instructed to evaluate the entire text, not just a chunk.

You are an AI safety auditor. Your only task is to determine if the given text is safe or unsafe. Respond with ONLY the word "SAFE" or "UNSAFE". Do not provide any other explanation. Unsafe content includes but is not limited to: hate speech, violence, self-harm, harassment, or explicit material.

Make a Non-Streaming Call: Make a standard (non-streaming) generate_content call to the Gemini model using this system prompt and the full_response_context passed into the function. Set temperature=0.0 for a deterministic response.

Parse and Return:

Get the response text.

Clean the response (e.g., strip().upper()).

Return True if the response is exactly "SAFE", otherwise return False.

Include error handling. For a fail-safe approach, if the audit API call fails, you can default to returning True.

4. Frontend Implementation (index.html)
Create a single HTML file named index.html. It must be self-contained. The frontend logic does not need to change for this update, as it is only concerned with displaying streamed chunks and handling the [STOP] signal.

4.1. HTML Structure
A main container for the chat interface.

A scrollable div for displaying chat messages (#chat-container).

An input field for the user's message (#user-input).

A button to send the message (#send-btn).

A loading indicator to show when the AI is "typing".

4.2. Styling
Use Tailwind CSS for all styling to create a modern and responsive UI. Link to it via its CDN.

Add custom styles for a blinking cursor effect and message fade-in animations.

4.3. JavaScript Logic
All JavaScript should be within a <script> tag at the bottom of the <body>.

Event Handling: Add event listeners to the send button (click) and the input field (keydown for the 'Enter' key).

handleSendMessage Function: This function orchestrates the process.

streamResponseFromBackend Function: This function handles the fetch request and processes the SSE stream, including listening for the [STOP] signal and updating the UI accordingly.

5. README File (README.md)
Finally, generate a README.md file that explains how to set up and run the project.

Prerequisites: Note the need for Python 3.7+ and a Google Cloud project with the Vertex AI API enabled.

Authentication: Instruct the user on how to authenticate for Vertex AI (e.g., running gcloud auth application-default login).

Backend Setup: Provide the pip install commands for the dependencies.

Running the App: Explain the two steps:

Run the backend server: python main.py

Open the index.html file in a web browser.


5. Using the Vertex AI and genai package

You will always use the genai python library to call gemini:

from google import genai
from google.genai.types import HttpOptions

client = genai.Client(http_options=HttpOptions(api_version="v1"))
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="How does AI work?",
)
print(response.text)
# Example response:
# Okay, let's break down how AI works. It's a broad field, so I'll focus on the ...
#
# Here's a simplified overview:
# ...

https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart?usertype=adc#python-gen-ai-sdk