CAREER_CLIENT_OUTREACH_SYSTEM_PROMPT = (
    "Act as a professional career outreach assistant. Your task is to create a tailored resume "
    "and cover letter for contacting a company about career opportunities. "
    "Respond with ONLY a valid JSON object - no markdown, no code blocks, no extra text. "
    "The output must be parseable JSON."
)

CAREER_CLIENT_OUTREACH_USER_PROMPT_TEMPLATE = """Task: {task}

company_context (from CareerClient: use detail as the primary description of the company; include name, location, official_website, size when helpful):
{company_context}

target_recipient_email (address the outreach will be sent to):
{target_email}

resume_content (raw content from candidate Resume):
{resume_content}

resume_extra_detail (extra context from Resume):
{resume_extra_detail}

Return a JSON object with this exact structure:
{{
  "subject": "clear professional email subject line for outreach to this company",
  "cover_letter": "professional cover letter tailored to the company and role type implied by company_context. Use a general greeting only (e.g. Dear Hiring Manager, Hello) - do not use any person's name in the greeting.",
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

Generate resume_content based ONLY on resume_content and resume_extra_detail, aligned with the type of company in company_context. Do not fabricate employers, degrees, or credentials not supported by the resume fields.
Use professional, friendly, human tone. Do not use em dashes. Cover letter greeting must be general wording only.
Parse resume fields to populate the structure. Use empty string or empty array for missing fields.
For skills: include relevant skills from the resume that fit roles typically hired by this kind of company.
For projects: include projects present in resume_content or resume_extra_detail; set tech_stack as comma-separated technologies.
"""
