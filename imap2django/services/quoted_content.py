import re

QUOTE_PATTERNS = [
    re.compile(r'^>+.*$', re.MULTILINE),
    re.compile(r'^On .+ wrote:.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^From:.*$', re.MULTILINE),
    re.compile(r'^Sent:.*$', re.MULTILINE),
    re.compile(r'^To:.*$', re.MULTILINE),
    re.compile(r'^Subject:.*$', re.MULTILINE),
    re.compile(r'^-----Original Message-----.*$', re.MULTILINE | re.DOTALL),
    re.compile(r'^___________________________*$', re.MULTILINE),
]

def strip_quoted_content(text: str) -> str:
    if not text:
        return ""
    
    lines = text.split('\n')
    result_lines = []
    in_quote = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not in_quote:
                result_lines.append(line)
            continue
        
        is_quote_line = any(pattern.match(line) for pattern in QUOTE_PATTERNS)
        
        if is_quote_line:
            in_quote = True
            continue
        
        if in_quote and (stripped.startswith('>') or 'wrote:' in stripped.lower()):
            continue
        
        in_quote = False
        result_lines.append(line)
    
    return '\n'.join(result_lines).strip()

