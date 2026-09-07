"""Parse untrusted XML without entity expansion (XXE).

std ``xml.etree`` is kept only for the ``Element`` type; parsing uses defusedxml.
"""
from xml.etree.ElementTree import Element
from defusedxml.ElementTree import fromstring

__all__ = ["Element", "fromstring"]
