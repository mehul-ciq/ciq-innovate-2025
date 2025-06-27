import random
import sqlite3
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "super-secret-key"

class CCP_Agent:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        self.cursor.executemany(
            "INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
            [(1, "Alice", "alice@example.com"), (2, "Bob", "bob@example.com"), (3, "Charlie", "charlie@example.com")]
        )
        self.conn.commit()

        def get_weather(city):
            conditions = ["sunny", "cloudy", "rainy", "stormy", "windy"]
            temp = random.randint(15, 30)
            condition = random.choice(conditions)
            return f"The weather in {city} is {condition} with a temperature of {temp}°C."

        def query_db(sql_query):
            try:
                cur = self.conn.execute(sql_query)
                rows = cur.fetchall()
                return "\n".join(str(row) for row in rows) if rows else "No results."
            except Exception as e:
                return f"Query error: {e}"

        self.tools = {
            "get_weather": {"func": get_weather, "desc": "Fetches the current weather for a given city. Usage: get_weather(\"city_name\")"},
            "query_db": {"func": query_db, "desc": "Executes an SQL query on the customer database. Usage: query_db(\"SELECT ...\")"}
        }

    def generate_response(self, system_prompt, messages):
        client = OpenAI(
            api_key="sk-WRDSNGPePp-cHG5Q6WhRjA",
            base_url="https://ciq-litellm-proxy-service.prod-dbx.commerceiq.ai"
        )

        final_answer = None
        for _ in range(3):
            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            assistant_reply = response.choices[0].message.content.strip()

            if assistant_reply.upper().startswith("TOOL:"):
                tool_call = assistant_reply[len("TOOL:"):].strip()
                parts = tool_call.split(maxsplit=1)
                tool_name = parts[0]
                tool_args = parts[1].strip('()"\'') if len(parts) > 1 else ""
                if tool_name in self.tools:
                    try:
                        result = self.tools[tool_name]["func"](tool_args) if tool_args else self.tools[tool_name]["func"]()
                    except Exception as e:
                        result = f"(Tool `{tool_name}` execution error: {e})"
                else:
                    result = f"(Unknown tool `{tool_name}` requested.)"
                observation_message = f"Tool result ({tool_name}): {result}"
                messages.append({"role": "system", "content": observation_message})
                continue
            else:
                final_answer = assistant_reply
                break

        if final_answer is None:
            final_answer = assistant_reply
        return final_answer

agent = CCP_Agent()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        system_prompt = request.form.get("system", "You are a helpful assistant.")
        knowledge = request.form.get("knowledge", "")
        tool_info = "\n\nYou have access to the following tools:\n"
        tool_info += "\n".join(f"- {name}: {tool['desc']}" for name, tool in agent.tools.items())
        tool_info += "\n\nExample:\nUser: What is the weather in London?\nAssistant: TOOL: get_weather(\"London\")\n"
        tool_info += "User: What is the email of Bob?\nAssistant: TOOL: query_db(\"SELECT email FROM customers WHERE name = 'Bob'\")\n"
        session['system'] = system_prompt + "\n\nKnowledge Base:\n" + knowledge + tool_info
        session['chat'] = [{"role": "system", "content": session['system']}]
        return redirect(url_for("chat"))

    return """
    <html>
      <head><title>Setup AI Agent</title></head>
      <body>
        <h1>Initialize AI Agent</h1>
        <form method="post">
          <p><strong>System Prompt:</strong><br>
             <textarea name="system" rows="4" cols="80">You are a helpful assistant.</textarea></p>
          <p><strong>Knowledge Base:</strong><br>
             <textarea name="knowledge" rows="6" cols="80">AcmeCorp Customer Database contains customer names and emails for support queries.</textarea></p>
          <p><button type="submit">Start Chat</button></p>
        </form>
      </body>
    </html>
    """

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if 'chat' not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        user_input = request.form.get("user", "")
        session['chat'].append({"role": "user", "content": user_input})
        answer = agent.generate_response(session['system'], session['chat'])
        session['chat'].append({"role": "assistant", "content": answer})
        session.modified = True

    chat_html = "".join(f"<p><b>{m['role'].capitalize()}:</b> {m['content']}</p>" for m in session['chat'] if m['role'] != 'system')
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
