from app.scoring import keyword_score

def test_score_contains_evidence_and_no_auto_reject():
    cv="Candidate has 6.5 years of experience in Java and Spring Boot. Notice period is 30 days."
    result=keyword_score(cv,{"must_have":["Java","Spring Boot","Microservices"],"min_experience":5,"max_notice":60})
    assert result["score"] > 0
    assert any(x["criterion"]=="Java" and x["matched"] for x in result["evidence"])
    assert any(x["criterion"]=="Microservices" and not x["matched"] for x in result["evidence"])
    assert "caveat" in result
