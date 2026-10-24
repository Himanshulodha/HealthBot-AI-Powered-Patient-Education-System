from pathlib import Path

APP_SOURCE = r'''import json
import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(".env")

st.set_page_config(
    page_title="HealthBridge | Patient Education",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1150px;}
    .hero {padding: 1.7rem 1.8rem; border-radius: 18px; background: linear-gradient(120deg,#102a43,#176b87); color: white; margin-bottom: 1.2rem;}
    .hero h1 {font-size: 2.35rem; margin: 0 0 .45rem 0; color: white;}
    .hero p {font-size: 1.02rem; margin: 0; color: #e6f4f7;}
    .notice {padding: .9rem 1rem; border-left: 4px solid #e0a526; background: rgba(224,165,38,.10); border-radius: 8px; margin: .8rem 0 1.2rem;}
    .source-card {padding: .9rem 1rem; border: 1px solid rgba(128,128,128,.35); border-radius: 10px; margin: .5rem 0;}
    .metric-label {font-size:.8rem; opacity:.75; text-transform:uppercase; letter-spacing:.08em;}
</style>
<div class="hero">
  <h1>🩺 HealthBridge</h1>
  <p>Evidence-grounded health education with source-backed summaries and a learning check.</p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="notice"><strong>Educational use only.</strong> HealthBridge is not a medical professional and does not provide diagnosis, treatment, or emergency advice. For personal medical concerns, consult a qualified clinician. If this may be an emergency, contact local emergency services.</div>',
    unsafe_allow_html=True,
)

def init_state():
    defaults = {
        "topic": "", "sources": [], "summary": "", "question": "",
        "expected_points": [], "answer": "", "grade_result": None,
        "stage": "topic", "error": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

def get_clients():
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not google_key or not tavily_key:
        raise RuntimeError("Missing GOOGLE_API_KEY or TAVILY_API_KEY. Add both to your .env file.")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key, temperature=0.2, max_output_tokens=1400)
    search = TavilySearchResults(max_results=5, search_depth="advanced", include_answer=False, include_raw_content=True, tavily_api_key=tavily_key)
    return llm, search

def parse_json(content: Any) -> dict:
    if isinstance(content, list):
        content = "".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content)
    text = str(content).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text.strip())

def search_sources(topic: str, search_tool) -> list[dict]:
    results = search_tool.invoke({
        "query": (
            f"Reliable patient education about {topic}; prioritize government health agencies, "
            "recognized medical organizations, major hospitals, and peer-reviewed sources."
        )
    })
    if isinstance(results, dict):
        results = results.get("results", [results])
    usable = [
        x for x in results if isinstance(x, dict) and x.get("url")
        and (x.get("content") or x.get("raw_content"))
    ]
    if not usable:
        raise RuntimeError("Search returned no usable source content. Try a more specific topic.")
    return usable[:5]

def source_context(sources: list[dict]) -> str:
    blocks = []
    for i, source in enumerate(sources, 1):
        content = source.get("raw_content") or source.get("content") or ""
        blocks.append(
            f"[Source {i}]\nTitle: {source.get('title', 'Medical source')}\n"
            f"URL: {source.get('url', '')}\nEvidence: {content[:4500]}"
        )
    return "\n\n".join(blocks)

def create_summary(topic: str, sources: list[dict], llm) -> str:
    prompt = f"""You are a careful patient educator. Use ONLY the numbered source evidence below.
Write exactly THREE short, patient-friendly paragraphs about: {topic}.
Cover (1) what it is and causes/effects, (2) symptoms or warning signs supported by sources,
and (3) prevention/management/treatment information supported by sources, encouraging professional care.
Each paragraph should be 35-65 words and contain at least one citation like [Source 1].
Do not diagnose, prescribe, invent facts, or imply that sources agree if they do not.
Return valid JSON only: {{"paragraphs":["...", "...", "..."]}}

SOURCE EVIDENCE:
{source_context(sources)}
"""
    data = parse_json(llm.invoke(prompt).content)
    paragraphs = data.get("paragraphs", [])
    if not isinstance(paragraphs, list) or len(paragraphs) != 3:
        raise RuntimeError("The model did not return exactly three paragraphs.")
    for p in paragraphs:
        if not isinstance(p, str) or "[Source " not in p:
            raise RuntimeError("A summary paragraph was missing a source citation. Please retry.")
    return "\n\n".join(p.strip() for p in paragraphs)

def create_question(summary: str, llm):
    prompt = f"""Using ONLY the summary below, create one short-answer comprehension question
and 2-4 expected answer points. Return valid JSON only:
{{"question":"...", "expected_points":["...", "..."]}}
SUMMARY:
{summary}
"""
    data = parse_json(llm.invoke(prompt).content)
    question = str(data.get("question", "")).strip()
    points = data.get("expected_points", [])
    if not question or not isinstance(points, list) or not points:
        raise RuntimeError("Could not create a comprehension question. Please retry.")
    return question, [str(x) for x in points]

def grade_answer(summary: str, question: str, points: list[str], answer: str, llm):
    prompt = f"""Assess a learner's answer ONLY against the summary, question, and expected points.
Grades: A correct/complete; B mostly correct; C partially correct; D minimally relevant; F incorrect/unrelated.
Do not use outside medical knowledge. Explain briefly and quote a relevant sentence from the summary
with its existing [Source N] citation. Never invent citations. Return valid JSON only:
{{"grade":"A", "explanation":"...", "citation":"... [Source 1]"}}
SUMMARY: {summary}
QUESTION: {question}
EXPECTED POINTS: {json.dumps(points)}
LEARNER ANSWER: {answer}
"""
    data = parse_json(llm.invoke(prompt).content)
    grade = str(data.get("grade", "")).upper().strip()
    explanation = str(data.get("explanation", "")).strip()
    citation = str(data.get("citation", "")).strip()
    if grade not in {"A", "B", "C", "D", "F"} or not explanation or "[Source " not in citation:
        raise RuntimeError("The model returned incomplete feedback. Please submit again.")
    return {"grade": grade, "explanation": explanation, "citation": citation}

with st.sidebar:
    st.markdown("## About this project")
    st.write("A patient-education prototype using Gemini, Tavily Search, and Streamlit.")
    st.markdown("**Pipeline**")
    st.caption("Topic → evidence retrieval → cited summary → comprehension check → feedback")
    st.divider()
    st.caption("Built for educational demonstration. Search results and generated summaries can be incomplete.")

left, right = st.columns([1.55, 1], gap="large")
with left:
    st.subheader("Explore a health topic")
    with st.form("topic_form", clear_on_submit=False):
        topic_input = st.text_input("Health topic", placeholder="e.g., hypertension, asthma, type 2 diabetes", value=st.session_state.topic)
        submitted = st.form_submit_button("Research topic", type="primary", use_container_width=True)
    if submitted:
        topic_input = topic_input.strip()
        if len(topic_input) < 2:
            st.warning("Please enter a health topic.")
        else:
            try:
                with st.spinner("Searching medical sources and preparing a cited summary…"):
                    llm, search_tool = get_clients()
                    sources = search_sources(topic_input, search_tool)
                    summary = create_summary(topic_input, sources, llm)
                    question, points = create_question(summary, llm)
                st.session_state.update({
                    "topic": topic_input, "sources": sources, "summary": summary,
                    "question": question, "expected_points": points, "answer": "",
                    "grade_result": None, "stage": "quiz", "error": None
                })
                st.rerun()
            except Exception as exc:
                st.error(f"Could not complete the research workflow: {exc}")
                st.info("Check your API keys, available API quota, network connection, and package versions.")

with right:
    st.subheader("Learning journey")
    steps = [("1", "Choose a topic"), ("2", "Read the evidence-based summary"), ("3", "Answer a question"), ("4", "Review feedback")]
    for number, label in steps:
        st.markdown(f"**{number}.** {label}")
    if st.session_state.topic:
        st.success(f"Current topic: {st.session_state.topic}")

if st.session_state.summary:
    st.divider()
    st.markdown(f"## Patient-friendly overview: {st.session_state.topic.title()}")
    st.caption("The summary is generated from retrieved source content. Citations refer to the sources listed below.")
    for paragraph in st.session_state.summary.split("\n\n"):
        st.write(paragraph)

    with st.expander(f"View retrieved sources ({len(st.session_state.sources)})", expanded=True):
        for i, source in enumerate(st.session_state.sources, 1):
            title = source.get("title") or f"Source {i}"
            url = source.get("url", "")
            snippet = source.get("content") or ""
            st.markdown(f"**[Source {i}] {title}**")
            if url:
                st.markdown(f"[Open source]({url})")
            if snippet:
                st.caption(snippet[:700])
            st.divider()

    st.divider()
    st.markdown("## Knowledge check")
    st.write(st.session_state.question)
    with st.form("answer_form"):
        answer = st.text_area("Your answer", placeholder="Explain in your own words…", height=120, value=st.session_state.answer)
        checked = st.form_submit_button("Evaluate my answer", type="primary")
    if checked:
        if not answer.strip():
            st.warning("Please write an answer before submitting.")
        else:
            try:
                with st.spinner("Evaluating your answer against the summary…"):
                    llm, _ = get_clients()
                    result = grade_answer(st.session_state.summary, st.session_state.question, st.session_state.expected_points, answer.strip(), llm)
                st.session_state.answer = answer.strip()
                st.session_state.grade_result = result
                st.rerun()
            except Exception as exc:
                st.error(f"Could not evaluate the answer: {exc}")

    if st.session_state.grade_result:
        result = st.session_state.grade_result
        st.markdown("### Your feedback")
        st.metric("Learning grade", result["grade"])
        st.write(result["explanation"])
        st.info(f"**Evidence from the summary:** {result['citation']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Explore another topic", use_container_width=True):
            for key in ["topic", "sources", "summary", "question", "expected_points", "answer", "grade_result", "error"]:
                st.session_state[key] = [] if key in {"sources", "expected_points"} else (None if key == "grade_result" else "")
            st.session_state.stage = "topic"
            st.rerun()
    with col2:
        st.download_button(
            "Download learning summary",
            data=f"HealthBridge — Educational summary: {st.session_state.topic}\n\n{st.session_state.summary}\n\nSources:\n" + "\n".join(f"[Source {i}] {x.get('title','Source')} — {x.get('url','')}" for i, x in enumerate(st.session_state.sources, 1)),
            file_name="healthbridge_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )

st.divider()
st.caption("HealthBridge is an educational prototype, not a medical device or a substitute for professional medical advice.")
'''
Path('app.py').write_text(APP_SOURCE, encoding='utf-8')
print('Created app.py')