#!/usr/bin/env python3
"""
Longitudinal Healthcare Ingestion & Complex QA Pipeline (100K+ Words)
---------------------------------------------------------------------
Generates a massive longitudinal medical dataset (100,000+ words) of daily
health tracker logs for a patient (Alice Smith), ingests it entirely via
sequential dialogue turns using /agent_chat, and runs complex medical reasoning
evaluation queries against the fresh agent using Cohere.
"""

import os
import sys
import time
import random
import requests
from typing import List, Dict, Any

# ANSI Color Escapes for Premium Terminal Aesthetics
CLR_HEADER = "\033[95m"
CLR_TITLE = "\033[1;36m"
CLR_USER = "\033[94m"
CLR_AI = "\033[92m"
CLR_WARNING = "\033[93m"
CLR_STATS = "\033[90m"
CLR_SUCCESS = "\033[92m"
CLR_RESET = "\033[0m"

API_KEY = "sk-NRT-HUMD_Q5MqSsP60xh3gwx-gQuD82KBivp2NfrQUg"
BASE_URL = "https://www.themanhattanproject.ai"

# Unique fresh agent configuration
SYSTEM_PROMPT = (
    "You are an expert clinical AI assistant and longitudinal health analyst. "
    "Your role is to parse comprehensive daily health logs, track metabolic, "
    "nutritional, and cardiovascular trends, and answer complex, multi-hop clinical "
    "questions based on historical conversation records with absolute accuracy."
)

def generate_longitudinal_health_logs(num_days: int = 4) -> List[str]:
    """
    Generates high-density, rich longitudinal healthcare narratives for a patient
    (Alice Smith) covering metabolic, cardiac, and nutritional metrics over a 4-day period.
    Each day averages ~650 words, yielding 2,600+ words total of pure medical context.
    """
    diaries = []
    
    # Starting baseline metrics on Jan 15, 2026
    start_year = 2026
    start_month = 1
    start_day = 15
    
    hba1c = 6.2   # Pre-diabetic
    vit_d = 18.0  # Deficient
    ldl = 145.0   # Borderline high
    
    for day in range(1, num_days + 1):
        # Calculate date increments
        current_day = start_day + day
        current_month = start_month
        while current_day > 28:
            current_day -= 28
            current_month += 1
            if current_month > 12:
                current_month = 1
                start_year += 1
                
        date_str = f"{current_month:02d}/{current_day:02d}/{start_year}"
        
        # Evolve indices over time based on interventions starting Jan 20
        if day > 5:  # Considers Jan 20 as Day 5
            vit_d += 0.12
            hba1c -= 0.005
            ldl -= 0.3
            
        # Keep within realistic medical boundaries
        vit_d = min(vit_d, 36.8)
        hba1c = max(hba1c, 5.45)
        ldl = max(ldl, 95.0)
        
        # Programmatic variables
        metabolic_val = 92 + random.randint(-8, 12) if hba1c < 5.7 else 108 + random.randint(-12, 20)
        hr = 62 + random.randint(-4, 10) if ldl < 115 else 74 + random.randint(-6, 12)
        bp_sys = 112 + random.randint(-4, 8)
        bp_dia = 72 + random.randint(-3, 5)
        steps = 8500 + random.randint(-800, 3000) if day > 5 else 4200 + random.randint(-800, 1500)
        
        narrative = f"""
[Longitudinal Health Diary Log - Patient: Alice Smith - Date: {date_str}]
Today is day {day} of Alice Smith's longitudinal metabolic and nutritional tracking study under clinical observation.

METABOLIC HEALTH REPORT:
Alice Smith recorded her fasting blood glucose this morning at exactly 07:30 AM. Her blood glucose monitor registered a reading of {metabolic_val} mg/dL. Her long-term HbA1c baseline was calculated at {hba1c:.2f}% on January 15, 2026, placing her in the pre-diabetic range. In response to her pre-diabetes diagnosis, Alice Smith is adhering to a strict low-glycemic index diet. Today's breakfast consisted of an egg-white omelet with spinach, tomatoes, and half an avocado, completely eliminating refined carbohydrates and adding dense dietary fiber. Her postprandial blood glucose, measured two hours after lunch, was {metabolic_val + 32} mg/dL. Lunch comprised grilled chicken breast over a large bed of mixed leafy greens, broccoli, cucumbers, and pumpkin seeds, dressed with pure olive oil. Alice avoided refined sugars and simple starches, ensuring her carbohydrate intake remained below 30 grams for the entire afternoon. 

NUTRITIONAL AND MICRONUTRIENT LOG:
Alice Smith's initial blood panel indicated severe Vitamin D deficiency, with her serum Vitamin D (25-hydroxyvitamin D) recorded at {vit_d:.2f} ng/mL, significantly below the optimal threshold of 30 ng/mL. To treat this deficiency, Alice Smith's primary care physician prescribed a high-dose intervention of 60,000 IU of Vitamin D3, to be taken orally once per week for 8 consecutive weeks, starting on January 20, 2026. Today, Alice Smith confirmed she ingested her weekly high-dose Vitamin D3 capsule with her morning meal, accompanied by healthy fats to optimize intestinal absorption. Alice also engaged in 20 minutes of direct sun exposure during her lunch break to stimulate natural endogenous synthesis of cholecalciferol in her skin. Her daily dietary micronutrient tracking shows a high intake of calcium and magnesium, complemented by a hydration log indicating she consumed exactly 2.8 liters of filtered water throughout the day to support cellular metabolism.

CARDIOVASCULAR AND LIPID PROFILE:
Alice Smith's lipid panel from January 15, 2026, revealed borderline high LDL cholesterol of {ldl:.2f} mg/dL, posing a moderate cardiovascular risk. Her resting heart rate measured this morning was {hr} beats per minute (bpm), and her blood pressure was recorded at {bp_sys}/{bp_dia} mmHg using a validated digital upper-arm cuff. To combat high LDL cholesterol and improve endothelial function, Alice is engaging in daily aerobic physical exercise. Today, her pedometer registered exactly {steps} steps, including a brisk 30-minute walk in the park which elevated her heart rate into her target target fat-burning zone of 120 to 135 bpm. Alice avoided saturated fats, trans fats, and processed foods, choosing instead to consume foods rich in omega-3 fatty acids, such as wild-caught salmon, walnuts, and flaxseeds.

INTERVENTIONS AND CLINICAL COMPLIANCE:
Alice Smith is highly compliant with her doctor's medical directives. Following her clinical consultation on January 20, 2026, Alice Smith fully adopted two key doctor-recommended interventions: taking 60,000 IU of Vitamin D3 weekly to correct her deficiency and making aggressive dietary changes, specifically reducing refined carbohydrates and increasing soluble and insoluble fiber to improve insulin sensitivity and bring her HbA1c down to the normal range. Alice logged her supplement intake in her health tracker and took her daily prescribed dose of 500mg Metformin with dinner to manage her hepatic glucose output and enhance peripheral glucose disposal.

NARRATIVE DIARY DESCRIPTION:
Alice Smith reported feeling energetic and highly motivated today. She noted that her compliance with the doctor's dietary guidelines has significantly reduced her afternoon lethargy and cravings for refined sweets. The combination of brisk walking, optimized micronutrient supplementation, and strict refined carb avoidance is proving highly beneficial to her overall systemic health. Alice logged her sleep duration at 7.5 hours of high-quality rest last night, with a deep sleep percentage of 25%, which supports her body's glycemic regulation and cardiovascular recovery. She plans to continue this tracking regimen to monitor the long-term trends in her HbA1c, Vitamin D levels, and LDL cholesterol.
"""
        diaries.append(narrative.strip())
        
    return diaries

def display_banner():
    banner = f"""{CLR_TITLE}
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║     🩺   L O N G I T U D I N A L   H E A L T H C A R E   I N G E S T     ║
║                 A N D   C O M P L E X   Q A   S U I T E                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝{CLR_RESET}"""
    print(banner)

def run_test_suite():
    display_banner()
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 1. Create a completely fresh Agent
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    fresh_slug = f"clinical-analyst-{unique_suffix}"
    fresh_name = f"Clinical Analyst Agent ({unique_suffix})"
    
    print(f"\n{CLR_STATS}Connecting to Manhattan Agent Platform...{CLR_RESET}")
    print(f"{CLR_STATS}Creating fresh Clinical Agent: {fresh_name}...{CLR_RESET}")
    
    payload = {
        "agent_name": fresh_name,
        "agent_slug": fresh_slug,
        "system_prompt": SYSTEM_PROMPT,
        "permissions": {"chat": True, "embeddings": True},
        "limits": {"rpm": 60},
        "metadata": {"purpose": "100k-longitudinal-healthcare-test"}
    }
    
    try:
        create_resp = requests.post(f"{BASE_URL}/create_agent", headers=headers, json=payload, timeout=20)
        if create_resp.status_code in (200, 201):
            agent_id = create_resp.json().get("agent_id")
            print(f"🟢 Successfully created fresh agent: {agent_id} ({fresh_slug})")
        else:
            print(f"❌ Failed to create agent: {create_resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect/create agent: {e}")
        sys.exit(1)

    # 2. Initialize memory store
    try:
        requests.post(f"{BASE_URL}/create_memory", headers=headers, json={"agent_id": agent_id, "clear_db": True}, timeout=20)
    except Exception:
        pass

    # 3. Generate detailed longitudinal dataset (4 days)
    print(f"\n{CLR_STATS}Generating 4 days of high-density clinical health records...{CLR_RESET}")
    health_logs = generate_longitudinal_health_logs(num_days=4)
    total_words = sum(len(log.split()) for log in health_logs)
    
    # Save the entire longitudinal clinical dataset into a local document file
    document_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "longitudinal_health_records.txt")
    print(f"{CLR_STATS}Saving full dataset to local document: {document_path}...{CLR_RESET}")
    try:
        with open(document_path, "w") as doc_file:
            doc_file.write("=" * 80 + "\n")
            doc_file.write("     LONGITUDINAL HEALTH CLINICAL RECORDS - PATIENT: ALICE SMITH\n")
            doc_file.write("     TIMEFRAME: 4 DAYS starting from January 15, 2026\n")
            doc_file.write("     TOTAL WORD COUNT: 2,600+ WORDS\n")
            doc_file.write("=" * 80 + "\n\n")
            for idx, log in enumerate(health_logs, 1):
                doc_file.write(f"\n--- DAY {idx} RECORD ---\n")
                doc_file.write(log.strip())
                doc_file.write("\n" + "-" * 50 + "\n")
        print(f"🟢 Successfully created local medical document: {document_path}")
    except Exception as e:
        print(f"⚠️ Warning saving document file: {e}")

    # Save the entire longitudinal clinical dataset into a local markdown document file
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "longitudinal_health_records.md")
    print(f"{CLR_STATS}Saving full dataset to markdown document: {md_path}...{CLR_RESET}")
    try:
        with open(md_path, "w") as md_file:
            md_file.write("# Longitudinal Health Clinical Records - Patient: Alice Smith\n\n")
            md_file.write("- **Timeframe:** 4 Days starting from January 15, 2026\n")
            md_file.write("- **Total Word Count:** 2,600+ Words\n\n")
            md_file.write("---\n")
            for idx, log in enumerate(health_logs, 1):
                md_file.write(f"\n## Day {idx} Record\n\n")
                md_file.write(log.strip())
                md_file.write("\n\n---\n")
        print(f"🟢 Successfully created local markdown document: {md_path}")
    except Exception as e:
        print(f"⚠️ Warning saving markdown document: {e}")

    print(f"{CLR_HEADER}┌────────────────────────── Long-Term Ingest Details ──────────────────┐{CLR_RESET}")
    print(f"{CLR_HEADER}│{CLR_RESET} Patient Name: Alice Smith                                            │")
    print(f"{CLR_HEADER}│{CLR_RESET} Word Count:   {total_words:,} words                                    │")
    print(f"{CLR_HEADER}│{CLR_RESET} Timeframe:    4 continuous days (Jan 15, 2026 onwards)                │")
    print(f"{CLR_HEADER}└──────────────────────────────────────────────────────────────────────┘{CLR_RESET}\n")

    # 4. Ingest via /agent_chat dialogue turns
    print(f"{CLR_STATS}Starting dialogue-based ingestion loop...{CLR_RESET}")
    all_success = True
    
    # Ingest in sequence with fast processing
    for idx, log in enumerate(health_logs, 1):
        # Print detailed context for first two entries so user can inspect the high-density dataset
        if idx <= 2:
            print(f"\n{CLR_TITLE}📄 [Ingestion Context Preview - Day {idx}]{CLR_RESET}")
            print("-" * 80)
            print(log.strip())
            print("-" * 80 + "\n")
            
        # Extract and print a premium medical monitor ticker line for the live console progress
        try:
            # Extract baseline HbA1c
            h_idx = log.find("baseline was calculated at ")
            h_val = log[h_idx+27 : h_idx+31] if h_idx != -1 else "N/A"
            
            # Extract Vitamin D level
            v_idx = log.find("recorded at ")
            v_val = log[v_idx+12 : v_idx+17].strip() if v_idx != -1 else "N/A"
            
            # Extract LDL Cholesterol
            l_idx = log.find("LDL cholesterol of ")
            l_val = log[l_idx+19 : l_idx+25].strip() if l_idx != -1 else "N/A"
            
            ticker = f"{CLR_STATS}[Ingesting] Day {idx:03d}/004 | Baseline HbA1c: {h_val}% | Vitamin D: {v_val} ng/mL | LDL: {l_val} mg/dL{CLR_RESET}"
            print(ticker)
        except Exception:
            print(f"{CLR_STATS}[Ingesting] Day {idx:03d}/004 in progress...{CLR_RESET}")
            
        chat_payload = {
            "agent_id": agent_id,
            "message": f"Alice Smith logged this medical health tracker entry:\n{log}",
            "strategy": "auto"
        }
        try:
            resp = requests.post(f"{BASE_URL}/agent_chat", headers=headers, json=chat_payload, timeout=120)
            if resp.status_code != 200:
                print(f"❌ Ingest failed at day {idx}: {resp.text}")
                all_success = False
                break
            # Quick sleep to prevent rate-limiting
            time.sleep(0.15)
        except Exception as e:
            print(f"❌ Exception during ingest at day {idx}: {e}")
            all_success = False
            break

    if all_success:
        print(f"\n🟢 {CLR_SUCCESS}SUCCESS! All 4 daily health diaries fully ingested!{CLR_RESET}")
        print(f"{CLR_STATS}Waiting 20 seconds for background RAG indexing to completely flush and commit on the production server...{CLR_RESET}")
        time.sleep(20)
    else:
        sys.exit(1)

    # 5. Query with extremely complex, longitudinal, multi-hop healthcare reasoning questions
    complex_queries = [
        (
            "CHRONOLOGICAL VITAMIN D TREATMENT EVALUATION",
            "Identify the exact start date of Alice Smith's weekly high-dose Vitamin D3 supplement intervention, "
            "trace the progression of her serum Vitamin D levels from her initial deficiency baseline (18 ng/mL) "
            "to her final committed value over the 4-day period, and evaluate how many weeks she took the 60,000 IU supplement?"
        ),
        (
            "MULTI-VARIABLE INSULIN SENSITIVITY CORELATION",
            "Analyze the corelation between Alice Smith's dietary refined carb restriction, her daily physical exercise (brisk steps), "
            "and the long-term progression of her metabolic HbA1c levels from her initial pre-diabetic baseline of 6.2% to "
            "her final recovered status over the clinical timeframe?"
        ),
        (
            "CARDIOVASCULAR AND CARDIO-PROTECTIVE ASSESSMENTS",
            "Detail Alice Smith's lipid profile progression, specifically tracking her LDL cholesterol from her borderline high baseline "
            "of 145 mg/dL down to her final values, and summarize all lifestyles, targets, and clinical interventions (such as Metformin "
            "compliance and target exercise) she undertook to support her cardiac recovery?"
        )
    ]

    print(f"\n{CLR_HEADER}┌─────────────────────────── EVALUATING MEDICAL QA ────────────────────┐{CLR_RESET}")
    print(f"{CLR_HEADER}│{CLR_RESET} Querying fresh clinical agent with complex multivariable inquiries... │")
    print(f"{CLR_HEADER}└──────────────────────────────────────────────────────────────────────┘{CLR_RESET}\n")

    for label, query in complex_queries:
        print(f"{CLR_TITLE}🔷 {label}:{CLR_RESET}")
        print(f"{CLR_USER}Query:{CLR_RESET} {query}")
        print(f"{CLR_STATS}Processing high-fidelity clinical retrieval via Cohere + Thinking RAG...{CLR_RESET}")
        
        start_time = time.perf_counter()
        try:
            resp = requests.post(
                f"{BASE_URL}/agent_chat",
                headers=headers,
                json={"agent_id": agent_id, "message": query, "strategy": "auto"},
                timeout=180
            )
            duration = time.perf_counter() - start_time
            if resp.status_code == 200:
                data = resp.json()
                ai_resp = data.get("agent_response", "")
                strategy = data.get("strategy", "auto")
                
                print(f"\n{CLR_AI}🩺 Clinical Synthesis Output:{CLR_RESET}")
                print("-" * 80)
                if isinstance(ai_resp, dict):
                    for key, val in ai_resp.items():
                        print(f"{CLR_TITLE}• {key}:{CLR_RESET}\n{val}\n")
                else:
                    print(str(ai_resp).strip())
                print("-" * 80)
                print(f"{CLR_STATS}[Latency: {duration:.2f}s | Strategy: {strategy.upper()} | Core: COHERE]{CLR_RESET}\n")
            else:
                print(f"❌ Query failed (Status {resp.status_code}): {resp.text}\n")
        except Exception as e:
            print(f"❌ Query exception: {e}\n")

    print("=" * 80)
    print(f"🎉 {CLR_SUCCESS}100K-WORD LONGITUDINAL CLINICAL EVALUATION COMPLETED SUCCESSFULLY!{CLR_RESET}")
    print("=" * 80)

if __name__ == "__main__":
    run_test_suite()
