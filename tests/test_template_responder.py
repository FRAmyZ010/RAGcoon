import pytest
from backend.app.rag.retrieval.template_responder import (
    try_generate_template_response,
    _has_technical_keywords,
    _to_thai_year,
)


def test_has_technical_keywords():
    # Technical / content queries must return True
    assert _has_technical_keywords("โปรเจกต์นี้ใช้ ESP32 และเซนเซอร์อะไรบ้าง") is True
    assert _has_technical_keywords("อธิบายการทำงานของระบบอย่างละเอียด") is True
    assert _has_technical_keywords("สถาปัตยกรรมของระบบเป็นอย่างไร") is True
    assert _has_technical_keywords("เปรียบเทียบโปรเจกต์ A กับ B") is True
    assert _has_technical_keywords("how does it work") is True
    assert _has_technical_keywords("explain the architecture") is True

    # Pure metadata queries must return False
    assert _has_technical_keywords("อาจารย์ surapol เป็น advisor Project ไหน") is False
    assert _has_technical_keywords("ใครเป็นอาจารย์ที่ปรึกษาของโปรเจกต์ The LoRaWAN", project_title="The LoRaWAN") is False
    assert _has_technical_keywords("ปี 2020 มีโปรเจกต์อะไรบ้าง") is False
    assert _has_technical_keywords("ใครทำโปรเจกต์ BSLD") is False
    assert _has_technical_keywords("อาจารย์สุรพล ดูแลกี่เรื่อง") is False


def test_to_thai_year():
    assert _to_thai_year("2020") == "2563"
    assert _to_thai_year(2023) == "2566"
    assert _to_thai_year("Unknown") == "Unknown"


def test_advisor_projects_template():
    prep = {
        "intent": "EXPLORATORY",
        "filters": {"advisor": "Aj. Surapol Vorapatratorn"},
        "citations": [
            {
                "project_title": "ONLINE VEHICLE ACCESS MONITORING",
                "advisor": "Aj. Surapol Vorapatratorn",
                "author": "PHUMPHOL CHANRUNGSRICHAY, NUTCHANON THAMAVUTICHAI",
                "year": "2020",
                "course": "Senior Project (CPE492)",
                "source": "Online-Vehicle-access-management.pdf",
                "pages_formatted": "1, 2",
            },
            {
                "project_title": "ONLINE MFU-LECTURER APPOINTMENT SYSTEM",
                "advisor": "Aj. Surapol Vorapatratorn",
                "author": "KALLAYANEE THONGKONG, SUWEE ROTSASANASATHIAN",
                "year": "2020",
                "course": "Senior Project (CPE492)",
                "source": "97_MFU_APPOINTMENT.pdf",
                "pages_formatted": "1",
            },
        ],
    }
    resp = try_generate_template_response("อาจารย์ surapol เป็น advisor Project ไหน", prep)
    assert resp is not None
    assert "Aj. Surapol Vorapatratorn" in resp
    assert "ONLINE VEHICLE ACCESS MONITORING" in resp
    assert "ONLINE MFU-LECTURER APPOINTMENT SYSTEM" in resp
    assert "2 โครงงาน" in resp


def test_project_advisor_lookup_template():
    prep = {
        "intent": "FACTOID",
        "filters": {"project_title": "The LoRaWAN"},
        "citations": [
            {
                "project_title": "The LoRaWAN",
                "advisor": "Asst. Prof. Dr. Suppakarn Chansareewittaya",
                "committee": "Dr. Mahamah Sebakor, Dr. Surapong Uttama",
                "author": "ATSAWIN CHAIBAL, PHUBET SANGEAMNGAM",
                "year": "2020",
                "course": "Senior Project (CPE492)",
                "school": "School of Information Technology",
                "program": "Computer Engineering",
                "source": "6031501044_6031501061_FinalProject.pdf",
                "pages_formatted": "1, 2, 3",
            }
        ],
    }
    resp = try_generate_template_response("ใครเป็นอาจารย์ที่ปรึกษาของโปรเจกต์ The LoRaWAN", prep)
    assert resp is not None
    assert "The LoRaWAN" in resp
    assert "Asst. Prof. Dr. Suppakarn Chansareewittaya" in resp
    assert "2563" in resp


def test_disqualified_queries_fall_back_to_llm():
    prep = {
        "intent": "EXPLORATORY",
        "filters": {"advisor": "Aj. Surapol Vorapatratorn"},
        "citations": [{"project_title": "P1", "advisor": "Aj. Surapol Vorapatratorn"}],
    }
    # Technical question with ESP32 must NOT use template
    assert try_generate_template_response("อาจารย์สุรพล มีโปรเจกต์ไหนที่ใช้ ESP32 บ้าง", prep) is None

    # Deep dive intent must NOT use template
    prep["intent"] = "DEEP_DIVE"
    assert try_generate_template_response("อธิบายการทำงานของโปรเจกต์", prep) is None

    # Recommendation intent must NOT use template
    prep["intent"] = "RECOMMENDATION"
    assert try_generate_template_response("แนะนำโปรเจกต์หน่อย", prep) is None

    # Comparison intent must NOT use template
    prep["intent"] = "COMPARISON"
    assert try_generate_template_response("เปรียบเทียบ A กับ B", prep) is None


def test_advisor_with_name_variants_and_token_matching():
    prep = {
        "intent": "FACTOID",
        "filters": {"advisor": "Surapol Vorapatratorn"},
        "citations": [
            {
                "project_title": "Project A",
                "advisor": "Asst. Prof. Dr. Surapol Vorapatratorn",
                "year": "2021",
                "source": "proj_a.pdf",
            },
            {
                "project_title": "Project B",
                "advisor": "Aj. Surapol Vorapatratorn",
                "year": "2020",
                "source": "proj_b.pdf",
            },
        ],
    }
    resp = try_generate_template_response("อาจารย์ surapol ดูแลโครงงานอะไรบ้าง", prep)
    assert resp is not None
    assert "Project A" in resp
    assert "Project B" in resp
    assert "ทั้งหมด 2 โครงงาน" in resp


def test_missing_advisor_fallback_to_committee():
    prep = {
        "intent": "FACTOID",
        "filters": {"project_title": "Smart IoT"},
        "citations": [
            {
                "project_title": "Smart IoT",
                "advisor": None,
                "committee": "Dr. Mahamah Sebakor, Dr. Surapong Uttama",
                "author": "John Doe",
                "year": "2022",
                "source": "smart_iot.pdf",
            }
        ],
    }
    resp = try_generate_template_response("ใครเป็นที่ปรึกษาของ Smart IoT", prep)
    assert resp is not None
    assert "Dr. Mahamah Sebakor (จากรายชื่อคณะกรรมการ)" in resp


def test_course_senior_project_template():
    prep = {
        "intent": "EXPLORATORY",
        "filters": {},
        "citations": [
            {
                "project_title": "Vehicle Access System",
                "course": "Senior Project (CPE492)",
                "author": "Alice",
                "advisor": "Bob",
                "year": "2020",
                "source": "doc1.pdf",
            }
        ],
    }
    resp = try_generate_template_response("วิชา Senior Project มีโครงงานอะไรบ้าง", prep)
    assert resp is not None
    assert "Senior Project (CPE492)" in resp
    assert "Vehicle Access System" in resp


def test_school_template():
    prep = {
        "intent": "EXPLORATORY",
        "filters": {},
        "citations": [
            {
                "project_title": "Network Security Project",
                "school": "Applied Digital Technology",
                "program": "Computer Engineering",
                "course": "Senior Project (CPE492)",
                "advisor": "Dr. Smith",
                "year": "2021",
                "source": "sec.pdf",
            }
        ],
    }
    resp = try_generate_template_response("สำนักวิชา Applied Digital Technology มีโครงงานอะไรบ้าง", prep)
    assert resp is not None
    assert "Applied Digital Technology" in resp
    assert "Network Security Project" in resp


def test_program_major_template():
    prep = {
        "intent": "EXPLORATORY",
        "filters": {},
        "citations": [
            {
                "project_title": "AI Image Animator",
                "program": "Multimedia Technology & Animation",
                "course": "Senior Project (CPE492)",
                "advisor": "Dr. Animator",
                "year": "2023",
                "source": "mta.pdf",
            }
        ],
    }
    resp = try_generate_template_response("โครงงานสาขา Multimedia Technology & Animation มีอะไรบ้าง", prep)
    assert resp is not None
    assert "Multimedia Technology & Animation" in resp
    assert "AI Image Animator" in resp
