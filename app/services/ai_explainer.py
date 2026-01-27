import json
import os
import time

# # OpenRouter Configuration
# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# # Using the key provided by the user
# OPENROUTER_API_KEY = "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"
# SITE_URL = "http://localhost:8000"
# SITE_NAME = "Clinical Data Quality Checker"

# # Diverse pool of Free AI models to avoid 429 (Rate Limits) and 404 (Unavailability)
# AI_MODELS = [
#     "meta-llama/llama-3.3-70b-instruct:free",
#     "meta-llama/llama-3.2-3b-instruct:free",
#     "qwen/qwen-2.5-vl-7b-instruct:free",
#     "liquid/lfm-2.5-1.2b-thinking:free",
#     "xiaomi/mimo-v2-flash:free",
#     "openai/gpt-oss-20b:free",
#     "deepseek/deepseek-r1-0528:free"
# ]
# _model_index = 0

# def explain_issue(issue, row_data, model_name=None):
#     global _model_index
    
#     # Enhanced prompt for detailed analytics
#     prompt = f"""
#     You are a Senior Clinical Data Scientist. Provide a comprehensive, detailed analysis of this specific data quality issue.
    
#     Context:
#     - Issue Found: {issue.get('issue')}
#     - Column Name: {issue.get('column')}
#     - Row Data Context: {row_data}

#     Instructions:
#     1. **Deep Dive**: Explain specifically why this value is erroneous or suspicious in a clinical context. Use medical knowledge if applicable (e.g., physiological ranges).
#     2. **Clinical Impact**: Detail the downstream consequences on diagnosis, treatment planning, or statistical modeling.
#     3. **Remediation**: Provide a concrete, actionable step to resolve this.
    
#     Output Format:
#     Return your response as plain text. Do not use HTML tags or Markdown formatting. 
#     Format each section clearly with labels: "DETAILED OBSERVATION:", "CLINICAL IMPACT:", and "RECOMMENDED ACTION:".
#     """

#     max_total_attempts = 5
    
#     for attempt in range(max_total_attempts):
#         # Pick the next model in rotation
#         current_model = AI_MODELS[_model_index % len(AI_MODELS)]
#         _model_index += 1
        
#         try:
#             headers = {
#                 "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#                 "HTTP-Referer": SITE_URL,
#                 "X-Title": SITE_NAME,
#                 "Content-Type": "application/json"
#             }
            
#             payload = {
#                 "model": current_model,
#                 "messages": [
#                     {"role": "system", "content": "You are a helpful expert clinical data assistant. Output strictly plain text."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 "temperature": 0.2
#             }

#             response = requests.post(
#                 OPENROUTER_URL,
#                 headers=headers,
#                 json=payload,
#                 timeout=25
#             )
            
#             if response.status_code == 429:
#                 print(f"Rate limit hit for {current_model}. Rotating to next...")
#                 time.sleep(0.5)
#                 continue
            
#             if response.status_code in [404, 403, 401]:
#                 print(f"Model Unfetchable ({response.status_code}) for {current_model}. Skipping...")
#                 continue

#             response.raise_for_status()
#             result = response.json()
#             ai_content = result['choices'][0]['message']['content']
#             # Clean up any residual markdown if the AI ignored instructions
#             ai_content = ai_content.replace("```text", "").replace("```", "").strip()
#             return ai_content

#         except Exception as e:
#             print(f"AI Error with {current_model}: {e}")
#             if attempt < max_total_attempts - 1:
#                 time.sleep(0.5)
#                 continue
#             return _get_fallback_explanation(issue)
    
#     return _get_fallback_explanation(issue)

# def _get_fallback_explanation(issue):
#     """Provide a static explanation if AI is unavailable."""
#     issue_desc = issue.get('issue', '').lower()
#     col = issue.get('column', 'Unknown')
    
#     if "missing" in issue_desc:
#         return f"DETAILED OBSERVATION: Missing data detected in field '{col}'.\nCLINICAL IMPACT: Incomplete records can bias analysis or lead to patient identification errors.\nRECOMMENDED ACTION: Verify source documents and backfill if possible."
#     elif "outlier" in issue_desc:
#         return f"DETAILED OBSERVATION: Statistical outlier detected in '{col}'.\nCLINICAL IMPACT: Extreme values may skew averages/models or indicate entry errors.\nRECOMMENDED ACTION: Cross-reference with clinical notes to confirm validity."
#     elif "duplicate" in issue_desc:
#         return f"DETAILED OBSERVATION: Duplicate record detected.\nCLINICAL IMPACT: Inflates sample size and biases statistical power.\nRECOMMENDED ACTION: Remove duplicate entries while preserving one unique copy."
#     else:
#         return "Standard data quality check failed. Review manually."

# ==========================================
# OpenRouter (DISABLED)
# ==========================================
# OPENROUTER_API_KEY = "sk-or-xxxxxxxxxxxxxxxx"
# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ==========================================
# Local Ollama Configuration
# ==========================================
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL_NAME = "deepseek-r1:1.5b"


import httpx
import asyncio
from langsmith import traceable
from app.services.vector_db import find_similar_issue, store_explanation

@traceable(name="Clinical Issue Explanation")
async def explain_issue(issue: dict, row_data: dict) -> str:
    # 1. First, check semantic cache (ChromaDB)
    try:
        match = await find_similar_issue(issue.get('issue'), issue.get('column'), row_data, threshold=0.92)
        if match:
            print(f"✨ [SEMANTIC HIT] Reusing cached explanation (Confidence: {match['similarity']:.2f})")
            return match['explanation']
    except Exception as e:
        print(f"⚠️ Vector DB Search Error: {e}")

    # 2. If no hit, proceed with local DeepSeek (as requested for analysis) ...
    prompt = f"""
You are a Senior Clinical Data Scientist.

Context:
- Issue Found: {issue.get('issue')}
- Column Name: {issue.get('column')}
- Row Data Context: {row_data}

Instructions:
1. Explain why this value is erroneous or suspicious in a clinical context.
2. Describe the downstream clinical or analytical impact.
3. Provide a concrete remediation step.

Return plain text only.
Use EXACT labels:
DETAILED OBSERVATION:
CLINICAL IMPACT:
RECOMMENDED ACTION:
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": LOCAL_MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_URL,
                    json=payload,
                    timeout=120
                )

                response.raise_for_status()
                explanation = response.json().get("response", "").strip()
                
                # Strip DeepSeek thinking tags if they leak into internal analysis
                if "</think>" in explanation:
                    explanation = explanation.split("</think>")[-1].strip()

                # 3. Store the new explanation in ChromaDB for future intelligence
                try:
                    store_explanation(issue.get('issue'), issue.get('column'), row_data, explanation)
                except Exception as ve:
                    print(f"⚠️ Vector DB Storage Error: {ve}")
                    
                return explanation

        except Exception as e:
            print(f"❌ Local DeepSeek Error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            
    return _get_fallback_explanation(issue)


def _get_fallback_explanation(issue: dict) -> str:
    col = issue.get("column", "Unknown")
    desc = issue.get("issue", "").lower()

    if "missing" in desc:
        return (
            f"DETAILED OBSERVATION: Missing value detected in '{col}'.\n"
            "CLINICAL IMPACT: Missing clinical data can bias analysis or affect patient safety.\n"
            "RECOMMENDED ACTION: Retrieve the original value or apply clinically justified imputation."
        )

    if "outlier" in desc:
        return (
            f"DETAILED OBSERVATION: Outlier detected in '{col}'.\n"
            "CLINICAL IMPACT: Extreme values may indicate data entry errors or abnormal physiology.\n"
            "RECOMMENDED ACTION: Validate against source clinical records."
        )

    if "duplicate" in desc:
        return (
            "DETAILED OBSERVATION: Duplicate record detected.\n"
            "CLINICAL IMPACT: Inflates sample size and biases statistical analysis.\n"
            "RECOMMENDED ACTION: Remove duplicates while retaining one authoritative record."
        )

    return (
        "DETAILED OBSERVATION: Data quality issue detected.\n"
        "CLINICAL IMPACT: May compromise downstream clinical analysis.\n"
        "RECOMMENDED ACTION: Manual review recommended."
    )

async def ollama_chat(prompt: str) -> str:
    """Specialized chat function using only the local DeepSeek model."""
    print(f"📡 [OLLAMA] Sending chat request (Prompt length: {len(prompt)})")
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": f"You are a Clinical Data Assistant. Answer surgically.\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 800
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(OLLAMA_URL, json=payload, timeout=90)
            if response.status_code == 200:
                ai_response = response.json().get("response", "").strip()
                
                # Strip DeepSeek thinking tags
                if "</think>" in ai_response:
                    ai_response = ai_response.split("</think>")[-1].strip()
                
                if ai_response:
                    print(f"✅ [OLLAMA] Received response ({len(ai_response)} chars)")
                    return ai_response
            else:
                print(f"❌ [OLLAMA] HTTP Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ [OLLAMA] Chat Exception: {e}")
    return ""
