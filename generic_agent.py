from flask import Flask, request, session
from openai import OpenAI
import requests
from flask_session import Session
import json


app = Flask(__name__)
app.secret_key = "super-secret-key"

app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis', 'sqlalchemy', etc.
app.config['SESSION_FILE_DIR'] = './.flask_session/'  # Optional, defaults to /tmp
Session(app)


class GenericAgent:
    def __init__(self):
        def get_ccp_execution_status(input):
            execution_id = input["execution_id"]
            url = f"http://ccp-execute-beta.commerceiq.ai/ccp/execute/{execution_id}/status"
            payload = ""
            headers = {'accept': 'application/json'}
            response = requests.request("GET", url, headers=headers, data=payload)
            return response.json() if response.status_code == 200 else f"Error: {response.status_code} - {response.text}"

        def get_ccp_execution_details(input):
            execution_id = input["execution_id"]
            url = f"http://ccp-execute-beta.commerceiq.ai/ccp/execute/{execution_id}/details"
            payload = ""
            headers = {'accept': 'application/json'}
            response = requests.request("GET", url, headers=headers, data=payload)
            return response.json() if response.status_code == 200 else f"Error: {response.status_code} - {response.text}"
        
        def get_time_till_now(input):
            from datetime import datetime
            now = datetime.now()
            other = input['other_timestamp']
            print(now.timestamp, other)
            return str(round(now.timestamp - other))
        
        self.tools = {
            "get_ccp_execution_status": {
                "func": get_ccp_execution_status,
                "desc": "Fetches the status for a ccp execution. Usage: get_ccp_execution_status(\"execution_id\")"
            },
            "get_ccp_execution_details": {
                "func": get_ccp_execution_details,
                "desc": "Fetches the more details for a ccp execution. Usage: get_ccp_execution_details(\"execution_id\")"
            },
            "get_time_till_now": {
                "func": get_time_till_now,
                "desc": "Fetches the current time. Usage: get_time_till_now()"
            }
        }

    def generate_response(self, messages):
        client = OpenAI(
            api_key="sk-WRDSNGPePp-cHG5Q6WhRjA",
            base_url="https://ciq-litellm-proxy-service.prod-dbx.commerceiq.ai"
        )

        for _ in range(6):
            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            assistant_reply = response.choices[0].message.content.strip()
            print("assistant_reply", assistant_reply)
            if "<TOOL_CALL>" in assistant_reply.upper():            
                tool_call = assistant_reply.split("<TOOL_CALL>")[1].split("</TOOL_CALL>")[0].strip().split('\n')
                tool_name = tool_call[0].split("=")[-1].strip()
                tool_args = tool_call[1].split("=")[-1].strip()
                tool_args = json.loads(tool_args) if tool_args else None

                if tool_name in self.tools:
                    try:    
                        print(f"Executing tool: '{tool_name}' with args: '{tool_args}'")
                        result = self.tools[tool_name]["func"](tool_args) if tool_args else self.tools[tool_name]["func"]()
                    except Exception as e:
                        result = f"(Tool `{tool_name}` execution error: {e})"
                else:
                    result = f"(Unknown tool `{tool_name}` requested.)"

                observation_message = f"Tool result ({tool_name}): {result}"
                messages.append({"role": "system", "content": observation_message})
                continue

            return assistant_reply

        return assistant_reply

def load_initial_context(agent):
    with open("system_prompt.txt", "r") as sp_file:
        system_prompt = sp_file.read().strip()

    with open("knowledge_base.txt", "r") as kb_file:
        knowledge = kb_file.read().strip()

    system_full = f"{system_prompt}\n\nKnowledge Base:\n{knowledge}"
    session['chat'] = [{"role": "system", "content": system_full}]

agent = GenericAgent()

@app.before_request
def initialize_session():
    load_initial_context(agent)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if 'chat' not in session:
        return "Session not initialized. Please restart the app."

    if request.method == "POST":
        user_input = request.form.get("user", "")
        session['chat'].append({"role": "user", "content": user_input})
        answer = agent.generate_response(session['chat'])
        session['chat'].append({"role": "assistant", "content": answer})
        session.modified = True

    chat_html = "".join(
        f"<p><b>{m['role'].capitalize()}:</b> {m['content']}</p>" 
        for m in session['chat'] if m['role'] != 'system')

    return f"""
    <html>
      <head><title>Chat with AI Agent</title></head>
      <body>
        <h1>Chat with AI Agent</h1>
        {chat_html}
        <form method="post">
          <p><strong>Your Message:</strong><br>
             <textarea name="user" rows="3" cols="80"></textarea></p>
          <p><button type="submit">Send</button></p>
        </form>
      </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
