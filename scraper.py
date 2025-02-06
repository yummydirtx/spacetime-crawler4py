import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter
from stopwords import stop_words

# Set to keep track of visited URLs to detect traps
visited_urls = set()

# Variable to keep track of the longest page
longest_page = {
    'url': '',
    'word_count': 0
}

# Counter to keep track of word frequencies
word_counter = Counter()

# Dictionary to keep track of subdomains and their unique page counts
subdomains = {}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status != 200:
        return []
    
    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    text = soup.get_text()
    words = re.findall(r'\w+', text)
    word_count = len(words)
    
    # Filter out stop words
    filtered_words = [word.lower() for word in words if word.lower() not in stop_words]
    word_counter.update(filtered_words)
    

    
    global longest_page
    if word_count > longest_page['word_count']:
        longest_page = {
            'url': url,
            'word_count': word_count
        }
    
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)
        defragmented_url = parsed_url._replace(fragment='').geturl()
        
        # Check for infinite traps by detecting repeated URL patterns
        if defragmented_url in visited_urls:
            continue
        visited_urls.add(defragmented_url)
        
        # Track subdomains
        if 'ics.uci.edu' in parsed_url.netloc:
            subdomain = parsed_url.scheme + '://' + parsed_url.netloc
            if subdomain not in subdomains:
                subdomains[subdomain] = set()
            subdomains[subdomain].add(defragmented_url)
        
        links.append(defragmented_url)
    
    return links

def is_valid(url):
    # Decide whether to crawl this URL or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not re.match(r".*\.(ics\.uci\.edu|cs\.uci\.edu|informatics\.uci\.edu|stat\.uci\.edu)", parsed.netloc):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def get_top_50_words():
    return word_counter.most_common(50)

def get_unique_pages_count():
    return len(visited_urls)

def get_subdomains_info():
    subdomain_info = {subdomain: len(pages) for subdomain, pages in subdomains.items()}
    sorted_subdomain_info = dict(sorted(subdomain_info.items()))
    return sorted_subdomain_info
