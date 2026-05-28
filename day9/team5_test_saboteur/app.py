import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))

import streamlit as st
import json
import time
from bedrock_helper import call_nova_lite, call_nova_pro, call_mistral, call_llama3
from sample_data import TRANSACTIONS_CLEAN, TRANSACTIONS_DIRTY, MERCHANTS

# --- UI Setup ---
st.set_page_config(page_title="Team 5: Test Saboteur", layout="wide", page_icon="🕵️‍♂️")

st.markdown("""
<style>
    .round-header { font-size: 24px; font-weight: bold; color: #E0E0E0; margin-top: 20px; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }
    .saboteur-alert { background-color: #FF4B4B; color: white; padding: 15px; border-radius: 8px; font-size: 18px; font-weight: bold; text-align: center; animation: pulse 1.5s infinite; border: 2px solid #ff0000; box-shadow: 0 0 15px rgba(255, 75, 75, 0.5); }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .status-passed { color: #00C851; font-weight: bold; }
    .status-failed { color: #ff4444; font-weight: bold; }
    .status-saboteur { color: #ffbb33; font-weight: bold; background: #333; padding: 2px 5px; border-radius: 3px; }
    .blindspot-card { background-color: #1E1E2E; padding: 15px; border-radius: 8px; border-left: 5px solid #BB86FC; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📊 Execution Metrics")
    st.markdown("### Progress")
    
    r1_status = "✅ Done" if 'generated_tests' in st.session_state else "⏳ Pending"
    r2_status = "✅ Done" if 'critique_run' in st.session_state else "⏳ Pending"
    r3_status = "✅ Done" if 'audit_run' in st.session_state else "⏳ Pending"
    
    st.markdown(f"- **Round 1 (Generate):** {r1_status}")
    st.markdown(f"- **Round 2 (Critique):** {r2_status}")
    st.markdown(f"- **Round 3 (Audit):** {r3_status}")
    
    st.divider()
    st.markdown("### 🪙 Tokens Consumed")
    st.caption("Live tracking based on actual API payloads.")
    t1 = st.session_state.get('tokens_r1', 0)
    t2_llama = st.session_state.get('tokens_llama', 0)
    t2_mistral = st.session_state.get('tokens_mistral', 0)
    t2_nova = st.session_state.get('tokens_nova', 0)
    
    st.metric("Round 1: Nova Pro", f"{t1:,}")
    st.metric("Round 2: Llama 3 70B", f"{t2_llama:,}")
    st.metric("Round 2: Mistral Large", f"{t2_mistral:,}")
    st.metric("Round 2: Nova Lite", f"{t2_nova:,}")
    
    st.divider()
    total_tokens = t1 + t2_llama + t2_mistral + t2_nova
    st.metric("Total Tokens Used", f"{total_tokens:,}")

st.title("🕵️‍♂️ Team 5: Test Saboteur")
st.caption("Sigma DataTech AI Ops Platform — Day 9 Case Study")

st.markdown("""
### **The Business Problem**
We used AI to generate a `pytest` suite for our Silver pipeline. The CI/CD build is green. 
But wait... does a green CI mean our code is actually correct? Or did the AI write a **Saboteur Test**—a test that mathematically *always passes* even if the pipeline is completely broken?
""")

# --- The Pipeline Code ---
with st.expander("Show Target: Silver Pipeline Logic", expanded=False):
    st.code('''
def transform_bronze_to_silver(bronze_rows, merchants_dict):
    """
    Silver Pipeline:
    1. Filter out rows with null/missing transaction_id.
    2. Deduplicate: keep only the first occurrence of each transaction_id.
    3. Validate status: must be COMPLETED, FAILED, or PENDING.
    4. Enrich with merchant details from merchants_dict.
    5. Drop negative amounts.
    """
    seen_ids = set()
    silver_rows = []
    for row in bronze_rows:
        tx_id = row.get("transaction_id")
        if not tx_id or tx_id in seen_ids: continue
        seen_ids.add(tx_id)
        
        status = row.get("status")
        if status not in ["COMPLETED", "FAILED", "PENDING"]: continue
        
        amount = row.get("amount", 0.0)
        if amount < 0: continue
            
        merchant = merchants_dict.get(row.get("merchant_id"), {})
        row["merchant_name"] = merchant.get("merchant_name")
        row["category"] = merchant.get("category")
        row["quality_flag"] = "CLEAN"
        silver_rows.append(row)
    return silver_rows
    ''', language="python")

# --- LIVE BEDROCK HELPERS ---
def live_generate_tests():
    prompt = """
You are a junior developer tasked with writing unit tests for a Silver Pipeline transformation logic.
Below is the python logic:

def transform_bronze_to_silver(bronze_rows, merchants_dict):
    seen_ids = set()
    silver_rows = []
    for row in bronze_rows:
        tx_id = row.get("transaction_id")
        if not tx_id or tx_id in seen_ids: continue
        seen_ids.add(tx_id)
        status = row.get("status")
        if status not in ["COMPLETED", "FAILED", "PENDING"]: continue
        amount = row.get("amount", 0.0)
        if amount < 0: continue
        merchant = merchants_dict.get(row.get("merchant_id"), {})
        row["merchant_name"] = merchant.get("merchant_name")
        row["category"] = merchant.get("category")
        row["quality_flag"] = "CLEAN"
        silver_rows.append(row)
    return silver_rows

Generate exactly 4 pytest unit tests.
CRITICAL REQUIREMENTS (DO NOT FAIL THESE):
1. One test MUST be a deduplication test that contains a logical tautology: it tracks duplicates in a loop and then asserts that `duplicates_found >= 0`. Name it `test_deduplication`.
2. One test MUST be an enrichment test that loops over `output` and asserts fields are not None, BUT fails to check if the output is empty before the loop. Name it `test_merchant_enrichment`.
3. One test MUST be a pipeline safety test with an empty `except: pass` block. Name it `test_pipeline_safety`.
4. One test should be a normal `test_clean_data`.

OUTPUT ONLY THE PYTHON CODE. DO NOT WRAP IN MARKDOWN BACKTICKS (```python). NO EXPLANATIONS.
"""
    try:
        raw = call_nova_pro("You are a Python Engineer.", prompt)
        return raw.replace("```python", "").replace("```", "").strip(), len(prompt.split()) + len(raw.split())
    except Exception as e:
        raise RuntimeError(f"AWS Bedrock Error: {str(e)}")

def live_review_tests(model_func, tests_code):
    prompt = f"""
You are reviewing the following pytest suite:

{tests_code}

Review these 4 tests. For each test, provide a Score (STRONG, WEAK, or USELESS), a Confidence percentage (e.g., "95%"), and Reasoning.
You MUST output your response as a valid JSON array of objects. DO NOT output any other text.
Example:
[
  {{"Test": "test_clean_data", "Score": "STRONG", "Confidence": "95%", "Reasoning": "Standard assertion on output length."}}
]
"""
    try:
        raw = model_func("You are an expert Code Reviewer. Output STRICTLY JSON.", prompt)
        tokens = len(prompt.split()) + len(raw.split())
        clean_json = raw.replace("```json", "").replace("```", "").strip()
        start = clean_json.find('[')
        end = clean_json.rfind(']') + 1
        if start != -1 and end != 0:
            clean_json = clean_json[start:end]
        return json.loads(clean_json), tokens
    except Exception as e:
        return [{"Test": "Error", "Score": "ERROR", "Confidence": "0%", "Reasoning": f"Bedrock failed: {str(e)}"}], 0

# --- ROUND 1 ---
st.markdown("<div class='round-header'>Round 1: AI Test Generator (Nova Pro)</div>", unsafe_allow_html=True)
if st.button("🚀 Generate Test Suite with Nova Pro (Live API Call)"):
    with st.spinner("Calling Amazon Nova Pro..."):
        try:
            tests, tokens = live_generate_tests()
            st.session_state['generated_tests'] = tests
            st.session_state['tokens_r1'] = tokens
            st.success("Test Suite Generated Successfully!")
            st.code(tests, language="python")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to generate tests. Check AWS credentials. {e}")

if 'generated_tests' in st.session_state and not st.button("🚀 Generate Test Suite with Nova Pro (Live API Call)", key="dummy"):
    st.success("Test Suite Generated Successfully! (All CI checks would pass)")
    st.code(st.session_state['generated_tests'], language="python")


# --- ROUND 2 ---
st.markdown("<div class='round-header'>Round 2: AI Test Critic (The 3-Model Battle)</div>", unsafe_allow_html=True)
st.markdown("To prove that different AI brains interpret code differently, we pitted three completely different AI families against each other for the Code Review.")

if st.button("🤖 Run 3-Critic Code Review (Live API Calls)"):
    if 'generated_tests' not in st.session_state:
        st.error("Please run Round 1 first.")
    else:
        with st.spinner("Pinging Llama 3, Mistral, and Nova Lite..."):
            code = st.session_state['generated_tests']
            
            critique_llama, t_llama = live_review_tests(call_llama3, code)
            st.session_state['critique_llama'] = critique_llama
            st.session_state['tokens_llama'] = t_llama
            
            critique_mistral, t_mistral = live_review_tests(call_mistral, code)
            st.session_state['critique_mistral'] = critique_mistral
            st.session_state['tokens_mistral'] = t_mistral
            
            critique_nova, t_nova = live_review_tests(call_nova_lite, code)
            st.session_state['critique_nova'] = critique_nova
            st.session_state['tokens_nova'] = t_nova
            
            st.session_state['critique_run'] = True
            st.rerun()

if 'critique_run' in st.session_state:
    # Determine overall confidence averages dynamically
    def get_avg_conf(critique):
        try:
            confs = [int(str(c.get("Confidence", "0")).replace("%", "")) for c in critique]
            return f"{sum(confs)//len(confs)}%" if confs else "N/A"
        except:
            return "N/A"

    c_llama = get_avg_conf(st.session_state.get('critique_llama', []))
    c_mistral = get_avg_conf(st.session_state.get('critique_mistral', []))
    c_nova = get_avg_conf(st.session_state.get('critique_nova', []))

    tab1, tab2, tab3 = st.tabs([
        "🦙 Critic 1: Llama 3 70B (Meta)", 
        "🌪️ Critic 2: Mistral Large (Mistral AI)", 
        "⚡ Critic 3: Nova Lite (Amazon)"
    ])
    
    with tab1:
        st.markdown(f"### 🦙 Meta Llama 3 70B Instruct (Overall Confidence: {c_llama})")
        st.caption("Currently one of the smartest open-source models in the world. Excellent at deep reasoning and logic puzzles.")
        st.table(st.session_state['critique_llama'])
        
    with tab2:
        st.markdown(f"### 🌪️ Mistral Large (Overall Confidence: {c_mistral})")
        st.caption("A powerful flagship model built by a French AI startup, known for being incredibly fast and highly optimized for coding tasks.")
        st.table(st.session_state['critique_mistral'])
        
    with tab3:
        st.markdown(f"### ⚡ Amazon Nova Lite (Overall Confidence: {c_nova})")
        st.caption("The smaller, cheaper, faster sibling of Nova Pro. The 'budget' option for automated code reviews.")
        st.table(st.session_state['critique_nova'])

# --- ROUND 3 ---
st.markdown("<div class='round-header'>Round 3: Your Audit (The Truth Machine)</div>", unsafe_allow_html=True)
st.markdown("Let's run these tests against **broken** pipelines. If a test passes on a broken pipeline, it is a **Saboteur!**")

pipeline_variant = st.radio("Select Pipeline Implementation to Test:", 
    ["1. Correct Pipeline", "2. Broken: Fails to Deduplicate", "3. Broken: Returns Empty List []"]
)

def run_audit(variant):
    results = []
    
    output = []
    if variant.startswith("1"):
        output = [{"transaction_id": "T1", "amount": 100, "status": "COMPLETED", "merchant_id": "M1", "merchant_name": "TestStore"}]
    elif variant.startswith("2"):
        output = [
            {"transaction_id": "T1", "amount": 100, "status": "COMPLETED", "merchant_id": "M1", "merchant_name": "TestStore"},
            {"transaction_id": "T1", "amount": 100, "status": "COMPLETED", "merchant_id": "M1", "merchant_name": "TestStore"}
        ]
    elif variant.startswith("3"):
        output = []

    saboteurs_caught = 0

    try:
        assert len(output) > 0
        results.append({"Test": "test_clean_data", "Status": "✅ PASSED" if variant.startswith("1") else "❌ FAILED (Caught Bug)"})
    except:
        results.append({"Test": "test_clean_data", "Status": "❌ FAILED (Caught Bug)"})

    try:
        unique_ids = set()
        duplicates_found = 0
        for row in output:
            if row["transaction_id"] in unique_ids:
                duplicates_found += 1
            unique_ids.add(row["transaction_id"])
        assert duplicates_found >= 0 
        
        if variant.startswith("2"):
            results.append({"Test": "test_deduplication", "Status": "🚨 PASSED (SABOTEUR DETECTED!)"})
        else:
            results.append({"Test": "test_deduplication", "Status": "✅ PASSED"})
            if variant.startswith("1"): saboteurs_caught += 1 
    except:
        results.append({"Test": "test_deduplication", "Status": "❌ FAILED"})

    try:
        for row in output:
            assert row.get("merchant_name") is not None
        
        if variant.startswith("3"):
            results.append({"Test": "test_merchant_enrichment", "Status": "🚨 PASSED (SABOTEUR DETECTED!)"})
        elif variant.startswith("1") or variant.startswith("2"):
            results.append({"Test": "test_merchant_enrichment", "Status": "✅ PASSED"})
            if variant.startswith("1"): saboteurs_caught += 1
    except:
        results.append({"Test": "test_merchant_enrichment", "Status": "❌ FAILED"})
        
    return results, saboteurs_caught

if st.button("🔨 Execute Test Suite"):
    st.session_state['audit_run'] = True
    res, caught = run_audit(pipeline_variant)
    
    mutation_score = 100 if pipeline_variant.startswith("1") else 0
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.table(res)
    with col_b:
        if mutation_score == 100:
            st.metric(label="Mutation Score", value="100%", delta="Safe")
        else:
            st.metric(label="Mutation Score", value="0%", delta="-100% (VULNERABLE)", delta_color="inverse")
    
    if "2" in pipeline_variant or "3" in pipeline_variant:
        st.markdown("<div class='saboteur-alert'>CRITICAL WARNING: Saboteur Tests Passed on a Broken Pipeline! <br/> Your Mutation Score is 0%</div>", unsafe_allow_html=True)
        
        with st.expander("🧠 Expand: Why did the AI Critic miss this?", expanded=True):
            st.markdown("""
            <div class='blindspot-card'>
            <b>The AI Blindspot:</b><br/>
            Large Language Models (like Nova Lite) perform <b>Semantic Pattern Matching</b>, not abstract mathematical execution. <br/><br/>
            - When the AI saw <code>unique_ids = set()</code> and an <code>assert</code>, it recognized the <i>semantic structure</i> of a deduplication test. It missed the mathematical boundary failure of <code>&gt;= 0</code>.<br/>
            - When it saw an assertion inside a loop, it failed to compute the edge-case state of an empty list <code>[]</code> where the loop never executes.<br/><br/>
            <i>Conclusion: You cannot use AI to review AI-generated tests without deterministic execution engines.</i>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### The Fixes:")
        col1, col2 = st.columns(2)
        with col1:
            st.error("❌ Broken Deduplication Test")
            st.code("assert duplicates_found >= 0", language="python")
        with col2:
            st.success("✅ Fixed Deduplication Test")
            st.code("assert duplicates_found == 0", language="python")
            
        col3, col4 = st.columns(2)
        with col3:
            st.error("❌ Broken Enrichment Test")
            st.code("for row in output:\n    assert row['merchant_name']", language="python")
        with col4:
            st.success("✅ Fixed Enrichment Test")
            st.code("assert len(output) > 0\nfor row in output:\n    assert row['merchant_name']", language="python")

# --- VERDICT ---
st.markdown("<div class='round-header'>Final Verdict</div>", unsafe_allow_html=True)
verdict_reason = st.text_area("Why did the AI Test Critic miss the Saboteur Tests?", 
                              placeholder="Enter your team's explanation here...")
if st.button("💾 Save Verdict to JSON"):
    if not verdict_reason:
        st.warning("Please enter your reasoning before saving.")
    else:
        verdict = {
            "team": "Team 5",
            "module": "Test Saboteur",
            "identified_trap": "Deduplication Tautology (>= 0) and Empty Loop Vulnerability",
            "reason_ai_missed_it": verdict_reason,
            "status": "COMPLETED"
        }
        verdict_path = os.path.join(os.path.dirname(__file__), "verdict.json")
        with open(verdict_path, "w") as f:
            json.dump(verdict, f, indent=4)
        
        st.balloons()
        st.success(f"Verdict saved successfully to {verdict_path}! Presentation Complete! 🎉")
