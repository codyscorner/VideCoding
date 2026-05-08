# ComfyUI Workflow Editor — Plan

## Overview

A simple desktop form editor for ComfyUI workflow JSON files.
Open a `.json` workflow, edit the fields that matter most (prompts, LoRA strengths, sampler settings),
and save. No node canvas, no wires — just a clean scrollable form.

---

## What It Edits

| Node type | Section shown | Fields |
|-----------|--------------|--------|
| CLIPTextEncode | **Prompts** | `text` (multiline) — negative tinted red |
| LoraLoader / LoraLoaderModelOnly | **LoRA Strengths** | `strength_model`, `strength_clip` |
| Lora Loader Stack (rgthree) | **LoRA Strengths** | all `strength_NN` slots |
| KSampler / KSamplerAdvanced | **KSampler** | steps, CFG, sampler, scheduler, seed |
| WanImageToVideo / WanVideoToVideo | **Video Settings** | frame count |

Everything else in the JSON is passed through untouched on save.

---

## Tech Stack

- Python + PyQt6
- No ComfyUI server connection needed — pure file editor

---

## UI Layout

```
┌─ Menu: File ─────────────────────────────────────────────────┐
├─ Toolbar: [Open] [Save]  filename.json ──────────────────────┤
│                                                              │
│  ┌── Prompts ─────────────────────────────────────────────┐  │
│  │  Positive Prompt  (CLIPTextEncode #6)                  │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ beautiful landscape, detailed...                  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │  Negative Prompt  (CLIPTextEncode #7)                  │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ blurry, ugly...                                   │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌── LoRA Strengths ────────────────────────────────────┐    │
│  │  my_lora_v2         Model: [0.80]  CLIP: [0.80]      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌── KSampler ──────────────────────────────────────────┐    │
│  │  Steps: [20]  CFG: [7.0]  Sampler: [euler ▾]         │    │
│  │  Seed:  [123456789]                                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
├─ Status bar: filename — N nodes — M editable fields ─────────┤
└──────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
Cumfy_Workflow_Editor/
  main.py                  ← entry point (v1.0.0)
  ui/
    __init__.py
    styles.py              ← dark theme (shared with Chain Automator)
    main_window.py         ← all form logic here
    node_cards.py          ← (unused, kept for future canvas mode)
    canvas.py              ← (unused, kept for future canvas mode)
```

---

## Out of Scope (for now)

- Node canvas / drag-drop layout
- Adding, removing, or rewiring nodes
- Connecting to the ComfyUI server
- Custom node types beyond the list above

---

## App Name

**ComfyUI Workflow Editor**
EXE target: `P:\Apps\VibeCoded\ComfyUI Workflow Editor\`
