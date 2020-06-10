from bs4 import BeautifulSoup
from readability.readability import Document
from urllib.parse import urlparse
from pdftitle import get_title_from_io as get_title_from_pdf

import tempfile
import requests
import tldextract

from src.common.date_extractor import extract_date
from src.common.utils import write_file, get_file_name_from_url


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36', # noqa
}


class DefaultWebInfoExtractor:
    HTML = 'html'
    PDF = 'pdf'

    def __init__(self, url):
        self.url = url
        self.readable = None
        self.page = None
        self.content = None
        self.type = None

        try:
            head = requests.head(url, headers=HEADERS)
        except requests.exceptions.RequestException:
            return

        try:
            response = requests.get(url, headers=HEADERS, verify=False)
            self.content = response.content
        except requests.exceptions.RequestException:
            return

        if 'text/html' in head.headers.get('content-type', ''):
            self.type = self.HTML
            html = response.text
            self.readable = Document(html)
            self.page = BeautifulSoup(html, 'lxml')
        elif 'application/pdf' in head.headers.get('content-type', ''):
            self.type = self.PDF
            fp = tempfile.NamedTemporaryFile(dir='/tmp/', delete=False)
            write_file(response, fp)
            self.content = fp

    def get_serialized_data(self):
        date = self.get_date()
        country = self.get_country()
        source_raw = self.get_source()
        author_raw = self.get_author()
        website = self.get_website()
        title = self.get_title()

        return {
            'source_raw': source_raw,
            'author_raw': author_raw,
            'title': title,
            'date': date,
            'country': country,
            'website': website,
            'url': self.url,
        }

    def get_title(self):
        if self.type == self.PDF:
            try:
                return get_title_from_pdf(self.content)
            except Exception:
                return get_file_name_from_url(self.url)
        return self.readable and self.readable.short_title()

    def get_date(self):
        return extract_date(self.url, self.page)

    def get_country(self):
        if not self.page:
            return None
        country = self.page.select('.primary-country .country a')
        if country:
            return country[0].text.strip()

        country = self.page.select('.country')
        if country:
            return country[0].text.strip()

        return None

    def get_source(self):
        return tldextract.extract(self.url).domain

    def get_author(self):
        if self.page:
            source = self.page.select('footer .meta .source li')
            if source:
                return source[0].text.strip()

    def get_website(self):
        return urlparse(self.url).netloc

    def get_content(self):
        return self.content
