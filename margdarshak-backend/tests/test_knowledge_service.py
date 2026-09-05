from app.services.knowledge_service import knowledge_rank


def test_knowledge_priority_matches_product_contract() -> None:
    assert knowledge_rank("resolved_issue") < knowledge_rank("company_information")
    assert knowledge_rank("company_information") < knowledge_rank("placement_policy")
    assert knowledge_rank("placement_policy") < knowledge_rank("shortlist")
    assert knowledge_rank("shortlist") < knowledge_rank("other")
