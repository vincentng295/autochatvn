import base64
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Global caches for resources
resource_cache_text = {}
resource_cache_binary = {}

def download_file(url):
    """Download a file and return its content as a string, with caching."""
    if url in resource_cache_text:
        return resource_cache_text[url]
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            resource_cache_text[url] = content
            return content
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return None

def download_binary(url):
    """Download a binary resource and return its content, with caching."""
    if url in resource_cache_binary:
        return resource_cache_binary[url]
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content = response.content
            resource_cache_binary[url] = content
            return content
    except Exception as e:
        print(f"Error downloading binary {url}: {e}")
    return None

def download_image_as_base64(url):
    """Download an image and return its Base64 string, with caching."""
    binary_content = download_binary(url)
    if binary_content:
        img_base64 = base64.b64encode(binary_content).decode("utf-8")
        try:
            response = requests.head(url)
            mime_type = response.headers.get("Content-Type", "image/jpeg")
        except Exception:
            mime_type = "image/jpeg"
        return f"data:{mime_type};base64,{img_base64}"
    return None

def download_font_as_base64(url):
    """Download a font file and return its Base64 string."""
    binary_content = download_binary(url)
    if binary_content:
        font_base64 = base64.b64encode(binary_content).decode("utf-8")
        if url.endswith(".woff2"):
            mime_type = "font/woff2"
        elif url.endswith(".woff"):
            mime_type = "font/woff"
        elif url.endswith(".ttf"):
            mime_type = "font/ttf"
        elif url.endswith(".otf"):
            mime_type = "font/otf"
        else:
            mime_type = "application/octet-stream"
        return f"data:{mime_type};base64,{font_base64}"
    return None

def resolve_absolute_url(base_url, resource_url):
    """Convert a relative URL into an absolute URL."""
    return urljoin(base_url, resource_url)

def process_css(content, base_url):
    """
    Converts relative `url(...)` in CSS files to absolute or Base64 URLs,
    and also processes @import statements.
    """
    def replace_url(match):
        original_url = match.group(1).strip("'\"")  # Extract URL
        absolute_url = resolve_absolute_url(base_url, original_url)
        # Check if it's an image or font
        if any(absolute_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]):
            base64_img = download_image_as_base64(absolute_url)
            return f"url('{base64_img}')" if base64_img else f"url('{absolute_url}')"
        elif any(absolute_url.lower().endswith(ext) for ext in [".woff2", ".woff", ".ttf", ".otf"]):
            base64_font = download_font_as_base64(absolute_url)
            return f"url('{base64_font}')" if base64_font else f"url('{absolute_url}')"
        return f"url('{absolute_url}')"

    def replace_import(match):
        import_url = match.group(1).strip("'\"")
        absolute_import_url = resolve_absolute_url(base_url, import_url)
        imported_css = download_file(absolute_import_url)
        if imported_css:
            processed_imported_css = process_css(imported_css, absolute_import_url)
            return processed_imported_css
        return ""

    # Process @import rules first
    content = re.sub(r"@import\s+(?:url\()?['\"]?(.*?)['\"]?\)?\s*;", replace_import, content)
    # Replace all url(...) occurrences
    content = re.sub(r"url\((.*?)\)", replace_url, content)
    return content

def process_inline_style(style_content, base_url):
    """Process inline style attribute content to resolve URLs."""
    def replace_url(match):
        original_url = match.group(1).strip("'\"")
        absolute_url = resolve_absolute_url(base_url, original_url)
        if any(absolute_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]):
            base64_img = download_image_as_base64(absolute_url)
            return f"url('{base64_img}')" if base64_img else f"url('{absolute_url}')"
        elif any(absolute_url.lower().endswith(ext) for ext in [".woff2", ".woff", ".ttf", ".otf"]):
            base64_font = download_font_as_base64(absolute_url)
            return f"url('{base64_font}')" if base64_font else f"url('{absolute_url}')"
        return f"url('{absolute_url}')"
    return re.sub(r"url\((.*?)\)", replace_url, style_content)

def inline_iframe(iframe, base_url):
    """Inline iframe content by downloading the iframe's source and setting it to srcdoc."""
    iframe_src = iframe.get("src")
    if iframe_src:
        absolute_src = resolve_absolute_url(base_url, iframe_src)
        iframe_content = download_file(absolute_src)
        if iframe_content:
            # Parse iframe HTML
            iframe_soup = BeautifulSoup(iframe_content, "html.parser")
            # Remove all script tags in iframe content
            for script in iframe_soup.find_all("script"):
                script.decompose()
            # Process images in iframe
            for img in iframe_soup.find_all("img"):
                img_url = img.get("src")
                if img_url:
                    img_url = resolve_absolute_url(absolute_src, img_url)
                    base64_img = download_image_as_base64(img_url)
                    if base64_img:
                        img["src"] = base64_img
            # Process inline styles in iframe
            for tag in iframe_soup.find_all(style=True):
                original_style = tag.get("style")
                tag["style"] = process_inline_style(original_style, absolute_src)
            # Resolve relative URLs for common tags
            for tag in iframe_soup.find_all(["a", "link", "img"]):
                attr = "href" if tag.name in ["a", "link"] else "src"
                if tag.has_attr(attr):
                    tag[attr] = resolve_absolute_url(absolute_src, tag[attr])
            # Set the processed HTML as srcdoc
            iframe["srcdoc"] = str(iframe_soup)
            del iframe["src"]
        else:
            # If unable to download, just update src to absolute
            iframe["src"] = absolute_src

def remove_event_handlers(soup):
    """Remove inline event handler attributes from all tags."""
    for tag in soup.find_all():
        to_remove = [attr for attr in tag.attrs if attr.lower().startswith("on")]
        for attr in to_remove:
            del tag[attr]

def capture_static_html(driver, output_file: str):
    """
    Captures a fully static HTML version of the currently loaded page in Selenium.

    - Removes all JavaScript (`<script>` elements)
    - Resolves all relative URLs to absolute
    - Inlines external CSS (including @import rules)
    - Fixes `url(...)` in CSS and inline styles to be absolute or Base64
    - Converts images and fonts to Base64
    - Inlines iframe content
    - Processes other media elements (<video>, <audio>, <source>)
    - Removes inline event handlers
    - Saves the final static page as an HTML file.

    :param driver: Selenium WebDriver instance (page should already be loaded)
    :param output_file: The output file name (e.g., "saved_page.html").
    """
    page_url = driver.current_url
    full_html = driver.execute_script("return document.documentElement.outerHTML")
    soup = BeautifulSoup(full_html, "html.parser")

    # Convert all images to Base64
    for img in soup.find_all("img"):
        img_url = img.get("src")
        if img_url:
            img_url = resolve_absolute_url(page_url, img_url)
            base64_img = download_image_as_base64(img_url)
            if base64_img:
                img["src"] = base64_img

    # Inline external CSS and process @import rules
    for link in soup.find_all("link", {"rel": "stylesheet"}):
        css_url = link.get("href")
        if css_url:
            css_url = resolve_absolute_url(page_url, css_url)
            css_content = download_file(css_url)
            if css_content:
                fixed_css = process_css(css_content, css_url)
                style_tag = soup.new_tag("style")
                style_tag.string = fixed_css
                link.replace_with(style_tag)

    # Process <link> tags preloading fonts by inlining them
    for link in soup.find_all("link", {"rel": "preload"}):
        if link.get("as") == "font":
            font_url = link.get("href")
            if font_url:
                font_url = resolve_absolute_url(page_url, font_url)
                base64_font = download_font_as_base64(font_url)
                if base64_font:
                    link["href"] = base64_font

    # Process inline style attributes
    for tag in soup.find_all(style=True):
        original_style = tag.get("style")
        tag["style"] = process_inline_style(original_style, page_url)

    # Process media elements (<video>, <audio>, <source>)
    for tag in soup.find_all(["video", "audio"]):
        if tag.get("src"):
            tag["src"] = resolve_absolute_url(page_url, tag["src"])
        for source in tag.find_all("source"):
            if source.get("src"):
                source["src"] = resolve_absolute_url(page_url, source["src"])

    # Inline iframe content
    for iframe in soup.find_all("iframe"):
        inline_iframe(iframe, page_url)

    # Resolve relative URLs for common tags
    for tag in soup.find_all(["a", "link", "img"]):
        attr = "href" if tag.name in ["a", "link"] else "src"
        if tag.has_attr(attr):
            tag[attr] = resolve_absolute_url(page_url, tag[attr])

    # Remove all JavaScript
    for script in soup.find_all("script"):
        script.decompose()

    # Remove inline event handlers
    remove_event_handlers(soup)

    # Save the modified HTML to a file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(str(soup))

    print(f"Static page saved as {output_file} (No JavaScript, Fixed CSS, Inlined Media)")
