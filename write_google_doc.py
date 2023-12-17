import os
from typing import List

from googleapiclient.discovery import build
from google.oauth2 import service_account

from trailjournals_scraping import User, Entry, Image

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.getLevelName(os.getenv("LOGLEVEL", "WARNING")))
logging.getLogger("trailjournals_scraping").setLevel(logging.getLevelName(os.getenv("LOGLEVEL", "WARNING")))

DOCUMENT_ID = os.getenv("GOOGLE_DOC_ID")
TRAILJOURNALS_USERNAME = os.getenv("TRAILJOURNALS_USERNAME")

user = User(TRAILJOURNALS_USERNAME)

DEFAULT_IMAGE_HEIGHT = 360
DEFAULT_IMAGE_WIDTH = 360

SECTION_BREAK = {"insertSectionBreak": {"location": {"index": 1}, "sectionType": "NEXT_PAGE"}}
PAGE_BREAK = {"insertSectionBreak": {"location": {"index": 1}, "sectionType": "NEXT_PAGE"}}


def cell_border(
        width: float = 0,
        unit: str = "PT",
        dash_style: str = "SOLID",
        red: int = 0,
        green: int = 0,
        blue: int = 0,
) -> dict:
    return {
        "width": {"magnitude": width, "unit": unit.upper()},
        "dashStyle": dash_style.upper(),
        "color": {"color": {"rgbColor": {"red": red / 256, "green": green / 256, "blue": blue / 256}}}
    }


def cell_padding(amount: float = 0, unit: str = "PT") -> dict:
    return {
        "magnitude": amount,
        "unit": unit.upper(),
    }


def apply_border(top: float = 0, bottom: float = 0, left: float = 0, right: float = 0, **kwargs) -> dict:
    return {
        "borderTop": cell_border(width=top, **kwargs),
        "borderBottom": cell_border(width=bottom, **kwargs),
        "borderLeft": cell_border(width=left, **kwargs),
        "borderRight": cell_border(width=right, **kwargs),
    }


def apply_padding(top: float = 0, bottom: float = 0, left: float = 0, right: float = 0, **kwargs) -> dict:
    return {
        "paddingTop": cell_padding(amount=top, **kwargs),
        "paddingBottom": cell_padding(amount=bottom, **kwargs),
        "paddingLeft": cell_padding(amount=left, **kwargs),
        "paddingRight": cell_padding(amount=right, **kwargs),
    }


def format_named_style_type(style_type: str, start: int = 1, end: int = 1) -> dict:
    return {
        "updateParagraphStyle": {
            "fields": "namedStyleType",
            "range": {"startIndex": start, "endIndex": end},
            "paragraphStyle": {"namedStyleType": style_type.upper()}
        }
    }


def format_paragraph_alignment(alignment: str, start: int = 1, end: int = 1) -> dict:
    return {
        "updateParagraphStyle": {
            "fields": "alignment",
            "range": {"startIndex": start, "endIndex": end},
            "paragraphStyle": {"alignment": alignment.upper()}
        }
    }


def format_text_italic(start: int = 1, end: int = 1) -> dict:
    return {
        "updateTextStyle": {
            "fields": "italic",
            "range": {"startIndex": start, "endIndex": end},
            "textStyle": {"italic": True}
        }
    }


def insert_text_with_style(
        text: str,
        named_style: str = "NORMAL_TEXT",
        alignment: str = "START",  # "START", "CENTER", "END", "JUSTIFIED"
        italic: bool = False,
        start: int = 1,
) -> List[dict]:
    """
    Usage:
    ```
    request_list += [
        ...,  # other requests
        *insert_text_with_style("asdf", named_style="NORMAL_TEXT"),
    ]
    ```
    """
    out = []
    if alignment:
        out.append(format_paragraph_alignment(alignment, start=start, end=start + len(text)))
    if italic:
        out.append(format_text_italic(start=start, end=start + len(text)))
    if named_style:
        out.append(format_named_style_type(named_style, start=start, end=start + len(text)))
    out.append({"insertText": {"location": {"index": start}, "text": text}})
    return out


def insert_hr(
        width: float = 0.5,
        top_or_bottom: str = "bottom",
        red: int = 102,
        green: int = 102,
        blue: int = 102,
) -> List[dict]:
    if top_or_bottom not in ("top", "bottom"):
        raise ValueError(f"top_or_bottom must be 'top' or 'bottom', not {top_or_bottom}")
    top = width if top_or_bottom == "top" else 0
    bottom = width if top_or_bottom == "bottom" else 0
    return [
        {
            "updateTableCellStyle": {
                "fields": "borderBottom,borderLeft,borderRight,borderTop,"
                          "paddingBottom,paddingLeft,paddingRight,paddingTop",
                "tableStartLocation": {
                    "index": 2,
                },
                "tableCellStyle": {
                    **apply_padding(),
                    **apply_border(top=top, bottom=bottom, red=red, green=green, blue=blue),
                },
            },
        },
        {"insertTable": {"location": {"index": 1}, "columns": 1, "rows": 1}},
    ]


def process_entry_metadata(entry: Entry) -> List[dict]:
    return [
        # not really sure how the index values are supposed to work with tables, but it
        # seems you add 2 to go to the next column, add 5 to go to the next row
        *insert_text_with_style(
            text=f"Start: {entry.metadata.start}",
            named_style="SUBTITLE",
            alignment="START",
            start=5
        ),
        *insert_text_with_style(
            text=f"Miles: {entry.metadata.miles}",
            named_style="SUBTITLE",
            alignment="END",
            start=7
        ),
        *insert_text_with_style(
            text=f"Destination: {entry.metadata.destination}",
            named_style="SUBTITLE",
            alignment="START",
            start=10
        ),
        *insert_text_with_style(
            text=f"Trip miles: {entry.metadata.trip_miles}",
            named_style="SUBTITLE",
            alignment="END",
            start=12
        ),
        {
            "updateTableCellStyle": {
                "fields": "borderBottom,borderLeft,borderRight,borderTop,"
                          "paddingBottom,paddingLeft,paddingRight,paddingTop,"
                          "contentAlignment",
                "tableStartLocation": {
                    "index": 2,
                },
                "tableCellStyle": {
                    **apply_border(),
                    **apply_padding(),
                    "contentAlignment": "MIDDLE",
                },
            },
        },
        {
            "updateTableColumnProperties": {
                "tableStartLocation": {"index": 2},
                "columnIndices": [1],
                "tableColumnProperties": {
                    "widthType": "FIXED_WIDTH",
                    "width": {
                        "magnitude": 110,
                        "unit": "PT"
                    }
                },
                "fields": "*"
            },
        },
        {
            "updateTableColumnProperties": {
                "tableStartLocation": {"index": 2},
                "columnIndices": [0],
                "tableColumnProperties": {
                    "widthType": "FIXED_WIDTH",
                    "width": {
                        "magnitude": 280,
                        "unit": "PT"
                    }
                },
                "fields": "*"
            },
        },
        {"insertTable": {"location": {"index": 1}, "columns": 2, "rows": 2}},
        format_paragraph_alignment("CENTER", start=1, end=1),
        *insert_hr(top_or_bottom="top"),
    ]


def insert_image(
        image: Image,
        height: int = DEFAULT_IMAGE_HEIGHT,
        width: int = DEFAULT_IMAGE_WIDTH,
) -> List[dict]:
    out = [
        format_paragraph_alignment("CENTER"),
        {
            "insertInlineImage": {
                "location": {"index": 1},
                "uri": image.url,
                "objectSize": {
                    "height": {"magnitude": height, "unit": "PT"},
                    "width": {"magnitude": width, "unit": "PT"},
                },
            }
        },
    ]
    if image.caption:
        out += [
            *insert_text_with_style("\n"),
            *insert_text_with_style(image.caption, named_style="SUBTITLE", alignment="CENTER", italic=True),
        ]
    out += insert_text_with_style("\n\n")
    return out


request_list = []
# request_list += [
#     *insert_text_with_style(f"Trailjournals for {user.username}", "TITLE"),
#     # format_named_style_type("TITLE"),
#     # {"insertText": {"location": {"index": 1}, "text": user_title}},
# ]
for i, journal in enumerate(user.journals):
    if i > 0:
        request_list.append(SECTION_BREAK)
    request_list += insert_text_with_style(journal.title, named_style="HEADING_1", alignment="CENTER")
    for entry in journal.entries:
        request_list += [
            PAGE_BREAK,
            *insert_text_with_style(entry.title, named_style="HEADING_2", alignment="CENTER"),
            *insert_text_with_style("\n", alignment="CENTER"),
            *insert_text_with_style(entry.date, named_style="SUBTITLE", alignment="CENTER"),
            *insert_hr(),
        ]
        has_metadata = any([entry.metadata.start, entry.metadata.destination, entry.metadata.miles, entry.metadata.trip_miles])
        if has_metadata:
            request_list += process_entry_metadata(entry)
        else:
            request_list += insert_text_with_style("\n")

        # put the first image before the content
        if entry.images:
            request_list += insert_image(entry.images[0])
        else:
            request_list += insert_text_with_style("\n")

        # entry content
        request_list += [*insert_text_with_style(entry.text, alignment="JUSTIFIED")]

        # put the rest of the images after the content
        for image in entry.images[1:]:
            request_list += insert_text_with_style("\n\n")
            request_list += insert_image(image)

# following the best practices of the API, i.e., writing backwards so the formatting works correctly
request_list = request_list[::-1]

creds_file = os.getenv("GOOGLE_DOC_CREDENTIALS_FILE")
credentials = service_account.Credentials.from_service_account_file(creds_file)

with build("docs", "v1", credentials=credentials) as service:
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    logger.info(f"Loaded document: {document.get('title')}")
    logger.info(f"Processing {len(request_list)} requests")
    result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={"requests": request_list}).execute()
