from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from .metadata_cache import metadata_cache


def build_qdrant_filter(filters: dict | None) -> Filter | None:
    if not filters:
        return None

    metadata_cache.load_metadata()
    conditions = []

    VALID_FILTER_KEYS = {
        "author",
        "advisor",
        "year",
        "project_title",
        "program",
        "school",
        "project_type",
        "key_technologies",
    }

    for key, value in filters.items():
        if key not in VALID_FILTER_KEYS:
            continue
        if value is None or value == "" or value == [] or str(value).strip().lower() in ("null", "none", "n/a", "undefined"):
            continue

        if key == "author":
            author_list = value if isinstance(value, list) else [value]
            all_matching_payloads = set()
            for auth in author_list:
                auth_str = str(auth).strip()
                if not auth_str:
                    continue
                resolved = metadata_cache.resolve_author_variants(auth_str)
                if resolved:
                    all_matching_payloads.update(resolved)
                else:
                    all_matching_payloads.add(auth_str)

            if len(all_matching_payloads) == 1:
                conditions.append(FieldCondition(key="author", match=MatchValue(value=list(all_matching_payloads)[0])))
            elif len(all_matching_payloads) > 1:
                conditions.append(FieldCondition(key="author", match=MatchAny(any=list(all_matching_payloads))))

        elif key == "advisor":
            advisor_list = value if isinstance(value, list) else [value]
            all_matching_advisors = set()
            for adv in advisor_list:
                adv_str = str(adv).strip()
                if not adv_str:
                    continue
                resolved = metadata_cache.resolve_advisor_variants(adv_str)
                if resolved:
                    all_matching_advisors.update(resolved)
                else:
                    all_matching_advisors.add(adv_str)

            if len(all_matching_advisors) == 1:
                conditions.append(FieldCondition(key="advisor", match=MatchValue(value=list(all_matching_advisors)[0])))
            elif len(all_matching_advisors) > 1:
                conditions.append(FieldCondition(key="advisor", match=MatchAny(any=list(all_matching_advisors))))

        elif key == "project_type":
            val_str = str(value).strip().lower()
            if any(k in val_str for k in ["iot", "hardware", "ไอโอที", "ฮาร์ดแวร์"]):
                target_types = ["IoT", "IoT & Hardware", "Hardware", "Embedded Systems", "Robotics"]
            elif any(k in val_str for k in ["web", "เว็บ"]):
                target_types = ["Web Application", "Web", "Website"]
            elif any(k in val_str for k in ["network", "เน็ตเวิร์ก", "เครือข่าย", "wireless", "wlan"]):
                target_types = ["Network", "Network & Wireless", "Wireless Communication", "Wireless LAN"]
            elif any(k in val_str for k in ["ai", "machine learning", "ปัญญาประดิษฐ์"]):
                target_types = ["AI & Machine Learning", "Computer Vision"]
            elif any(k in val_str for k in ["security", "cyber", "ความปลอดภัย"]):
                target_types = ["Cybersecurity"]
            elif any(k in val_str for k in ["mobile", "โมบาย", "แอปมือถือ"]):
                target_types = ["Mobile App", "Mobile Application"]
            else:
                target_types = [value] if isinstance(value, str) else list(value)

            conditions.append(FieldCondition(key="project_type", match=MatchAny(any=target_types)))

        elif isinstance(value, list):
            conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
        else:
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

    return Filter(must=conditions) if conditions else None



