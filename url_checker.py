import re
import os

def load_tlds():
    tld_file_path = os.path.join(os.path.dirname(__file__), "TLDs.txt")
    with open(tld_file_path, 'r') as file:
        # Skip comments and empty lines, convert to lowercase
        tlds = [line.strip().lower() for line in file if line.strip() and not line.strip().startswith('//')]
    return tlds

VALID_TLDS = load_tlds()

def contains_prohibited_url(text, exempt_patterns=None):
    if exempt_patterns is None:
        exempt_patterns = []
    
    url_pattern = re.compile(
        r'((?:(?:https?://)|(?:www\.)|(?:[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+))\S*)', 
        re.IGNORECASE
    )
    matches = url_pattern.findall(text)

    for match in matches:
        url = re.sub(r'\s+', '', match)

        if url.lower().startswith("www."):
            url = "http://" + url
        
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            parts = domain.lower().split('.')
            if len(parts) > 1 and parts[-1] in VALID_TLDS:
                allowed = any(pattern.lower() in url.lower() for pattern in exempt_patterns)
                if not allowed:
                    return True

    return False

if __name__ == "__main__":
    from glob import glob as glob_glob
    from re import split as re_split

    all_urls = []
    for file_path in glob_glob("*_allowed_urls.txt"):
        with open(file_path, 'r') as file:
            urls = re_split(r'\n+', file.read().strip())
            all_urls.extend(urls)

    test_texts = [
        "linx.yodobashi",
        "x.y",
        "link.sinx.logx",
    ]
    
    print("Testing URL detection with valid TLDs:")
    for test in test_texts:
        result = contains_prohibited_url(test, exempt_patterns=all_urls)
        print(f"'{test}' - Contains prohibited URL: {result}")