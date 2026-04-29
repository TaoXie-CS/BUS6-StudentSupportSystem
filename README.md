# Student Support App
A comprehensive student support platform designed to facilitate communication between students and teachers, manage appointments, provide AI-assisted support, and handle student inquiries efficiently.

## Table of Contents
- [Project Overview](#project-overview)
- [Tools & Technologies](#tools--technologies)
- [Prerequisites](#prerequisites)
- [How to Run the Project](#how-to-run-the-project)
- [Testing the Project](#testing-the-project)
- [UML Diagrams](#diagrams)
- [Troubleshooting](#troubleshooting)

## Project Overview
This system provides the following core functionalities:
- User authentication (Student, Teacher, Admin roles)
- Message management (Teachers can publish messages; Students can view and download attachments)
- Survey system (Students can submit feedback surveys; Admin can view all survey results)
- AI assistant support (Summarize content, deadline reminders, motivation, etc.)
- Appointment booking system (Students book time slots with teachers)
- Role-based access control (Different permissions for students, teachers, and admins)

## Tools & Technologies
- Programming Language: Python
- Framework: Flask
- Database: SQLite
- Frontend: HTML, Bootstrap, Jinja2
- Form Validation: Flask-WTF, WTForms
- User Authentication: Flask-Login
- Database Migration: Flask-Migrate
- ORM: SQLAlchemy
- Unit Testing: pytest
- Environment Management: Virtual Environment (venv)

## Prerequisites
- Python 3.8 or higher
- PyCharm (Recommended for easy setup) or any code editor
- Git (for cloning the repository)

## How to Run the Project
You can set up the project in **PyCharm** . 

### Method : PyCharm Setup (Recommended)
1. **Clone the Repository**  
   Open Git Bash or Terminal, run the command to clone the project:
   ```bash
   git clone -b main https://github.com/TaoXie-CS/BUS6-StudentSupportSystem
   cd BUS6-StudentSupportSystem
2. **Open Project in PyCharm**
   Launch PyCharm → Click "Open" → Select the BUS6-StudentSupportSystem folder.
3. **Set Up Python Interpreter**
   Go to File > Settings > Project: BUS6-StudentSupportSystem > Python Interpreter (Windows)
   Or PyCharm > Settings > Project: BUS6-StudentSupportSystem > Python Interpreter (Mac)
   Click the Add (+) button → Select "New Virtual Environment"
   Choose "Python Interpreter" → Select the appropriate Python version (3.8+)
   Click "OK" to create and set the virtual environment as the project interpreter.
4. **Install Dependencies**
   Open the PyCharm Terminal (bottom panel) and run:
   pip install -r requirements.txt
   
   Then initialize the database:
   flask shell
   db.create_all()

   Copy and paste all content from origin_data.txt into the Flask shell to initialize the data.
5. **Open Local LLM (for ai-assistant)**
   Download and launch LM Studio.

   Install and load the following model:
   Model: tinyllama-1.1b-chat-v1.0
   Version: Q4_K_M

   Make sure the model status shows Running before starting the system.
6. **Run Project**
   In the PyCharm Terminal, run:
   flask run
   
   Open your browser and visit:
   http://127.0.0.1:5000

   
## Testing the Project
To run the test cases and verify system functionality:
All test files are located in the tests/ folder.
To run a specific test file, use the following command in the project root directory:
   python -m pytest "tests/ai_assistant_tests/test_ai_assistant.py" -v
   


## UML Diagrams
All UML diagrams are stored in the /docs/diagram folder, including:
Class Diagram
Sequence Diagram

## Troubleshooting
If you encounter errors while running the project:

When facing **sqlalchemy.exc.OperationalError**:
1. Stop the project
2. Delete the `app.db` file
3. Run `flask shell` in the terminal
4. Run `db.create_all()`
5. Copy and paste all content from `origin_data.txt` to initialize the data







Github link:https://github.com/TaoXie-CS/BUS6-StudentSupportSystem

