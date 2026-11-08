"""Pluggable extraction backends for document capture.

Default is open-source + local (Tesseract OCR + Indian-GST rules) — no API key,
no per-document cost, documents stay on the server/device. The LLM-vision backend
is an optional booster that uses the tenant's own key (BYOK) or a local model.

All backends return the SAME normalized dict, so the validators, scoring, gate and
routing downstream are engine-agnostic.
"""
