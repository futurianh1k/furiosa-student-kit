"""Streamlit UI for chatting with a local Furiosa LLM artifact.

Run:
  streamlit run streamlit_artifact_chat.py
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from time import perf_counter
import traceback

import streamlit as st
from furiosa_llm import LLM, SamplingParams


DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[2] / "qwen2.5-0.5b" / "qwen2.5-0.5b-artifact"
)


def page_setup() -> None:
    st.set_page_config(
        page_title="Furiosa Artifact Chat",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 1180px;
            padding-top: 1.5rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.45rem;
        }
        .small-muted {
            color: #6b7280;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def load_llm(artifact_path: str) -> LLM:
    return LLM(artifact_path)


def reset_model() -> None:
    load_llm.clear()
    st.session_state.pop("loaded_artifact", None)


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_logs", "")
    st.session_state.setdefault("last_error", "")
    st.session_state.setdefault("last_latency", None)


def render_sidebar() -> tuple[str, SamplingParams, int]:
    st.sidebar.header("Model")
    artifact_path = st.sidebar.text_input("Artifact path", value=str(DEFAULT_ARTIFACT))

    exists = Path(artifact_path).exists()
    if exists:
        st.sidebar.success("Artifact directory found")
    else:
        st.sidebar.error("Artifact directory not found")

    st.sidebar.divider()
    st.sidebar.header("Sampling")
    temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.5, 0.05)
    top_p = st.sidebar.slider("Top-p", 0.05, 1.0, 0.3, 0.05)
    top_k = st.sidebar.number_input("Top-k", min_value=1, max_value=1000, value=100)
    min_tokens = st.sidebar.number_input("Min tokens", min_value=0, max_value=512, value=10)
    max_tokens = st.sidebar.number_input("Max tokens", min_value=1, max_value=2048, value=256)

    st.sidebar.divider()
    col_a, col_b = st.sidebar.columns(2)
    if col_a.button("Reset chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if col_b.button("Reload", use_container_width=True):
        reset_model()
        st.rerun()

    params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        top_k=int(top_k),
        min_tokens=int(min_tokens),
        max_tokens=int(max_tokens),
    )
    return artifact_path, params, int(max_tokens)


def render_status(artifact_path: str) -> None:
    exists = Path(artifact_path).exists()
    loaded = st.session_state.get("loaded_artifact") == artifact_path
    latency = st.session_state.get("last_latency")

    cols = st.columns(3)
    cols[0].metric("Artifact", "Ready" if exists else "Missing")
    cols[1].metric("Model", "Loaded" if loaded else "Not loaded")
    cols[2].metric("Last run", f"{latency:.1f}s" if latency is not None else "-")


def build_prompt(llm: LLM, messages: list[dict[str, str]]) -> str:
    return llm.tokenizer.apply_chat_template(messages, tokenize=False)


def generate_reply(
    artifact_path: str, messages: list[dict[str, str]], sampling_params: SamplingParams
) -> tuple[str, str, float]:
    captured = StringIO()
    start = perf_counter()
    with redirect_stdout(captured), redirect_stderr(captured):
        llm = load_llm(artifact_path)
        st.session_state.loaded_artifact = artifact_path
        prompt = build_prompt(llm, messages)
        outputs = llm.generate([prompt], sampling_params)
    latency = perf_counter() - start
    return outputs[0].outputs[0].text, captured.getvalue(), latency


def render_chat(artifact_path: str, sampling_params: SamplingParams) -> None:
    st.subheader("Chat")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Ask the local artifact something")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if not Path(artifact_path).exists():
        st.session_state.last_error = f"Artifact path does not exist: {artifact_path}"
        st.error(st.session_state.last_error)
        return

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.info("Loading model and generating...")
        try:
            reply, logs, latency = generate_reply(
                artifact_path, st.session_state.messages, sampling_params
            )
        except Exception:
            st.session_state.last_error = traceback.format_exc()
            placeholder.error("Generation failed. Open the log panel below.")
            return

        st.session_state.last_logs = logs
        st.session_state.last_error = ""
        st.session_state.last_latency = latency
        st.session_state.messages.append({"role": "assistant", "content": reply})
        placeholder.write(reply)


def render_logs() -> None:
    st.subheader("Runtime Logs")
    last_error = st.session_state.get("last_error", "")
    last_logs = st.session_state.get("last_logs", "")

    if last_error:
        st.error("Last run failed")
        st.code(last_error, language="text")
    elif last_logs.strip():
        with st.expander("Show captured stdout/stderr", expanded=False):
            st.code(last_logs, language="text")
    else:
        st.markdown(
            '<p class="small-muted">Logs will appear here after the first run.</p>',
            unsafe_allow_html=True,
        )


def main() -> None:
    page_setup()
    init_state()

    st.title("Furiosa Artifact Chat")
    st.caption("Local artifact inference without digging through terminal logs.")

    artifact_path, sampling_params, _ = render_sidebar()
    render_status(artifact_path)
    render_chat(artifact_path, sampling_params)
    render_logs()


if __name__ == "__main__":
    main()
