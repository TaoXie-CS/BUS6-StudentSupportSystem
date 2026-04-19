import requests

def generate_message_summary(messages_context, mode="summarize"):
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    if not messages_context or not messages_context.strip():
        return "⚠️ No messages available to analyze."


    if mode == "deadlines":
        instruction = "ONLY extract deadlines and tasks. Be very brief."
        prefix = "Important Deadlines ⏰"
        example = "- April 24: Python Midterm\n- Next Wed: Java Homework"
    elif mode == "motivation":
        instruction = "Summarize tasks with high energy and encouragement!"
        prefix = "Listen up, Champ! 🔥"
        example = "- You'll crush the Python exam!\n- Stay strong for Java!"
    else:

        instruction = "Summarize messages in 3-4 concise bullet points."
        prefix = "Hi there! 👋"
        example = "- 3 updates for your exams.\n- Prep for Python and Java."


    prompt = f"""<|system|>
{instruction}
Example:
{prefix}
{example}
<|user|>
Summarize these:
{messages_context}
<|assistant|>
{prefix}"""

    data = {
        "model": "tinyllama",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 300,
        "stop": ["<|user|>", "<|system|>", "Subject:", "Teacher:"],
        "stream": False
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=15)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()


        if content.startswith("-") or content.startswith(" "):
            return f"{prefix}\n{content.strip()}"
        return content if prefix in content else f"{prefix}\n{content}"

    except Exception as e:
        return f"{prefix}\n- Failed to connect to local AI.\n- Please check if LM Studio is running."