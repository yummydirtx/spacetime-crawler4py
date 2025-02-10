from configparser import ConfigParser
from argparse import ArgumentParser
import os

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

# Main function to start the crawler
def main(config_file, restart):
    # If restart flag is set, remove existing report and data files
    if restart:
        if os.path.exists("report.txt"):
            os.remove("report.txt")
        if os.path.exists("cache/page_hashes.txt"):
            os.remove("cache/page_hashes.txt")
        if os.path.exists("cache/subdomains.txt"):
            os.remove("cache/subdomains.txt")
        if os.path.exists("cache/longest_page.txt"):
            os.remove("cache/longest_page.txt")
        if os.path.exists("cache/visited_urls.txt"):
            os.remove("cache/visited_urls.txt")
        if os.path.exists("cache/word_frequencies.txt"):
            os.remove("cache/word_frequencies.txt")
    # Read configuration from the config file
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    # Get cache server based on the configuration
    config.cache_server = get_cache_server(config, restart)
    # Initialize and start the crawler
    crawler = Crawler(config, restart)
    crawler.start()

# Entry point of the script
if __name__ == "__main__":
    # Parse command line arguments
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    # Call the main function with parsed arguments
    main(args.config_file, args.restart)
