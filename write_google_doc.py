import os
from typing import List

from googleapiclient.discovery import build
from google.oauth2 import service_account

from trailjournals_scraping import User

from dotenv import load_dotenv
load_dotenv()

DOCUMENT_ID = os.getenv("GOOGLE_DOC_ID")
TRAILJOURNALS_USERNAME = os.getenv("TRAILJOURNALS_USERNAME")

SECTION_BREAK = {"insertSectionBreak": {"location": {"index": 1}, "sectionType": "NEXT_PAGE"}}
PAGE_BREAK = {"insertSectionBreak": {"location": {"index": 1}, "sectionType": "NEXT_PAGE"}}

user = User(TRAILJOURNALS_USERNAME)


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


def insert_text_with_style(
        text: str,
        named_style: str = "NORMAL_TEXT",
        alignment: str = "START",  # "START", "CENTER", "END", "JUSTIFIED"
        start: int = 1,
) -> List[dict]:
    """
    Usage:
    ```
    request_list += [
        ...,  # other requests
        *insert_text_with_style("asdf", style="NORMAL_TEXT"),
    ]
    ```
    """
    out = []
    if alignment:
        out.append(format_paragraph_alignment(alignment, start=start, end=start + len(text)))
    if named_style:
        out.append(format_named_style_type(named_style, start=start, end=start + len(text)))
    out.append({"insertText": {"location": {"index": start}, "text": text}})
    return out

request_list = []
# request_list += [
#     *insert_text_with_style(f"Trailjournals for {user.username}", "TITLE"),
#     # format_named_style_type("TITLE"),
#     # {"insertText": {"location": {"index": 1}, "text": user_title}},
# ]
for i, journal in enumerate(user.journals[:1]):  # TODO: all journals
    if i > 0:
        request_list.append(SECTION_BREAK)
    request_list += insert_text_with_style(journal.title, named_style="HEADING_1", alignment="CENTER")
    for entry in journal.entries:
        request_list += [
            PAGE_BREAK,
            *insert_text_with_style(entry.title, named_style="HEADING_2", alignment="CENTER"),
            *insert_text_with_style("\n", alignment="CENTER"),
            *insert_text_with_style(entry.date, named_style="NORMAL_TEXT", alignment="CENTER"),
        ]
        has_metadata = any([entry.metadata.start, entry.metadata.destination, entry.metadata.miles, entry.metadata.trip_miles])
        if has_metadata:
            # not really sure how the index values are supposed to work, but it seems you add 2 to go to the next
            # column, add 5 to go to the next row
            request_list += insert_text_with_style(f"Start: {entry.metadata.start}", alignment="CENTER", start=5)
            request_list += insert_text_with_style(f"Miles: {entry.metadata.miles}", alignment="CENTER", start=7)
            request_list += insert_text_with_style(f"Destination: {entry.metadata.destination}", alignment="CENTER", start=10)
            request_list += insert_text_with_style(f"Trip miles: {entry.metadata.trip_miles}", alignment="CENTER", start=12)

            no_border = {
                "width": {"magnitude": 0, "unit": "PT"},
                "dashStyle": "SOLID",
                "color": {"color": {"rgbColor": {"red": 0, "green": 0, "blue": 0}}}
            }
            no_padding = {
                "magnitude": 0,
                "unit": "PT",
            }
            no_border_all = {x: no_border for x in ["borderBottom", "borderLeft", "borderRight", "borderTop"]}
            no_padding_all = {x: no_padding for x in ["paddingBottom", "paddingLeft", "paddingRight", "paddingTop"]}
            request_list += [
                {
                    "updateTableCellStyle": {
                        "fields": "borderBottom,borderLeft,borderRight,borderTop,"
                                  "paddingBottom,paddingLeft,paddingRight,paddingTop,"
                                  "contentAlignment",
                        "tableStartLocation": {
                            "index": 2,
                        },
                        "tableCellStyle": {
                            **no_border_all,
                            **no_padding_all,
                            "contentAlignment": "MIDDLE",
                        },
                    },
                },
                {
                    'updateTableColumnProperties': {
                        'tableStartLocation': {'index': 2},
                        'columnIndices': [],
                        'tableColumnProperties': {
                            'widthType': 'FIXED_WIDTH',
                            'width': {
                                'magnitude': 200,
                                'unit': 'PT'
                            }
                        },
                        'fields': '*'
                    },
                },
                {
                    "insertTable": {
                        "location": {
                            "index": 1,
                        },
                        "columns": 2,
                        "rows": 2,
                    }
                },
            ]

        request_list += [
            *insert_text_with_style("\n" if has_metadata else "\n\n"),
            *insert_text_with_style(entry.text),
        ]

# following the best practices of the API, i.e., writing backwards so the formatting works correctly
request_list = request_list[::-1]

creds_file = os.getenv("GOOGLE_DOC_CREDENTIALS_FILE")
credentials = service_account.Credentials.from_service_account_file(creds_file)

with build("docs", "v1", credentials=credentials) as service:
    # Retrieve the documents contents from the Docs service.
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    print(f"The title of the document is: {document.get('title')}")
    result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': request_list}).execute()
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
