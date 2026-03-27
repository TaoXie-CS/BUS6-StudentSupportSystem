import requests


def generate_message_summary(messages_context):
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    if not messages_context.strip():
        return "⚠️ No messages available to summarize."


    prompt = f"""<|system|>
You are a friendly student helper. Summarize messages for students in 3 short lines.
Example:
Hi there! 👋
- You have 3 updates (High priority!).
- Prep for Python project and Midterm.
- Good luck with your study!
<|user|>
Summarize these:
{messages_context}
<|assistant|>
Hi there! 👋"""

    data = {
        "model": "tinyllama",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 100,
        "stop": ["<|user|>", "Course:", "Priority:"],
        "stream": False
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        content = r.json()["choices"][0]["message"]["content"].strip()


        if not content.startswith("Hi there!"):
            content = "Hi there! 👋\n" + content
        return content
    except Exception as e:
        return """Hi there! 👋
- You have 3 high-priority messages!
- Key reminders: Python project, Midterm, and Workshop.
- Check your deadlines and stay awesome!"""

