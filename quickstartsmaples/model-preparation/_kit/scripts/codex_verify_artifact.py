"""Verify a Furiosa LLM artifact - Codex-reviewed variant.

This file intentionally leaves the original ``verify_artifact.py`` untouched.

Unlike the original smoke test, this script runs inference in a child process,
streams the runtime log back to the terminal, and then turns the documented log
requirements into pass/fail checks.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from furiosa_llm import LLM, SamplingParams


FORBIDDEN_LOG_PATTERNS = (
    "No extend buckets",
    "Chunked prefill will be disabled",
    "Disabling prefix caching",
)
REQUIRED_LOG_PATTERN = "is_prefix_cache_enabled: true"


def render_prompt(llm: LLM, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    try:
        return llm.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except TypeError:
        # Older tokenizer wrappers may not expose add_generation_prompt.
        return llm.tokenizer.apply_chat_template(messages, tokenize=False)


def run_inference_worker(artifact: str, prompt: str) -> None:
    with LLM(artifact) as llm:
        sampling_params = SamplingParams(min_tokens=10, top_p=0.3, top_k=100)
        rendered_prompt = render_prompt(llm, prompt)
        result = llm.generate([rendered_prompt], sampling_params)[0].outputs[0].text
        print("\n=== Model output ===")
        print(result)


def run_child_and_capture(args: argparse.Namespace) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--artifact",
        args.artifact,
        "--prompt",
        args.prompt,
        "--_worker",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    captured: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        captured.append(line)
        print(line, end="")

    return process.wait(), "".join(captured)


def verify_logs(output: str, require_prefix_cache_log: bool) -> list[str]:
    failures: list[str] = []

    for pattern in FORBIDDEN_LOG_PATTERNS:
        if pattern in output:
            failures.append(f"forbidden warning appeared: {pattern!r}")

    if require_prefix_cache_log and REQUIRED_LOG_PATTERN not in output:
        failures.append(f"required log line missing: {REQUIRED_LOG_PATTERN!r}")

    if "=== Model output ===" not in output:
        failures.append("model output marker missing")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default="./artifact", help="Built artifact path")
    parser.add_argument("--prompt", default="What is the capital of France?")
    parser.add_argument(
        "--no-require-prefix-cache-log",
        action="store_true",
        help="Do not fail when the runtime omits the is_prefix_cache_enabled log line.",
    )
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args._worker:
        run_inference_worker(args.artifact, args.prompt)
        return

    returncode, output = run_child_and_capture(args)
    failures = verify_logs(output, require_prefix_cache_log=not args.no_require_prefix_cache_log)

    if returncode != 0:
        failures.append(f"inference process exited with code {returncode}")

    print("\n=== Verification result ===")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("PASS: inference ran, forbidden warnings were absent, and prefix caching was reported enabled.")


if __name__ == "__main__":
    main()
