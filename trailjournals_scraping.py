import os
import re
import json
import string
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from bs4 import BeautifulSoup
import requests

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from dotenv import load_dotenv
load_dotenv()


USERNAME = os.getenv("TRAILJOURNALS_USERNAME")


class Entry:
    def __init__(self, url: str, journal: "Journal" = None):
        self.journal = journal
        self.url = format_trailjournals_url(url)
        self._soup = get_soup(self.url)
        self.title = self._get_title()
        self.date = self._get_date()
        self.metadata = self._get_metadata()
        self.text = self._get_text()
        self.images = self._get_images()

    def _get_title(self) -> str:
        return self._soup.find("h2", {"class": "entry-title"}).text.strip()

    def _get_date(self) -> str:
        # format is "Saturday, July 08, 2023"
        d = self._soup.find("div", {"class": "entry-date"}).text.strip()
        d = datetime.strptime(d, "%A, %B %d, %Y")
        return self._format_entry_date(d)

    def _get_metadata(self) -> "EntryMetadata":
        metadata_left = self._soup.find_all("div", {"class": "entry-text"})
        metadata_right = self._soup.find_all("div", {"class": "entry-text-right"})

        def extract_metadata(x: List[BeautifulSoup], idx: int) -> str:
            """Extract metadata elements from a post if they exist."""
            try:
                return x[idx].find("span", {"class": "entry-text-detail"}).text.strip()
            except IndexError:
                return ""

        destination = extract_metadata(metadata_left, 0)
        start = extract_metadata(metadata_left, 1)
        miles = extract_metadata(metadata_right, 0)
        trip_miles = extract_metadata(metadata_right, 1)
        return EntryMetadata(
            start=start,
            destination=destination,
            miles=miles,
            trip_miles=trip_miles,
        )

    @staticmethod
    def _format_entry_date(d: datetime) -> str:
        """
        Format the date as, e.g., "Saturday, July 8th, 2023".

        Using a solution found here:
        https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
        """
        def suffix(day: int):
            return {1: "st", 2: "nd", 3: "rd"}.get(day % 20, "th")

        def custom_strftime(fmt: str, d: datetime) -> str:
            return d.strftime(fmt).replace("{S}", f"{d.day}{suffix(d.day)}")

        return custom_strftime("%A, %B {S}, %Y", d)

    def _get_text(self) -> str:
        entry = self._soup.find("div", {"class": "entry"})
        # TODO: should we attempt to put the images in the right places?
        text = [x.text for x in entry.find_all("p")]
        text = [x.replace("\xa0", "") for x in text]  # replace double spaces
        text = [x.replace("\n", " ").strip() for x in text]  # remove in middle of paragraphs
        return "\n\n".join(text).strip()  # combine lists into a single string

    def _get_images(self) -> List["Image"]:
        entry = self._soup.find("div", {"class": "entry"})
        image_urls = [x["src"] for x in entry.find_all("img")]
        logger.debug(f"found {len(image_urls)} images")

        # first (featured) image caption has a <font> tag with size="-1"
        captions = [entry.find("font", {"size": "-1"}).text.strip() or ""]

        # subsequent image captions have <figcaption> tags
        captions += [x.text.strip() for x in entry.find_all("figcaption")]

        # TODO: does this handle images w/o captions? do a better job of accounting for this
        #  - maybe create Image class?

        return [Image(url, caption) for url, caption in zip(image_urls, captions)]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "date": self.date,
            "text": self.text,
            "image_urls": self.images,
            "image_names": [x.split("/")[-1] for x in self.images],
        }

    def to_text(self) -> str:
        return f"{self.title}\n\n{self.date}\n\n{self.text}"

    def write_to_json(self, path: str):
        self._write_entry_to_file(path, "json")

    def write_to_text(self, path: str):
        self._write_entry_to_file(path, "text")

    def _write_entry_to_file(self, path: str, method: str):
        if method not in ["json", "text"]:
            raise ValueError(f"method must be 'json' or 'text', not {method}")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        suffix = ".json" if method == "json" else ".txt"
        if not path.endswith(suffix):
            path = f"{path}{suffix}"

        # remove punctuation and replace spaces with underscores
        file_name = "".join(os.path.basename(path).split(".")[:-1])  # remove file extension
        file_name = replace_spaces_and_dashes(file_name)
        for char in [x for x in string.punctuation if x != "_"]:
            file_name = file_name.replace(char, "")
        file_name = f"{file_name}{suffix}"  # add file extension back
        path = os.path.join(os.path.dirname(path), file_name)

        logger.debug(f"writing entry to {path}")
        if method == "json":
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
        elif method == "text":
            with open(path, "w") as f:
                f.write(self.to_text())

    def download_images(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        for i, image in enumerate(self.images):
            url = image.url
            logger.debug(f"downloading image {i} of {len(self.images)}")
            image_name = url.split("/")[-1]
            path = os.path.join(directory, image_name)
            download_image(url, path)

    def __repr__(self):
        return f"Entry(title={self.title}, date={self.date})"


@dataclass
class Image:
    url: str
    caption: str = None

    def __post_init__(self):
        self.url = format_trailjournals_url(self.url)


@dataclass
class EntryMetadata:
    start: str
    destination: str
    miles: str
    trip_miles: str

    def __bool__(self):
        return any([self.start, self.destination, self.miles, self.trip_miles])


class Journal:
    def __init__(self, url: str, user: "User" = None):
        self.user = user
        self._initial_url = format_trailjournals_url(url)
        # this is the meaningful URL with the list of entries
        self.url = self._initial_url.replace("journal/", "journal/entries/")
        self._soup = get_soup(self.url)
        self.title = self._get_title()
        self.year = self._get_year()
        self.entries = self._get_entries()

    def _get_title(self) -> str:
        title_contents = self._soup.find("h1", {"class": "journal-title"}).contents
        title = " ".join(title_contents[2].split(" ")[:-1]).strip()
        logger.debug(f"found journal title: {title}")
        return title

    def _get_year(self) -> str:
        title_contents = self._soup.find("h1", {"class": "journal-title"}).contents
        year = title_contents[0].split(" ")[-1].strip()
        logger.debug(f"found journal year: {year}")
        return year

    def _get_entries(self) -> List[Entry]:
        logger.info(f"processing entries for {self.title}")
        table = self._soup.find("table")
        entry_urls = [x["href"] for x in table.find_all("a")]
        logger.info(f"found {len(entry_urls)} entries")
        entries = [Entry(x, journal=self) for x in entry_urls]
        return entries

    def write_all_entries_to_json(self, directory: str):
        self._write_all_entries(directory, method="json")

    def write_all_entries_to_text(self, directory: str):
        self._write_all_entries(directory, method="text")

    def _write_all_entries(self, directory: str, method: str):
        logger.info(f"writing {self.title} journal entries ({self.n_entries} total) to {method} in {directory}")
        n_digits = min(2, len(str(self.n_entries)))
        for i, entry in enumerate(self.entries):
            # format the entry number with leading zeros
            entry_number = str(i + 1).zfill(n_digits)
            name = f"{entry_number}_{replace_spaces_and_dashes(entry.title)}"
            path = os.path.join(directory, name)
            entry._write_entry_to_file(path=path, method=method)

    @property
    def n_entries(self) -> int:
        return len(self.entries)

    def __repr__(self):
        return f"Journal(title={self.title}, year={self.year}, n_entries={self.n_entries})"


class User:
    def __init__(self, username: str):
        self.username = username
        self._initial_url = f"https://www.trailjournals.com/{username}"
        self.url = self._get_url()  # this is the meaningful URL with the list of journals
        self._soup = get_soup(self.url)
        self.journals = self._get_journals()

    def _get_url(self):
        """This is the "Other Journals" URL, which is the meaningful URL with the list of journals."""
        soup = get_soup(self._initial_url)
        other_journals = soup.find("li", {"class": "other-journals"})
        url = other_journals.find("a")["href"]
        url = format_trailjournals_url(url)
        logger.debug(f"found other journals URL: {url}")
        return url

    def _get_journals(self) -> List[Journal]:
        journals = self._soup.find_all("div", {"class": "media-body"})
        logger.info(f"found {len(journals)} journals")
        journal_list = []
        for journal in journals:
            journal_url = journal.find("a", {"class": "btn-primary"})["href"]
            journal_list.append(Journal(journal_url, user=self))
        return journal_list[::-1]  # reverse the list so it goes from earliest to latest

    def write_all_journals_to_json(self, directory: str = None):
        if directory is None:
            directory = self._default_directory
        self._write_all_journals(directory=directory, method="json")

    def write_all_journals_to_text(self, directory: str = None):
        if directory is None:
            directory = self._default_directory
        self._write_all_journals(directory=directory, method="text")

    def _write_all_journals(self, directory: str, method: str):
        logger.info(f"writing all journals ({self.n_journals} total) to {method} in {directory}")
        for i, journal in enumerate(self.journals):
            # format the journal number with leading zeros
            dir_name = f"{journal.year}_{replace_spaces_and_dashes(journal.title)}"
            journal_dir = os.path.join(directory, dir_name)
            journal._write_all_entries(directory=journal_dir, method=method)

    @property
    def _default_directory(self) -> str:
        output_dir = os.getenv("OUTPUT_DIR", "./data")
        return os.path.join(output_dir, self.username)

    @property
    def n_journals(self) -> int:
        return len(self.journals)

    @property
    def n_entries(self) -> int:
        return sum([x.n_entries for x in self.journals])

    def __repr__(self):
        return f"User(username={self.username}, n_journals={self.n_journals}, total_entries={self.n_entries})"


def get_soup(url: str, parser: str = "html.parser", **requests_kwargs) -> BeautifulSoup:
    """Make a request to the URL and scrape the HTML."""
    logger.debug(f"scraping {url}")
    r = requests.get(url, **requests_kwargs)
    r.raise_for_status()
    return BeautifulSoup(r.text, parser)


def download_image(image_url: str, path: str):
    logger.debug(f"downloading image from {image_url}")
    r = requests.get(image_url)
    r.raise_for_status()
    image_data = r.content
    logger.debug(f"writing image data to {path}")
    with open(path, "wb") as handler:
        handler.write(image_data)


def format_trailjournals_url(url: str):
    if not url.startswith("https://www.trailjournals.com"):
        if not url.startswith("/"):
            url = f"/{url}"
        url = f"https://www.trailjournals.com{url}"
    return url


def replace_spaces_and_dashes(s: str) -> str:
    s = s.replace(" ", "_").replace("-", "_")
    s = re.sub("_+", "_", s)  # replace repeated underscores with a single underscore
    return s
