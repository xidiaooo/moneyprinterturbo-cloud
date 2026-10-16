#!/usr/bin/env python3
"""Hugging Face Spaces entrypoint for MoneyPrinterTurbo.

Reads API keys from Space secrets (env vars), writes config.toml,
then launches the Streamlit WebUI on port 7860.

Required secrets:
  OPENROUTER_API_KEY  - OpenRouter key for script generation
  PIXABAY_API_KEY     - Pixabay key for video materials
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    missing = [
        name
        for name, val in (
            ("OPENROUTER_API_KEY", openrouter_key),
            ("PIXABAY_API_KEY", pixabay_key),
        )
        if not val
    ]
    if missing:
        print(f"FATAL: missing Space secrets: {', '.join(missing)}", flush=True)
        print("Add them in Space Settings -> Variables and secrets, then restart.",
              flush=True)
        sys.exit(1)

    example = os.path.join(BASE, "config.example.toml")
    with open(example, encoding="utf-8") as f:
        text = f.read()

    text = re.sub(r'^llm_provider\s*=.*$',
                  'llm_provider = "openrouter"', text, flags=re.M)
    text = re.sub(r'^openrouter_api_key\s*=.*$',
                  f'openrouter_api_key = "{openrouter_key}"', text, flags=re.M)
    text = re.sub(r'^openrouter_model_name\s*=.*$',
                  'openrouter_model_name = "nvidia/nemotron-3.5-lightning:free"',
                  text, flags=re.M)
    text = re.sub(r'^video_source\s*=.*$',
                  'video_source = "pixabay"', text, flags=re.M)
    text = re.sub(r'^pixabay_api_keys\s*=.*$',
                  f'pixabay_api_keys = ["{pixabay_key}"]', text, flags=re.M)

    cfg_path = os.path.join(BASE, "config.toml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(cfg_path, 0o600)
    print("config.toml written from Space secrets", flush=True)

    port = os.environ.get("PORT", "7860")
    os.execvp("streamlit", [
        "streamlit", "run", os.path.join(BASE, "webui", "Main.py"),
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    main()
