import random
import sqlite3
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

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

    def generate_response(self, system_prompt, user_prompt, knowledge_base=""):
        system_message = system_prompt.strip() if system_prompt else "You are a helpful assistant."
        if knowledge_base:
            system_message += f"\n\nKnowledge Base:\n{knowledge_base.strip()}"
        if self.tools:
            tool_listings = [f"- **{name}**: {info['desc']}" for name, info in self.tools.items()]
            tool_text = "You have access to the following tools:\n" + "\n".join(tool_listings)
            usage_text = (
                "If needed, you can use a tool by responding with the format:\n"
                "TOOL: tool_name arguments\n"
                "Only use a tool if it's necessary to answer the question and the information is not already in the knowledge base or your own knowledge. "
                "After getting the tool result, I (the system) will provide it to you, and then you should answer the question using that result."
            )
            system_message += "\n\n" + tool_text + "\n" + usage_text

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ]

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

@app.route("/", methods=["GET"])
def index():
    return """
    <html>
      <head><title>AI Agent Demo</title></head>
      <body>
        <h1>AI Agent Demo</h1>
        <p>Enter the prompts and knowledge base below:</p>
        <form action="/chat" method="post">
          <p><strong>System Prompt:</strong><br>
             <textarea name="system" rows="4" cols="80">You are a helpful assistant.</textarea></p>
          <p><strong>Knowledge Base:</strong><br>
             <textarea name="knowledge" rows="6" cols="80">AcmeCorp Customer Database contains customer names and emails for support queries.</textarea></p>
          <p><strong>User Prompt:</strong><br>
             <textarea name="user" rows="3" cols="80">What is the email of Alice from the customer database?</textarea></p>
          <p><button type="submit">Ask</button></p>
        </form>
      </body>
    </html>
    """

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        system_prompt = request.args.get("system", "")
        knowledge = request.args.get("knowledge", "")
        user_prompt = request.args.get("user", "")
    else:
        if request.is_json:
            data = request.get_json()
            system_prompt = data.get("system", "")
            knowledge = data.get("knowledge", "")
            user_prompt = data.get("user", "")
        else:
            system_prompt = request.form.get("system", "")
            knowledge = request.form.get("knowledge", "")
            user_prompt = request.form.get("user", "")

    answer = agent.generate_response(system_prompt, user_prompt, knowledge)
    if request.is_json:
        return jsonify({"answer": answer})
    else:
        return f"<h2>Answer:</h2><p>{answer}</p>"

if __name__ == "__main__":
    app.run(debug=True)