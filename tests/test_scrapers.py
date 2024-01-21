from bs4 import BeautifulSoup

from trailjournals_scraping import (
    get_images_from_soup,
    format_trailjournals_url,
    soup_to_text
)


TEST_IMAGE_SOUP_1 = """
<p>
  <br>
  <img src="/image1">
</p>
<figcaption>This image has a caption.</figcaption>
<p>This is a paragraph.</p>
<p>
  <br>
  <img src="/image2_no_caption">
</p>
<p>
  <br>
  <img src="/image3">
</p>
<figcaption>This image also has a caption.</figcaption>
"""

TEST_IMAGE_SOUP_2 = """
<table>
  <tbody>
    <tr>
      <td>
        <img src="/image_in_table">
      </td>
    </tr>
  </tbody>
</table>
<p>
  <br>
  <img src="/image1">
</p>
<figcaption>This image has a caption.</figcaption>
<p>This is a paragraph.</p>
<p>
  <br>
  <img src="/image2_no_caption">
</p>
<p>
  <br>
  <img src="/image3">
</p>
<figcaption>This image also has a caption.</figcaption>
"""

TEST_IMAGE_SOUP_3 = """
<table>
  <tbody>
    <tr>
      <td>
        <img src="/image_in_table">
        <br>
        <b>
          <i>
            <font size="-1">now it has a caption</font>
          </i>
        </b>
      </td>
    </tr>
  </tbody>
</table>
<p>
  <br>
  <img src="/image1">
</p>
<figcaption>This image has a caption.</figcaption>
<p>This is a paragraph.</p>
<p>
  <br>
  <img src="/image2_no_caption">
</p>
<p>
  <br>
  <img src="/image3">
</p>
<figcaption>This image also has a caption.</figcaption>
"""


def test_get_images_from_soup():
    images_1 = get_images_from_soup(BeautifulSoup(TEST_IMAGE_SOUP_1, "html.parser"))
    assert [x.url for x in images_1] == [
        format_trailjournals_url(x)
        for x in ["/image1", "/image2_no_caption", "/image3"]
    ]
    assert [x.caption for x in images_1] == [
        "This image has a caption.",
        None,
        "This image also has a caption.",
    ]

    images_2 = get_images_from_soup(BeautifulSoup(TEST_IMAGE_SOUP_2, "html.parser"))
    assert [x.url for x in images_2] == [
        format_trailjournals_url(x)
        for x in ["/image_in_table", "/image1", "/image2_no_caption", "/image3"]
    ]
    assert [x.caption for x in images_2] == [
        None,
        "This image has a caption.",
        None,
        "This image also has a caption.",
    ]

    images_3 = get_images_from_soup(BeautifulSoup(TEST_IMAGE_SOUP_3, "html.parser"))
    assert [x.url for x in images_3] == [
        format_trailjournals_url(x)
        for x in ["/image_in_table", "/image1", "/image2_no_caption", "/image3"]
    ]
    assert [x.caption for x in images_3] == [
        "now it has a caption",
        "This image has a caption.",
        None,
        "This image also has a caption.",
    ]


def test_soup_to_text_all_paragraphs():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\nYet another paragraph."
    )


def test_soup_to_text_with_list():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\n- Item 1"
        "\n\n- Item 2"
        "\n\nYet another paragraph."
    )


def test_soup_to_text_with_list_embedded_paragraphs():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <ul>
            <li>
                <p>Item 1</p>
            </li>
            <li>
                <p>Item 2</p>
            </li>
        </ul>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\n- Item 1"
        "\n\n- Item 2"
        "\n\nYet another paragraph."
    )


def test_soup_to_text_with_numbered_list():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <ol>
            <li>Item 1</li>
            <li>Item 2</li>
        </ol>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\n1. Item 1"
        "\n\n2. Item 2"
        "\n\nYet another paragraph."
    )


def test_soup_to_text_with_numbered_list_embedded_paragraphs():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <ol>
            <li>
                <p>Item 1</p>
            </li>
            <li>
                <p>Item 2</p>
            </li>
        </ol>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\n1. Item 1"
        "\n\n2. Item 2"
        "\n\nYet another paragraph."
    )


def test_soup_to_text_with_extra_tags():
    html_string = """
        <p>A paragraph.</p>
        <p>Another paragraph.</p>
        <asdf>Extra tag</asdf>
        <p>Yet another paragraph.</p>
    """
    soup = BeautifulSoup(html_string, "html.parser")
    assert soup_to_text(soup) == (
        "A paragraph."
        "\n\nAnother paragraph."
        "\n\nYet another paragraph."
    )
