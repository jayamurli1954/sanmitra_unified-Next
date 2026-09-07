"""LegalMitra RSS/XML ingest must reject entity expansion (XXE)."""
from __future__ import annotations

import pytest
from defusedxml.common import DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden

from app.modules.legal_compat.safe_xml import fromstring

_XXE_PAYLOAD = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<rss><channel><item><title>&xxe;</title></item></channel></rss>
"""


@pytest.mark.parametrize("parser", [fromstring], ids=["legal_compat.safe_xml"])
def test_legal_compat_xml_parsers_reject_external_entities(parser) -> None:
    with pytest.raises((EntitiesForbidden, DTDForbidden, ExternalReferenceForbidden)):
        parser(_XXE_PAYLOAD)
