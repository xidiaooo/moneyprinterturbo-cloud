"""Streamlit Community Cloud entrypoint for MoneyPrinterTurbo.

Builds config.toml from the app's Secrets on first run only
(the filesystem is ephemeral; UI-saved settings survive reruns
within the same session because we don't overwrite an existing file).

Required secrets (App settings -> Secrets):
  OPENROUTER_API_KEY = "..."
  PIXABAY_API_KEY    = "..."
"""
import os
import re
import runpy
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import streamlit as st  # noqa: E402


def _build_config():
    secrets = st.secrets
    openrouter_key = str(secrets.get("OPENROUTER_API_KEY", "")).strip()
    pixabay_key = str(secrets.get("PIXABAY_API_KEY", "")).strip()
    if not openrouter_key or not pixabay_key:
        st.error(
            "缺少 Secrets：请在 App 设置 → Secrets 里填写 "
            "OPENROUTER_API_KEY 和 PIXABAY_API_KEY，然后重启 App。"
        )
        st.stop()

    with open(os.path.join(BASE, "config.example.toml"), encoding="utf-8") as f:
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


if not os.path.exists(os.path.join(BASE, "config.toml")):
    _build_config()

runpy.run_path(os.path.join(BASE, "webui", "Main.py"), run_name="__main__")
