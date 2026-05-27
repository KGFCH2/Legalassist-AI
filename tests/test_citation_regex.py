from core.citation_engine import CitationEngine


def test_expanded_reporters():
    text = "The court relied on the judgment in Rajesh v. State of Kerala, MHC 2026 Mad 45."
    result = CitationEngine.analyze(text)
    citations = result["citations"]
    
    assert len(citations) > 0
    assert any("MHC 2026" in c["citation"] for c in citations)


def test_sclr_reporters():
    text = "Refer to the precedent Amit v. Union of India, SCLR 2026 SC 1234."
    result = CitationEngine.analyze(text)
    citations = result["citations"]
    
    assert len(citations) > 0
    assert any("SCLR 2026" in c["citation"] for c in citations)
