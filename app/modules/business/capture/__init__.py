"""AI document capture add-on (Phase 1): upload a bill → LLM-vision extract →
deterministic validate → confidence score → route to a review queue.

Enterprise opt-in, default OFF (see gating.py). The pipeline produces draft
CaptureItems only; it never posts to the ledger on its own. Materializing an
approved capture into a typed purchase bill (which then flows through the
existing approval queue) is a later slice.
"""
