import pytest
from backend.app.rag.embedding.metadata_extractor import (
    clean_project_title,
    _looks_like_author_name,
    _extract_title_and_authors,
    _extract_approval_committee,
    extract_project_metadata,
)


def test_clean_project_title():
    assert clean_project_title("PROJECT PROPOSAL THE LOGO DETECTION IN AN ILLEGITIMATE WEB PAGE") == "THE LOGO DETECTION IN AN ILLEGITIMATE WEB PAGE"
    assert clean_project_title("(PROJECT PROPSAL) Dust Collector Mini Robot Model") == "Dust Collector Mini Robot Model"
    assert clean_project_title("PROJECT PROPOSAL") is None
    assert clean_project_title("(PROJECT PROPOSAL)") is None
    assert clean_project_title("Title: The LoRaWAN") == "The LoRaWAN"
    assert clean_project_title("Gem car tracking application") == "Gem car tracking application"


def test_looks_like_author_name():
    assert _looks_like_author_name("NOTCHANON SRISANSAKUL") is True
    assert _looks_like_author_name("Vasawat prapachaimongkol") is True
    assert _looks_like_author_name("Mr. Phunyavee Khwandee") is True
    # Non-author words from titles / university should be rejected
    assert _looks_like_author_name("MAE FAH LUANG UNIVERSITY") is False
    assert _looks_like_author_name("CLUSTERING ALGORITHM") is False
    assert _looks_like_author_name("LPG WEB SERVICVE") is False
    assert _looks_like_author_name("MFU CASE STUDY") is False


def test_extract_approval_committee_with_adviser():
    lines = [
        "EXAMINING COMMITTEE",
        ".................................................................... ADVISER",
        "(Asst. Prof. Dr. Suppakarn Chansareewittaya)",
        ".................................................................... COMMITTEE",
        "(Dr. Mahamah Sebakor)",
        ".................................................................... COMMITTEE",
        "(Dr. Surapong Uttama)",
    ]
    advisor, committee = _extract_approval_committee(lines)
    assert advisor == "Asst. Prof. Dr. Suppakarn Chansareewittaya"
    assert committee == ["Dr. Mahamah Sebakor", "Dr. Surapong Uttama"]


def test_extract_academic_metadata():
    sample_text = """
    Gem car tracking application
    NOTCHANON SRISANSAKUL
    A COMPUTER ENGINEERING PROJECT SUBMITTED TO
    MAE FAH LUANG UNIVERSITY IN PARTIAL FULFILLMENT OF
    THE REQUIREMENTS FOR THE DEGREE OF
    BACHELOR OF ENGINEERING
    IN COMPUTER ENGINEERING
    SCHOOL OF INFORMATION TECHNOLOGY
    MAE FAH LUANG UNIVERSITY
    2022
    """
    meta = extract_project_metadata(sample_text, filename="Pre-Project_Gem_Car2.pdf")
    assert meta["school"] == "School of Information Technology"
    assert meta["program"] == "Computer Engineering"
    assert meta["course"] == "Pre-Project (CPE491)"
    assert meta["project_title"] == "Gem car tracking application"

