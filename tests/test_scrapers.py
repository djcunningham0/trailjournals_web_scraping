from bs4 import BeautifulSoup

from trailjournals_scraping import get_images_from_soup, format_trailjournals_url


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
