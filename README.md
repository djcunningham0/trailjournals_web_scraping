# trailjournals_web_scraping

TODO: finish README

### `trailjournals_scraping.py` 
Utilities for scraping all of a users journals from trailjournals.com

Example usage:

```python
from trailjournals_scraping import User

user = User("bcunningham")  # all journal entries are scraped here

user.write_all_journals_to_text()  # writes entries to text files nested in the `./data/` directory (directory can be overridden)
```

### `write_google_doc.py`
Write the scraped data into a Google Doc using the Google Docs API

Note: `write_google_doc.py` assumes the existance of a `.env` file that looks like this:
```
TRAILJOURNALS_USERNAME=...
OUTPUT_DIR=...
GOOGLE_DOC_ID=...
GOOGLE_DOC_CREDENTIALS_FILE=...
```
