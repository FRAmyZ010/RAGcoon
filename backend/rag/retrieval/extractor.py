import re
from typing import Dict, Tuple

from .metadata_cache import metadata_cache

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Extract key:value or key="value" or key:"value" patterns
# Supports project_title, title, author, advisor, keywords
KV_PATTERN = re.compile(
    r'(?:"?)\b(project_title|title|author|advisor|keywords?)\b(?:"?)\s*[:=]\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s"]+))', 
    re.IGNORECASE
)

# Comprehensive list of MFU ADT Staff / Lecturers based on the directory
# Maps common short names to their possible full formal names or just used for detection
MFU_STAFF = [
    "Nacha", "Worasak", "Pruet", "Paweena", "Kemachart", "Surapol",
    "Shanmugam", "Khwunta", "Pattaramon", "Narong", "Chayapol", "Mahamah",
    "Suppakarn", "Sirikan", "Titiya", "Teeravisit", "Prasara", "Wacharawan",
    "Nang", "Sujitra", "Vittayasak", "Tew", "Nikorn", "Soontarin", "Patcharaporn",
    "Teanjit", "Nilubon", "Waralak", "Charoenchai", "Nontawat", "Yootthapong",
    "Karn", "Thanpahtt", "Banphot", "Ratchanon", "Surapong", "Santichai",
    "Thongchai", "Roungsan", "Punnarumol", "Nattapol", "Tossapon", "Natthakan"
]

# Mapping heuristic names to exact Qdrant values based on metadata_extractor
# Add more mappings here if necessary to match the exact string in the database
ADVISOR_EXACT_MAP = {
    "Mahamah": "Dr. Mahamah Sebakor",
    "Surapol": "Aj. Surapol Vorapatratorn",
    "Tossapon": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
    "Natthakan": "Asst.Prof.Dr.Natthakan Iam-On",
    "Suppakarn": "Asst.Prof.Suppakarn Chansareewittaya",
    "Worasak": "Asst.Prof. Worasak Rueangsirarak",
    "Paweena": "Paweena Suebsombut",
    "Kemachart": "Kemachart Kemavuthanon",
    "Khwunta": "Asst.Prof. Khwunta Kirimasthong",
    "Pattaramon": "Asst.Prof. Pattaramon Vuttipittayamongkol",
    "Shanmugam": "Prof. Shanmugam Nandagopalan",
}

def extract_query_and_filters(user_query: str) -> Tuple[str, Dict]:
    """
    Extracts the cleaned query and metadata filters from the user query.
    Applies rule-based extraction for explicit fields, MFU staff names, 
    and dynamic matching against Qdrant metadata.
    """
    
    # Ensure metadata is loaded from Qdrant
    metadata_cache.load_metadata()
    
    filters = {}
    clean_query = user_query

    # 1. Extract Explicit Key-Value Pairs
    # Examples: project_title:"QUALITY DISCHARGE PLANNING PROJECT", advisor:Tossapon
    for match in KV_PATTERN.finditer(user_query):
        key = match.group(1).lower()
        if key == "title":
            key = "project_title"
        elif key == "keyword":
            key = "keywords"
            
        value = match.group(2) or match.group(3) or match.group(4)
        
        if value:
            # Map advisor short names to exact values if applicable
            if key == "advisor":
                for short_name, exact_name in ADVISOR_EXACT_MAP.items():
                    if short_name.lower() in value.lower():
                        value = exact_name
                        break
            
            filters[key] = value.strip()
            # Remove the exact match from the query string
            clean_query = clean_query.replace(match.group(0), "")

    # 2. Extract Year
    year_match = YEAR_PATTERN.search(clean_query)
    if year_match:
        filters["year"] = year_match.group()
        clean_query = YEAR_PATTERN.sub("", clean_query)
        
    # 3. Dynamic matching against exact Qdrant metadata fields
    # We sort by length descending to match longest phrases first
    
    # Match Project Titles
    if "project_title" not in filters:
        for title in sorted(metadata_cache.titles, key=len, reverse=True):
            if len(title) > 3 and title.lower() in clean_query.lower():
                filters["project_title"] = title
                # Remove title from query
                pattern = re.compile(re.escape(title), re.IGNORECASE)
                clean_query = pattern.sub("", clean_query)
                break
                
    # Match Authors
    if "author" not in filters:
        for author in sorted(metadata_cache.authors, key=len, reverse=True):
            if len(author) > 3 and author.lower() in clean_query.lower():
                full_strings = list(metadata_cache.author_to_full.get(author, [author]))
                filters["author"] = full_strings if len(full_strings) > 1 else full_strings[0]
                pattern = re.compile(re.escape(author), re.IGNORECASE)
                clean_query = pattern.sub("", clean_query)
                break
                
    # Match Advisors
    if "advisor" not in filters:
        for advisor in sorted(metadata_cache.advisors, key=len, reverse=True):
            if len(advisor) > 3 and advisor.lower() in clean_query.lower():
                filters["advisor"] = advisor
                pattern = re.compile(re.escape(advisor), re.IGNORECASE)
                clean_query = pattern.sub("", clean_query)
                break

    # Match Keywords
    if "keywords" not in filters:
        for kw in sorted(metadata_cache.keywords, key=len, reverse=True):
            if len(kw) > 2 and kw.lower() in clean_query.lower():
                full_strings = list(metadata_cache.keyword_to_full.get(kw, [kw]))
                filters["keywords"] = full_strings if len(full_strings) > 1 else full_strings[0]
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                clean_query = pattern.sub("", clean_query)
                break

    # 4. Rule-based heuristic for Advisor (if not already found explicitly or dynamically)
    if "advisor" not in filters:
        lower_query = clean_query.lower()
        for staff in MFU_STAFF:
            if re.search(r'\b' + re.escape(staff.lower()) + r'\b', lower_query):
                # Use mapped exact name if available, otherwise just use the staff name
                exact_name = ADVISOR_EXACT_MAP.get(staff, staff)
                filters["advisor"] = exact_name
                
                # Remove the name from the query
                clean_query = re.sub(r'\b' + re.escape(staff) + r'\b', "", clean_query, flags=re.IGNORECASE)
                break # Take the first match

    clean_query = " ".join(clean_query.split()) # clean up extra spaces
    return clean_query, filters
