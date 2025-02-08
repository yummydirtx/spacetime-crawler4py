from configparser import ConfigParser
from argparse import ArgumentParser
import os

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler


def main(config_file, restart):
    if restart:
        if os.path.exists("report.txt"):
            os.remove("report.txt")
        if os.path.exists("page_hashes.txt"):
            os.remove("page_hashes.txt")
        if os.path.exists("subdomains.txt"):
            os.remove("subdomains.txt")
        if os.path.exists("longest_page.txt"):
            os.remove("longest_page.txt")
        if os.path.exists("visited_urls.txt"):
            os.remove("visited_urls.txt")
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
