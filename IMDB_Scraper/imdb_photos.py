"""
IMDB Photo Downloader
Downloads all photos from an IMDB title's media gallery.

Usage:
    python imdb_photos.py <imdb_url> [output_folder]

Examples:
    python imdb_photos.py https://www.imdb.com/title/tt0111161/
    python imdb_photos.py https://www.imdb.com/title/tt0111161/ "C:/Photos/Shawshank"

Requirements:
    pip install playwright beautifulsoup4 requests
    python -m playwright install chromium
"""

import os
import re
import sys
import time
from pathlib import Path

# When frozen by PyInstaller, Playwright resolves its browser cache relative
# to the ephemeral _MEI extraction folder instead of the normal persistent
# %LOCALAPPDATA%\ms-playwright location. Pin it before importing playwright
# so installed browsers are found across runs.
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"),
)

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def extract_title_id(url: str) -> tuple[str, str]:
    match = re.search(r"(tt|nm)\d+", url)
    if not match:
        raise ValueError(f"Could not find IMDB title or name ID in URL: {url}")
    imdb_id = match.group()
    return imdb_id, "name" if imdb_id.startswith("nm") else "title"


def scrape_media_gallery(title_id: str) -> tuple[str, list[str]]:
    """Use Playwright to render the media gallery and collect all full-res image URLs."""
    image_urls = []
    title_name = title_id

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DOWNLOAD_HEADERS["User-Agent"],
            locale="en-US",
        )
        page = context.new_page()

        # Block unnecessary resources to speed things up
        page.route("**/*.{woff,woff2,ttf,otf}", lambda r: r.abort())

        base = "name" if title_id.startswith("nm") else "title"
        print("Opening IMDB media gallery...")
        page.goto(f"https://www.imdb.com/{base}/{title_id}/mediaindex/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Get title from og:title meta tag
        try:
            og = page.query_selector("meta[property='og:title']")
            if og:
                raw = og.get_attribute("content") or ""
                # "Girl Meets World (TV Series 2014-2017) - Photos - IMDb" -> "Girl Meets World..."
                title_name = raw.split(" - Photos")[0].strip()
        except Exception:
            pass

        # Find total pages
        total_pages = 1
        try:
            page_nums = page.query_selector_all("a.page-link, span.page-link, [class*='page']")
            nums = []
            for el in page_nums:
                try:
                    nums.append(int(el.inner_text().strip()))
                except Exception:
                    pass
            if nums:
                total_pages = max(nums)
        except Exception:
            pass

        print(f"Title : {title_name}")
        print(f"Pages : {total_pages}")

        def collect_images_from_page():
            # Wait for images to load
            page.wait_for_timeout(1500)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            found = []
            # Collect thumbnail src and derive full-res URL
            for img in soup.find_all("img"):
                src = img.get("src", "") or img.get("data-src", "")
                if "media-amazon.com" in src and "_V1_" in src:
                    # Strip size suffix to get full resolution
                    full = re.sub(r"\._V1_.*\.(jpg|jpeg|png)", r"._V1_.\1", src)
                    if full not in found:
                        found.append(full)
            return found

        # Page 1
        urls = collect_images_from_page()
        image_urls.extend(urls)
        print(f"Page 1/{total_pages} — {len(urls)} images")

        # Remaining pages
        for pg in range(2, total_pages + 1):
            page.goto(
                f"https://www.imdb.com/{base}/{title_id}/mediaindex/?page={pg}",
                wait_until="domcontentloaded"
            )
            urls = collect_images_from_page()
            image_urls.extend(urls)
            print(f"Page {pg}/{total_pages} — {len(urls)} images")
            time.sleep(0.5)

        browser.close()

    # Deduplicate
    image_urls = list(dict.fromkeys(image_urls))
    return title_name, image_urls


def download_image(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30, stream=True)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    title_id = extract_title_id(url)

    title_name, image_urls = scrape_media_gallery(title_id)

    print(f"\nTotal unique images found: {len(image_urls)}")

    if not image_urls:
        print("No images found. The page structure may have changed.")
        sys.exit(1)

    # Output folder
    if len(sys.argv) >= 3:
        out_dir = Path(sys.argv[2])
    else:
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", title_name)
        out_dir = Path.cwd() / safe_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving to: {out_dir}\n")

    downloaded = 0
    skipped = 0
    failed = 0

    for i, img_url in enumerate(image_urls, 1):
        # Use a hash of the URL as filename to avoid duplicates
        fname = re.search(r"/(RM\d+|rm\d+|[A-Z0-9_]+)\._V1_", img_url)
        stem = fname.group(1) if fname else f"img_{i:04d}"
        dest = out_dir / f"{stem}.jpg"

        if dest.exists():
            skipped += 1
            print(f"[{i}/{len(image_urls)}] Skip: {dest.name}")
            continue

        ok = download_image(img_url, dest)
        if ok:
            downloaded += 1
            print(f"[{i}/{len(image_urls)}] OK: {dest.name}")
        else:
            failed += 1
            print(f"[{i}/{len(image_urls)}] FAIL: {img_url[:80]}")

        time.sleep(0.2)

    print(f"\nDone. Downloaded: {downloaded}  Skipped: {skipped}  Failed: {failed}")
    print(f"Photos saved to: {out_dir}")


if __name__ == "__main__":
    main()
