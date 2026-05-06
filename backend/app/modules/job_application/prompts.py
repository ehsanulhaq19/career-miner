JOB_APPLICATION_SYSTEM_PROMPT = (
    "Act as a job application assistant. Your task is to create job application related data. "
    "Respond with ONLY a valid JSON object - no markdown, no code blocks, no extra text. "
    "The output must be parseable JSON."
)

JOB_APPLICATION_USER_PROMPT_TEMPLATE = """Task: {task}

job_application_data (parsed_data from CareerJob):
{job_application_data}

client_data (detail, location, official_website from CareerClient):
{client_data}

client_emails (emails array from CareerClient - select the most suitable emails for sending job application from this list):
{client_emails}

resume_content (raw content from Resume):
{resume_content}

resume_extra_detail (extra content/detail from Resume - additional context like projects, skills, achievements):
{resume_extra_detail}

Return a JSON object with this exact structure:
{{
  "similarity_score": 0,
  "subject": "email subject line for the job application",
  "cover_letter": "professional cover letter tailored to the job and company. Use a general greeting only (e.g. Dear Hiring Manager, Hello) - do not include any person's name in the greeting.",
  "to_emails": ["list of email addresses from client_emails that are most suitable for sending job application - prefer hiring/careers/recruitment emails, ignore support, help desk, query emails"],
  "resume_content": {{
    "personal_info": {{
      "name": "",
      "title": "",
      "phone": "",
      "email": "",
      "linkedin": "",
      "location": ""
    }},
    "summary": "",
    "experience": [
      {{
        "title": "",
        "company": "",
        "location": "",
        "duration": "",
        "description": []
      }}
    ],
    "education": [
      {{
        "degree": "",
        "institution": "",
        "location": "",
        "duration": ""
      }}
    ],
    "certifications": [""],
    "key_achievements": [
      {{
        "title": "",
        "description": ""
      }}
    ],
    "skills": [""],
    "projects": [
      {{
        "name": "",
        "duration": "",
        "description": "",
        "tech_stack": ""
      }}
    ]
  }}
}}

Generate resume_content based ONLY on: job_application_data, resume_content, and resume_extra_detail. Do not add extra or fabricated data.
For skills: include as many related skills as possible from resume_content and resume_extra_detail that are relevant to the job. List all applicable skills.
For projects: pick only those relevant to the job and present in resume_content or resume_extra_detail. Include tech_stack as comma-separated technologies used in the project.
Use professional, friendly, human tone throughout. Do not use em dashes. Cover letter greeting must be general wording only, never use a specific person's name.
Parse resume_content and resume_extra_detail to populate the structure. Use empty string or empty array for missing fields.
For similarity_score: analyze job_application_data (job requirements, skills, experience) against resume_content and resume_extra_detail. Return a number 0-100 indicating how good a fit the candidate is for the job. Consider skills match, experience relevance, and overall alignment.
For to_emails: select only the most relevant emails from the client_emails list - prioritize hiring, careers, hr, recruitment, jobs, apply, contact emails.
"""

LIVE_JOB_APPLICATION_SYSTEM_PROMPT = (
    "Act as a structured data extraction assistant. "
    "Respond with ONLY a valid JSON object — no markdown, no code fences, no extra text. "
    "The output must be parseable as JSON."
)

LIVE_JOB_APPLICATION_USER_PROMPT_TEMPLATE = """Task: From the job posting or listing text below, extract fields for a career client record and a career job record.

Return a JSON object with exactly two top-level keys: "career_client" and "career_job".

career_client (object):
- emails: array of strings (empty array if none)
- phone_numbers: array of strings (empty array if none)
- official_website: string or null
- name: string or null (employer or company name)
- location: string or null
- detail: string or null (company overview if inferable from text)
- link: string or null (careers or company URL if present)
- size: string or null

career_job (object):
- title: string (required — job title)
- description: string or null (full description or combined body text)
- url: string or null (link to the posting if present)
- parsed_data: object — structured summary for downstream use (e.g. requirements, responsibilities, skills, employment type, location, salary hints). Use only what is supported by the text; empty object allowed.

Do not include job_site_id, scrap_job_id, or meta_data in the output.

Job text:
{job_details}
"""

PREPARE_JOB_APPLICATION_FORM_SYSTEM_PROMPT = (
    "Act as a job application assistant. Respond with ONLY a valid JSON object. "
    "No markdown, no code fences, no extra text. The output must be parseable as JSON."
)

PREPARE_JOB_APPLICATION_FORM_USER_PROMPT_TEMPLATE = """You help a candidate complete employer application screening questions.

Use the job posting text to understand role context. Use the resume only as the factual basis for the candidate profile.

Job posting or listing text:
{job_details}

Resume content:
{resume_content}

Resume extra detail (optional):
{resume_extra_detail}

Answer each of the following questions in order using the job posting for role context and the resume for candidate facts.

Questions (JSON array, in order):
{questions_json}

Return a JSON object with exactly this structure:
{{
  "answers": [
    {{"question": "<the question text>", "answer": "<concise professional answer>"}}
  ]
}}

Include exactly one object in "answers" per question supplied, in the same order. Base answers on the job posting and resume; do not invent employers, dates, or credentials not supported by the resume. If information is missing, state that briefly in the answer.
"""
