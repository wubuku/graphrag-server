import re
from collections import defaultdict
from typing import Set, Dict

from webserver.configs import settings

# pattern = re.compile(r'\[\^Data:(\w+?)\((\d+(?:,\d+)*)\)\]')
# Updated pattern to support both formats:
# [^Data:Sources(446)] and [Data: Sources (446)]
# [Data: Sources (15, 16), Reports (1), Entities (5, 7); Relationships (23); Claims (2, 7, 34, 46, 64, +more)]

# Comprehensive regex that captures the entire reference format at once
# This avoids false matches of text that isn't actually a reference
pattern = re.compile(r'\[\^?Data:(?:\s*(\w+)\s*\(([\d\s,]+(?:\+\w+)?)\)(?:[,;]\s*)?)+\]')

def get_reference(text: str) -> dict:
    data_dict = defaultdict(set)
    
    # Find all complete references
    for match in pattern.finditer(text):
        # Get the entire matched string
        full_match = match.group(0)
        
        # Use a separate regex to extract individual data types and IDs from the full match
        # This is a controlled extraction from already validated content
        for item_match in re.finditer(r'(\w+)\s*\(([\d\s,]+(?:\+\w+)?)\)', full_match):
            data_type = item_match.group(1).lower()
            id_text = item_match.group(2)
            
            # Clean and extract IDs
            id_text = re.sub(r'\+\w+', '', id_text)  # Remove "+more" or similar
            for id_str in id_text.split(','):
                id_str = id_str.strip()
                if id_str.isdigit():
                    data_dict[data_type].add(id_str)
    
    return dict(data_dict)


def generate_ref_links(data: Dict[str, Set[int]], index_id: str) -> str:
    base_url = f"{settings.reference_url_base}/v1/references"
    lines = []
    for key, values in data.items():
        for value in values:
            lines.append(f'[^Data:{key.capitalize()}({value})]: [{key.capitalize()}: {value}]({base_url}/{index_id}/{key}/{value})')
    return "\n".join(lines)
