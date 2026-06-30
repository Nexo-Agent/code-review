from app.services.review_analytics_events import normalize_feedback_keyword


def test_normalize_feedback_keyword_accepts_exact_keywords() -> None:
    assert normalize_feedback_keyword("Helpful") == {
        "feedback_group": "quality_feedback",
        "feedback_value": "helpful",
        "match_type": "exact_keyword",
    }
    assert normalize_feedback_keyword("Not Helpful.") == {
        "feedback_group": "quality_feedback",
        "feedback_value": "not_helpful",
        "match_type": "exact_keyword",
    }
    assert normalize_feedback_keyword("Applied!") == {
        "feedback_group": "resolution_feedback",
        "feedback_value": "applied",
        "match_type": "exact_keyword",
    }


def test_normalize_feedback_keyword_rejects_freeform_text() -> None:
    assert normalize_feedback_keyword("this is fixed now") is None
