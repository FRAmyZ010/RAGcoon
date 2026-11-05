import pytest
from backend.app.rag.embedding.metadata_extractor import (
    clean_project_title,
    _looks_like_author_name,
    _extract_title_and_authors,
    _extract_approval_committee,
    _extract_supervisory_block,
    _finalize_person_name,
    _is_valid_author_name,
    _is_valid_supervisory_name,
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


def test_extract_keywords_from_label():
    text = """
    Intelligent Watering System
    Keywords: Arduino Mega 2560, soil moisture, LoRa
    ABSTRACT
    This project waters plants.
    """
    meta = extract_project_metadata(text)
    assert meta["keywords"] == "Arduino Mega 2560, soil moisture, LoRa"


def test_extract_thai_keywords_on_the_next_line():
    text = """
    ระบบรดน้ำอัจฉริยะ
    คำสำคัญ
    เซนเซอร์, อาดูอิโน, โลรา
    """
    meta = extract_project_metadata(text)
    assert meta["keywords"] == "เซนเซอร์, อาดูอิโน, โลรา"


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
    assert meta["school"] == "Applied Digital Technology"
    assert meta["program"] == "Computer Engineering"
    assert meta["project_title"] == "Gem car tracking application"


def test_all_five_majors_mapped_to_applied_digital_technology():
    majors = [
        ("BACHELOR OF ENGINEERING IN COMPUTER ENGINEERING", "Computer Engineering"),
        ("BACHELOR OF SCIENCE IN SOFTWARE ENGINEERING", "Software Engineering"),
        ("BACHELOR OF SCIENCE IN MULTIMEDIA TECHNOLOGY & ANIMATION", "Multimedia Technology & Animation"),
        ("BACHELOR OF ENGINEERING IN DIGITAL ENGINEERING & COMMUNICATIONS", "Digital Engineering & Communications"),
        ("BACHELOR OF SCIENCE IN DIGITAL TECHNOLOGY FOR BUSINESS INNOVATION", "Digital Technology for Business Innovation"),
    ]
    for text_fragment, expected_program in majors:
        full_text = f"Sample Project Title\nJohn Doe\n{text_fragment}\n2023"
        meta = extract_project_metadata(full_text)
        assert meta["program"] == expected_program, f"Failed for {text_fragment}"
        assert meta["school"] == "Applied Digital Technology", f"School must be Applied Digital Technology for {expected_program}"


def test_author_label_stripped_and_length_filter():
    assert _finalize_person_name("Author Mr. Vasawat prapachaimongkol") == "Mr. Vasawat prapachaimongkol"
    assert _is_valid_author_name("Aung") is False  # len <= 5
    assert _is_valid_author_name("AungMy") is True
    assert _is_valid_author_name("Mr. Vasawat prapachaimongkol") is True

    text = """
    Title Robot avoiding obstacles
    Author Mr. Vasawat prapachaimongkol
    Mr. Peeradon buranathawon
    Degree Bachelor of Engineering
    (Computer Engineering)
    Supervisory Committee Asst. Prof. Gp. Capt. Dr. Thongchai Yooyatiwong Advisor
    Aj. Dr. Mahamah Sebakor Committee
    Asst. Prof. Dr. Roungsan Chaisricharoen Committee
    Abstract
    The robot project explores automation.
    """
    meta = extract_project_metadata(text)
    assert meta["author"] == "Mr. Vasawat prapachaimongkol, Mr. Peeradon buranathawon"
    assert not meta["author"].lower().startswith("author ")
    assert meta["advisor"] == "Asst. Prof. Gp. Capt. Dr. Thongchai Yooyatiwong"
    assert meta["committee"] == "Aj. Dr. Mahamah Sebakor, Asst. Prof. Dr. Roungsan Chaisricharoen"


def test_supervisory_name_filters_drop_junk():
    assert _is_valid_supervisory_name("Committ") is False
    assert _is_valid_supervisory_name("Aj. ee") is False
    assert _is_valid_supervisory_name("Aj. Mahamah Sebakor") is True
    assert _is_valid_supervisory_name("Dr. X") is False  # too short


def test_cisco_style_broken_supervisory_does_not_leak_junk():
    lines = [
        "Supervisory Aj.Mahamah Sebakor Advisor",
        "Committee",
        "Aj. Dr.Surapol Committ",
        "Vorapatratorn Aj. ee",
        "Suppakarn Committ",
        "Chaisricharoen ee",
        "Abstract",
    ]
    advisor, committee = _extract_supervisory_block(lines)
    assert advisor == "Aj. Mahamah Sebakor"
    assert committee == []

    text = "\n".join(
        [
            "Title The development of Bluetooth low energy in cisco WLAN",
            "Author Mr.Kiattisak Hasati",
            "Miss Parichat Taram",
            "Degree Bachelor of Engineering",
            "(Computer Engineering)",
            *lines,
            "Keyword: Bluetooth Low Energy",
        ]
    )
    meta = extract_project_metadata(text)
    assert meta["author"] == "Mr. Kiattisak Hasati, Miss Parichat Taram"
    assert meta["advisor"] == "Aj. Mahamah Sebakor"
    assert meta["committee"] is None

