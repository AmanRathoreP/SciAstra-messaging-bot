import re

def contains_prohibited_url(text, exempt_patterns=None):
    if exempt_patterns is None:
        exempt_patterns = []
    
    text = text.replace(' ', '').replace('\n', '').replace('\t', '')

    url_pattern = re.compile(
        r'((?:(?:https?://)|(?:www\.)|(?:[a-zA-Z0-9-]+\.[a-zA-Z]{2,}))\S*)', 
        re.IGNORECASE
    )
    matches = url_pattern.findall(text)

    for match in matches:
        url = re.sub(r'\s+', '', match)

        # If URL starts with "www.", add a default protocol "http://"
        if url.lower().startswith("www."):
            url = "http://" + url

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

    test_text = "Visit github.com for more info."
    print("Contains prohibited URL:", contains_prohibited_url(test_text, exempt_patterns=all_urls))
