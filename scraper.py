import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter
from stopwords import stop_words
import json
import nltk
import lxml
from nltk.corpus import words as nltk_words

nltk.download("words")

# Global variables
total_pages = 0

# Set to keep track of visited URLs to detect traps
visited_urls = set()

# Variable to keep track of the longest page
longest_page = {"url": "", "word_count": 0}

# Counter to keep track of word frequencies
word_counter = Counter()

# Counter to keep track of subdomains and their unique page counts
subdomains = Counter()

# Dictionary to keep track of page hashes to detect exact duplicates
page_hashes = set()

# Dictionary to keep track of exact page content hashes to detect exact duplicates
exact_page_hashes = set()

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB


def save_all():
    save_longest_page()
    save_subdomains()
    save_page_hashes()
    save_word_frequencies()
    save_exact_page_hashes()
    save_total_pages()
    dump_report()


def load_all():
    load_longest_page()
    print("loaded longest page")
    load_subdomains()
    print("loaded subdomains")
    load_page_hashes()
    print("loaded page hashes")
    load_visited_urls()
    print("loaded visited urls")
    load_word_frequencies()
    print("loaded word frequencies")
    load_exact_page_hashes()
    load_total_pages()

def save_total_pages():
    with open("cache/total_pages.txt", "w") as f:
        f.write(str(total_pages))

def load_total_pages():
    try:
        with open("cache/total_pages.txt", "r") as f:
            global total_pages
            total_pages = int(f.read().strip())
    except FileNotFoundError:
        pass


def dump_report():
    with open("report.txt", "w") as f:
        f.write(f"Total pages: {get_unique_pages_count()}\n")
        f.write(
            f"Longest page: {longest_page['url']} with {longest_page['word_count']} words\n"
        )
        f.write("Top 50 words:\n")
        for word, count in get_top_50_words():
            f.write(f"{word}: {count}\n")
        f.write("Subdomains in ics.uci.edu:\n")
        for subdomain, count in get_subdomains_info().items():
            f.write(f"{subdomain}: {count}\n")


def save_word_frequencies():
    # Save the entire Counter to a file in JSON format
    with open("cache/word_frequencies.txt", "w") as f:
        json.dump(dict(word_counter), f)


def save_longest_page():
    with open("cache/longest_page.txt", "w") as f:
        json.dump(longest_page, f)


def load_longest_page():
    try:
        with open("cache/longest_page.txt", "r") as f:
            longest_page.update(json.load(f))
    except FileNotFoundError:
        pass


def save_subdomains():
    with open("cache/subdomains.txt", "w") as f:
        json.dump(dict(subdomains), f)


def load_subdomains():
    try:
        with open("cache/subdomains.txt", "r") as f:
            subdomains.update(Counter(json.load(f)))
    except FileNotFoundError:
        pass


def save_page_hashes():
    with open("cache/page_hashes.txt", "w") as f:
        json.dump(list(page_hashes), f)


def load_page_hashes():
    try:
        with open("cache/page_hashes.txt", "r") as f:
            page_hashes.update(set(json.load(f)))
    except FileNotFoundError:
        pass


def load_visited_urls():
    try:
        with open("cache/visited_urls.txt", "r") as f:
            for line in f:
                visited_urls.add(json.loads(line))
    except FileNotFoundError:
        pass

def compute_similarity_hash(text, window_size=3):
    """
    Compute a more robust similarity hash using character-level k-grams
    """
    # Convert to lowercase and remove extra whitespace
    text = " ".join(text.lower().split())

    # Create character-level k-grams
    k_grams = set()
    for i in range(len(text) - window_size + 1):
        k_grams.add(text[i : i + window_size])

    # Create a simple but effective hash
    hash_value = 0
    for gram in k_grams:
        hash_value ^= hash(gram)
    return hash_value

# Replace the existing shingle-related code with:
def are_pages_similar(text1_hash, text2_hash, threshold=0.8):
    """
    Compare two hash values using XOR distance
    Lower values indicate more similarity
    """
    xor_distance = bin(text1_hash ^ text2_hash).count("1")
    max_distance = 64  # Maximum bits in hash
    similarity = 1 - (xor_distance / max_distance)
    return similarity >= threshold


def normalize_url(url):
    """Normalize URL by removing trailing slash"""
    if url.endswith("/"):
        return url[:-1]
    return url


def process_urls(urls):
    """Normalize URLs and remove duplicates"""
    normalized_urls = set()
    for url in urls:
        normalized_urls.add(normalize_url(url))
    return normalized_urls


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links]


def process_page_text(soup):
    """Extract and process text content from the page"""
    text = soup.get_text()
    words = re.findall(r"\w+", text)
    return text, words


def filter_words(words):
    """Filter words to get valid English words"""
    filtered_words = [word.lower() for word in words if word.lower() not in stop_words]
    english_word_set = set(nltk_words.words())
    english_words = [
        word
        for word in filtered_words
        if word.lower() in english_word_set and len(word) > 1
    ]
    return english_words


def update_longest_page(url, english_word_count):
    """Update the longest page if current page has more English words"""
    global longest_page
    if english_word_count > longest_page["word_count"]:
        longest_page = {"url": url, "word_count": english_word_count}


def is_trap_url(url):
    """Check if URL is likely a trap"""
    parsed_url = urlparse(url)
    query_params = parsed_url.query.split("&")
    if len(query_params) > 2:
        return True
    if re.search(
        r"(share=|eventDisplay=|ical=|~cs224|do=|action=|login|logout|register|signup|edit" +
        r"|delete|update|create|backlink|aistats|revisions|format=|export_code|media|upload|search=|from=)",
        url,
        re.IGNORECASE,
    ):
        return True
    return False


def process_link(url, href):
    """Process individual link and return valid URL if any"""
    full_url = urljoin(url, href)
    parsed_url = urlparse(full_url)
    defragmented_url = parsed_url._replace(fragment="").geturl()
    defragmented_url = normalize_url(defragmented_url)
    # Filter out paths with /event(s)/ followed by YYYY-MM-DD format dates or date query parameters
    if (re.search(r'/(events|event)/\d{4}-\d{2}-\d{2}', parsed_url.path) or
        re.search(r'tribe-bar-date=\d{4}-\d{2}-\d{2}', parsed_url.query)):
        return None
    if (
        defragmented_url in visited_urls
        or is_trap_url(defragmented_url)
        or not is_valid(defragmented_url)
    ):
        return None

    visited_urls.add(defragmented_url)
    with open("cache/visited_urls.txt", "a") as f:
        f.write(json.dumps(defragmented_url) + "\n")

    if "ics.uci.edu" in parsed_url.netloc:
        subdomain = parsed_url.scheme + "://" + parsed_url.netloc
        subdomains[subdomain] += 1

    return defragmented_url


def is_large_file(resp):
    content_length = resp.raw_response.headers.get('Content-Length')
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        return True
    return False


def extract_next_links(url, resp):
    """Main function to extract links from a page"""
    if resp.status != 200 or not resp.raw_response.content.strip():
        return []

    total_pages += 1

    if is_large_file(resp):
        print(f"Skipping large file: {url}")
        return []

    soup = BeautifulSoup(resp.raw_response.content, features="lxml")
    text, words = process_page_text(soup)

    english_words = filter_words(words)
    if len(english_words) < 50:
        print(f"Page with little content: {url}")
        return []
    if len(english_words) < len(words) / 4:
        print(f"Page with less than 25% English words (low textual content): {url}")
        return []

    # Check for exact duplicate using hash
    text_hash = hash(text)
    if text_hash in exact_page_hashes:
        print(f"Exact duplicate page detected: {url}")
        return []

    page_hash = compute_similarity_hash(text)
    for existing_hash in page_hashes:
        if are_pages_similar(page_hash, existing_hash):
            print(f"Similar page detected: {url}")
            return []
    page_hashes.add(page_hash)
    word_counter.update(english_words)
    exact_page_hashes.add(text_hash)

    update_longest_page(url, len(english_words))

    links = []
    for a_tag in soup.find_all("a", href=True):
        processed_link = process_link(url, a_tag["href"])
        if processed_link:
            links.append(processed_link)

    save_all()
    return links


def is_valid(url):
    # Decide whether to crawl this URL or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not re.match(
            r".*\.(ics\.uci\.edu|cs\.uci\.edu|informatics\.uci\.edu|stat\.uci\.edu)",
            parsed.netloc,
        ):
            return False
        # print(parsed)
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|sql|conf"
            + r"|png|tiff?|mid|mp2|mp3|mp4|bam"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|war|img|apk|mpg"
            + r"|thmx|mso|arff|rtf|jar|csv|java|h|c|cpp|py|sh|php"
            + r"|html|htm|xml|json|yaml|yml|txt|log|cfg|ini|md"
            + r"|gitignore|gitattributes|gitmodules|gitkeep|git|gitconfig"
            + r"|rmvb|flv|txt|key|odp|ods|odt|pps|ppsx|pptx"
            + r"|xlk|xlsb|xlsm|xlsx|xlt|xltx|xltm|xlw"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower(),
        )

    except TypeError:
        print("TypeError for ", parsed)
        raise


def get_top_50_words():
    return word_counter.most_common(50)


def load_word_frequencies():
    try:
        with open("cache/word_frequencies.txt", "r") as f:
            word_counter.update(json.load(f))
    except FileNotFoundError:
        pass


def get_unique_pages_count():
    return total_pages


def get_subdomains_info():
    sorted_subdomain_info = dict(sorted(subdomains.items()))
    return sorted_subdomain_info


def save_exact_page_hashes():
    with open("cache/exact_page_hashes.txt", "w") as f:
        json.dump(list(exact_page_hashes), f)

def load_exact_page_hashes():
    try:
        with open("cache/exact_page_hashes.txt", "r") as f:
            exact_page_hashes.update(set(json.load(f)))
    except FileNotFoundError:
        pass
