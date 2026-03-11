JOB_PARSER_SYSTEM_PROMPT = (
    "Act as a text parser for job description prompt. "
    "Respond with ONLY a valid JSON array - no markdown, no code blocks, no extra text."
)

JOB_PARSER_USER_PROMPT_TEMPLATE = """Return data of every job in JSON format. For each job provide:
{{
    "job_title": "",
    "job_type": "",
    "location": "",
    "skills": [],
    "experience": "",
    "salary": "",
    "company_name": "",
    "company_emails": "",
    "company_numbers": "",
    "company_link": "",
    "company_size": "",
    "job_link": "",
    "job_posted_datetime": ""
}}

Return a JSON array of objects only. Use empty string or empty array for missing fields. job_link should be the primary job URL from the input. Output must be valid JSON with no markdown formatting.

Jobs to parse:
{jobs_json}
"""
