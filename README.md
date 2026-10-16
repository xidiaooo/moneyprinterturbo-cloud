---
title: MoneyPrinterTurbo
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# MoneyPrinterTurbo on Hugging Face Spaces

一站式 AI 短视频生成：主题 → 脚本(OpenRouter 免费模型) → Pixabay 素材 →
Edge TTS 配音 → 字幕 → 成片。

## 所需 Secrets（Settings → Variables and secrets）

- `OPENROUTER_API_KEY`：写脚本用
- `PIXABAY_API_KEY`：拉视频素材用

入口 `entrypoint.py` 会在启动时用这两个 key 生成 `config.toml`，
key 不会进镜像层。
