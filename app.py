import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import streamlit as st
from agent.config import LLMConfig, SearchConfig
from agent.llm import QuotaExhausted, StageError
from agent.pipeline import run
from agent.schemas import ClaimVerdict, FinalBrief

st.set_page_config(
    page_title="Research Brief Agent",
    page_icon="🔍",
    layout="wide"
)

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"

PRESETS = {
    "Google Gemini (Free Tier)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash"
    },
    "Groq (Free Tier)": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile"
    },
    "OpenRouter (Free / Low Cost)": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free"
    },
    "Custom Endpoint": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    }
}

def render_claim_badge(verdict: str) -> str:
    if verdict == "SUPPORTED":
        return "🟢 **Supported**"
    elif verdict == "PARTIAL":
        return "🟡 **Partial**"
    return "🔴 **Unsupported**"

def render_brief_ui(brief: FinalBrief):
    st.subheader(brief.title)
    st.caption(
        f"📅 Generated: {brief.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"🤖 Model: `{brief.model_used}` | "
        f"⏱️ Runtime: {brief.elapsed_s:.1f}s | "
        f"📞 LLM Calls: {brief.llm_calls}"
    )

    # Metric Strip
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Supported Claims", f"{brief.supported}/{brief.total_claims}")
    m2.metric("Partially Supported", f"{brief.partial}")
    m3.metric("Unsupported Claims", f"{brief.unsupported}")
    m4.metric("Dropped (Uncited/Invalid)", f"{brief.dropped_uncited_claims + brief.dropped_invalid_quotes}")

    st.markdown("---")

    # Render Summary Section
    st.markdown("### 📋 Executive Summary")
    summary_claims = [c for c in brief.claims if c.section == "summary"]
    if summary_claims:
        for c in summary_claims:
            _render_single_claim(c, brief)
    else:
        st.write("No summary claims generated.")

    # Render Key Findings Section
    st.markdown("### 🔍 Key Findings")
    key_claims = [c for c in brief.claims if c.section == "key_findings"]
    if key_claims:
        for c in key_claims:
            _render_single_claim(c, brief)
    else:
        st.write("No key findings generated.")

    # Render Gaps & Conflicts
    if brief.gaps_and_conflicts:
        st.markdown("### ⚠️ Gaps & Evidence Conflicts")
        for gap in brief.gaps_and_conflicts:
            st.warning(gap, icon="⚠️")

    # Render Sources
    st.markdown("### 📚 Cited Sources")
    if brief.sources:
        for s in brief.sources:
            date_info = f" • *Published: {s.published_date}*" if s.published_date else ""
            st.markdown(f"**[{s.id}]** [{s.title}]({s.url}) (`{s.domain}`){date_info}")
    else:
        st.write("No sources attached.")

    # Download Markdown Button
    st.markdown("---")
    md_content = brief.to_markdown()
    st.download_button(
        label="📥 Download Brief as Markdown",
        data=md_content,
        file_name=f"research_brief_{brief.title.lower().replace(' ', '_')[:30]}.md",
        mime="text/markdown"
    )

def _render_single_claim(claim: ClaimVerdict, brief: FinalBrief):
    cites = "".join(f"[{cid}]" for cid in claim.citation_ids)
    badge = render_claim_badge(claim.verdict)
    
    col_text, col_badge = st.columns([4, 1])
    with col_text:
        st.markdown(f"• {claim.text} **{cites}**")
    with col_badge:
        st.markdown(badge)

    with st.expander(f"Inspect Verification Evidence for Claim #{claim.claim_id}"):
        st.markdown(f"**Verifier Rationale**: {claim.reason}")
        if claim.supporting_quotes:
            st.markdown("**Cited Supporting Quotes from Source:**")
            for q in claim.supporting_quotes:
                st.info(f"\"{q}\"", icon="💬")
        
        # Link to cited sources
        cited_sources = [s for s in brief.sources if s.id in claim.citation_ids]
        if cited_sources:
            st.markdown("**Cited Sources:**")
            for cs in cited_sources:
                st.markdown(f"- [[{cs.id}]] [{cs.title}]({cs.url})")

def main():
    st.title("🔍 Research Brief Agent")
    st.markdown(
        "**Reliable, traceable AI intelligence for analysts.** Every claim is bound to explicit citations "
        "and independently validated with per-claim verdicts (`Supported`, `Partial`, `Unsupported`)."
    )

    # Sidebar: Mode Selection and BYOK
    with st.sidebar:
        st.header("⚙️ Configuration")
        mode = st.radio(
            "Select Operating Mode:",
            ["Showcase Briefs (Zero API Quota)", "Run Live Query (BYOK)"],
            index=0
        )

        if mode == "Showcase Briefs (Zero API Quota)":
            st.info("Explore pre-saved briefs without consuming API keys or burning live quota.")
            example_choice = st.selectbox(
                "Choose Showcase Brief:",
                [
                    "1. Mistral AI (Model Portfolio & Pricing)",
                    "2. Casgevy (CRISPR Approvals & Pricing)",
                    "3. Stripe (Crypto & Stablecoin Payments)"
                ]
            )
        else:
            st.markdown("### 🔑 Bring Your Own Keys")
            preset_name = st.selectbox("LLM Provider Preset:", list(PRESETS.keys()))
            selected_preset = PRESETS[preset_name]

            base_url = st.text_input("LLM Base URL:", value=selected_preset["base_url"])
            model_name = st.text_input("LLM Model Name:", value=selected_preset["model"])
            llm_key = st.text_input("LLM API Key:", type="password", placeholder="Enter your LLM API Key")
            tavily_key = st.text_input("Tavily API Key:", type="password", placeholder="Enter your Tavily Key")

            st.caption(
                "🔒 **Multi-Tenant Privacy**: Credentials are kept strictly in this browser session "
                "(`st.session_state`) and are NEVER stored in server environment variables or disk logs."
            )

    # Main Area
    if mode == "Showcase Briefs (Zero API Quota)":
        if "1." in example_choice:
            file_path = EXAMPLES_DIR / "example_1.json"
        elif "2." in example_choice:
            file_path = EXAMPLES_DIR / "example_2.json"
        else:
            file_path = EXAMPLES_DIR / "example_3.json"

        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                brief_data = json.load(f)
            brief_data["generated_at"] = datetime.fromisoformat(brief_data["generated_at"].replace("Z", "+00:00"))
            brief = FinalBrief(**brief_data)
            render_brief_ui(brief)
        else:
            st.error("Showcase example file not found.")

    else:
        # Live Run Mode
        question = st.text_input(
            "Research Question:",
            placeholder="e.g. What is the current pricing model and market footprint of Perplexity AI?"
        )
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            run_btn = st.button("🚀 Generate Verified Brief", type="primary", use_container_width=True)

        if run_btn:
            if not question.strip():
                st.warning("Please enter a research question.")
                return
            if not llm_key.strip():
                st.warning("Please provide your LLM API key in the sidebar.")
                return
            if not tavily_key.strip():
                st.warning("Please provide your Tavily API key in the sidebar.")
                return

            llm_cfg = LLMConfig(
                base_url=base_url.strip(),
                api_key=llm_key.strip(),
                model=model_name.strip(),
                min_interval_s=2.0
            )
            search_cfg = SearchConfig(api_key=tavily_key.strip())

            status_box = st.status("Executing research pipeline...", expanded=True)
            def on_progress(message: str):
                status_box.write(f"• {message}")

            try:
                brief = run(
                    question=question.strip(),
                    llm_cfg=llm_cfg,
                    search_cfg=search_cfg,
                    on_progress=on_progress,
                    use_cache=True
                )
                status_box.update(label="✅ Brief generation & verification complete!", state="complete", expanded=False)
                render_brief_ui(brief)

            except QuotaExhausted as qe:
                status_box.update(label="⚠️ Quota Exhausted", state="error", expanded=True)
                st.error(
                    "**Daily API Quota Limit Exceeded**: The selected provider's free-tier daily quota has been depleted. "
                    "Please wait for quota reset or switch to another provider in the sidebar."
                )
            except StageError as se:
                status_box.update(label="⚠️ Pipeline Warning", state="error", expanded=True)
                st.warning(f"**Research Pipeline Notice**: {se}")
            except Exception as e:
                status_box.update(label="❌ Execution Error", state="error", expanded=True)
                st.error(f"An unexpected error occurred during execution: {e}")

if __name__ == "__main__":
    main()
