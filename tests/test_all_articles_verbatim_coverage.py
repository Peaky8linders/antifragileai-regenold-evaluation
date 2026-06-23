import pytest
from app.data.official_eu_ai_act import OFFICIAL_ARTICLE_TEXT
from app.data.provision_text import get_provision_text

def test_all_articles_can_be_resolved():
    """
    Ensures that get_provision_text can successfully resolve the top-level text
    for every single Article and Annex defined in the official EU AI Act corpus.
    This expands our verbatim testing beyond Article 6 to the entire 113+ articles.
    """
    failed_keys = []
    
    # OFFICIAL_ARTICLE_TEXT contains keys like "Article 1", "Article 2", etc., and "Annex I", etc.
    for key in OFFICIAL_ARTICLE_TEXT.keys():
        text = get_provision_text(key)
        if not text:
            failed_keys.append(key)
            
    assert not failed_keys, f"Failed to resolve provision text for: {failed_keys}"

def test_random_sample_of_subpoints():
    """
    Verifies that get_provision_text also safely handles deeper resolutions 
    for broadly sampled provisions across the Act, proving that Article 6
    is not the only one that works.
    """
    samples = [
        "Article 5(1)", 
        "Article 5(1)(a)",
        "Article 9(2)",
        "Article 10(3)",
        "Article 13(1)",
        "Article 14(4)",
        "Article 50(1)",
        "Article 112(1)",
    ]
    failed = []
    for sample in samples:
        if not get_provision_text(sample):
            failed.append(sample)
            
    assert not failed, f"Failed to resolve sampled subpoints: {failed}"
