import logging
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests

log = logging.getLogger(__name__)


class Client:
    """Conservative single-threaded transport; failures are never bypassed."""
    def __init__(self, config):
        self.session = requests.Session()
        self.agent = config.get("user_agent", "MAPDIS-Research/0.1")
        self.session.headers["User-Agent"] = self.agent
        self.interval = config.get("request_interval_seconds", 1)
        self.last = {}
        self.robots = {}

    def get(self, url, **kwargs):
        # Redirects are checked explicitly so another host cannot evade policy.
        for _ in range(6):
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username:
                raise ValueError("Only credential-free HTTPS URLs are supported")
            host = parts.netloc
            delay = max(0, self.interval - (time.monotonic() - self.last.get(host, 0)))
            time.sleep(delay)
            response = self.session.get(url, timeout=30, allow_redirects=False, **kwargs)
            self.last[host] = time.monotonic()
            if response.is_redirect:
                from urllib.parse import urljoin
                url = urljoin(url, response.headers["Location"])
                kwargs.pop("params", None)
                if not self.allowed(url):
                    raise PermissionError("Redirect denied by robots policy")
                continue
            response.raise_for_status()  # Includes 429; do not retry anti-bot errors.
            return response
        raise requests.TooManyRedirects(url)

    def allowed(self, url):
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.robots:
            parser = RobotFileParser()
            try:
                # Fetch robots without following redirects; ambiguous policies fail closed.
                time.sleep(self.interval)
                r = self.session.get(origin + "/robots.txt", timeout=30, allow_redirects=False)
                self.last[parts.netloc] = time.monotonic()
                if r.status_code == 404:
                    parser.parse([])
                else:
                    r.raise_for_status()
                    if r.is_redirect or "text/html" in r.headers.get("Content-Type", ""):
                        raise ValueError("Unusable robots policy")
                    parser.parse(r.text.splitlines())
                self.robots[origin] = parser
            except (requests.RequestException, ValueError):
                log.warning("Unable to verify robots policy for %s", origin)
                self.robots[origin] = None
        parser = self.robots[origin]
        if parser is None:
            return False
        delay = parser.crawl_delay(self.agent) or parser.crawl_delay("*")
        rate = parser.request_rate(self.agent) or parser.request_rate("*")
        self.interval = max(self.interval, delay or 0, rate.seconds / rate.requests if rate else 0)
        return parser.can_fetch(self.agent, url)
