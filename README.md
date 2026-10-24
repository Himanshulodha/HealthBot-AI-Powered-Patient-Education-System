HealthBot: AI-Powered Patient Education System

HealthBot is a LangGraph-based patient education prototype. It retrieves current medical information with the Tavily search tool, creates a short patient-friendly summary with Google Gemini, asks one comprehension question, grades the patient's answer, and provides supporting evidence from the summary.

This project is for educational purposes only. It does not provide medical diagnosis, treatment, or personalized medical advice.

Main Features:-

Accepts a health topic from the patient.
Uses Gemini to create a Tavily search request.
Retrieves information from medical sources.
Creates exactly three short patient-friendly paragraphs.
Includes source citations in the summary.
Generates one question from the summary.
Accepts and grades the patient's answer.
Displays a grade, explanation, and supporting citation.
Allows the patient to learn another topic or exit.
Clears all previous state before starting a new topic.

Project Workflow:-

START
  -> Collect health topic
  -> Gemini creates Tavily search call
  -> Tavily retrieves medical sources
  -> Gemini creates three-paragraph summary
  -> Display summary and sources
  -> Patient presses Enter when ready
  -> Generate one comprehension question
  -> Collect patient answer
  -> Grade answer and provide citation
  -> Ask whether to continue
       -> Yes: clear state and start again
       -> No: END

Files:- 

Healthbot.ipynb                  - Complete project notebook
requirements.txt                 - Required Python packages
config.env                       - API-key template
README.md                        - Project instructions

Environment Setup:-

Python 3.11 is recommended.
Create a virtual environment:
uv venv --python 3.11
Activate it on Windows:
.\.venv\Scripts\Activate

Install the packages:-
uv add -r requirements.txt

Alternatively:-
pip install -r requirements.txt

API Configuration:-
Copy config.env.example and rename the copy to config.env.

Add your own active API keys:

GOOGLE_API_KEY="your-google-api-key"
TAVILY_API_KEY="your-tavily-api-key"



Run the Project:-

Open HealthBridge_Gemini_Fixed.ipynb in Jupyter Notebook or VS Code.
Restart the notebook kernel.
Run all cells from top to bottom.
Enter a real medical topic, such as cancer or hypertension.
Read the generated summary.
Press Enter when the notebook asks whether you are ready.
Type a meaningful answer to the comprehension question.
Enter no to finish or yes to start another topic.
Save the successfully executed notebook.



Example Output

HEALTHBRIDGE - PATIENT EDUCATION
Selected topic: Cancer

Searching reputable medical sources...
Search completed: 3 source(s) retrieved.
Creating a short patient-friendly summary...
Summary completed: 3 short paragraphs created.

PATIENT SUMMARY: CANCER
[Three short paragraphs with Source citations]

COMPREHENSION CHECK
[One question based only on the summary]
> Patient answer

GRADE: A/B/C/D/F
EXPLANATION: Reason for the grade
SUPPORTING CITATION: Evidence from the summary [Source N]

Learn another health topic? (yes/no):
> no

HealthBridge session completed.


Common Errors:-

Gemini error 429
The Gemini API quota is exhausted. Wait for the quota reset or use an account and model with available quota.

Tavily error 432
The Tavily plan usage limit is exhausted. Restore Tavily credits or wait for the plan reset.

Gemini AFC warning
The automatic function-calling message is a warning, not a workflow failure. The project can still execute successfully.

Privacy and Safety:-
API keys are stored outside the notebook.
The project does not invent fallback medical information when retrieval fails.
Summary and grading prompts use only the provided evidence.
Previous topic data is cleared before a new session.
The chatbot is an educational prototype and cannot replace a qualified healthcare professional.



Model Note
Google Gemini is used because OpenAI API access was unavailable. The original capstone rubric names OpenAI, so this substitution should be disclosed if required by the evaluator.