# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import time

# base_url = "https://drnatro.vn/collections/all?page={}"

# products = []

# headers = {
#     "User-Agent": "Mozilla/5.0"
# }

# for page in range(1, 4):  # chỉ lấy 3 page
#     url = base_url.format(page)
#     print(f"Fetching: {url}")

#     res = requests.get(url, headers=headers)
#     if res.status_code != 200:
#         print("Request failed!")
#         break

#     soup = BeautifulSoup(res.text, "html.parser")

#     # item product (Haravan thường là 1 trong 2 class này)
#     items = soup.select(".product-item, .product-loop")

#     print(f"Found {len(items)} items")

#     for item in items:
#         # ===== LINK =====
#         link_tag = item.select_one("a[href]")
#         link = "https://drnatro.vn" + link_tag["href"] if link_tag else ""

#         # ===== NAME =====
#         name = ""
#         name_tag = item.select_one("h3") or item.select_one(".product-title") or item.select_one(".product-name")

#         if name_tag:
#             name = name_tag.get_text(strip=True)

#         # fallback: lấy từ link
#         if not name and link:
#             name = link.split("/")[-1].replace("-", " ")

#         # ===== PRICE =====
#         price = ""
#         price_tag = (
#             item.select_one(".price")
#             or item.select_one(".product-price")
#             or item.select_one(".price-new")
#         )

#         if price_tag:
#             price = price_tag.get_text(strip=True)

#         products.append({
#             "Name": name,
#             "Price": price,
#             "Link": link
#         })

#     time.sleep(1)

# # ===== EXPORT =====
# df = pd.DataFrame(products)

# # loại dòng rỗng
# df = df[df["Link"] != ""]

# df.to_excel("drnatro_products.xlsx", index=False)

# print(f"Done! Total items: {len(df)}")

import re
import time
import html
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


DOMAIN = "https://drnatro.vn"
COLLECTION_URL = "https://drnatro.vn/collections/all?page={}"
OUTPUT_FILE = "drnatro_full_products.xlsx"

MAX_COLLECTION_PAGES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


session = requests.Session()
session.headers.update(HEADERS)


def clean_text(value: str) -> str:
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_html(value: str) -> str:
    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")
    return clean_text(soup.get_text(" ", strip=True))


def extract_handle(product_url: str) -> str:
    path = urlparse(product_url).path
    return path.rstrip("/").split("/")[-1]


def handle_to_name(handle: str) -> str:
    return clean_text(handle.replace("-", " ").title())


def normalize_price(value):
    """
    Normalize price từ nhiều format:
    - 198000
    - "198000"
    - 19800000 kiểu cents
    - "198,000₫"
    """
    if value is None or value == "":
        return ""

    raw = str(value)

    # Nếu có format VNĐ trong text
    match = re.search(r"\d{1,3}(?:[.,]\d{3})+\s*₫", raw)
    if match:
        return match.group(0).replace(" ", "")

    # Chỉ giữ số
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return ""

    number = int(digits)

    # Shopify-like đôi khi lưu cent: 19800000 -> 198000
    if number >= 1_000_000:
        maybe_vnd = number // 100
        if maybe_vnd >= 10_000:
            number = maybe_vnd

    return f"{number:,}₫"


def request_get(url, timeout=30, retries=3):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 200:
                return response

            last_error = f"HTTP {response.status_code}"
            print(f"⚠️ Attempt {attempt}: {url} -> {last_error}")

        except Exception as ex:
            last_error = str(ex)
            print(f"⚠️ Attempt {attempt}: {url} -> {last_error}")

        time.sleep(1)

    print(f"❌ Failed: {url} | Error: {last_error}")
    return None


def collect_product_links():
    """
    Crawl collection page 1..3 để gom unique product links.
    """
    product_links = []
    seen = set()

    for page in range(1, MAX_COLLECTION_PAGES + 1):
        url = COLLECTION_URL.format(page)
        print(f"\nFetching collection page {page}: {url}")

        response = request_get(url)
        if not response:
            continue

        print(f"Status: {response.status_code}")
        print(f"HTML length: {len(response.text)}")

        # Save debug HTML
        with open(f"debug_collection_page_{page}.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, "html.parser")

        raw_links = soup.select('a[href*="/products/"]')
        print(f"Found raw product links: {len(raw_links)}")

        for a in raw_links:
            href = a.get("href", "")
            if not href or "/products/" not in href:
                continue

            full_link = urljoin(DOMAIN, href.split("?")[0])
            handle = extract_handle(full_link)

            if not handle:
                continue

            # Deduplicate theo handle
            if handle in seen:
                continue

            seen.add(handle)
            product_links.append(full_link)

        print(f"Unique product links so far: {len(product_links)}")
        time.sleep(1)

    return product_links


def parse_json_from_product_js(product_url: str):
    """
    Thử endpoint product JSON:
    /products/{handle}.js

    Nếu site hỗ trợ thì đây là cách sạch nhất.
    """
    handle = extract_handle(product_url)
    json_url = f"{DOMAIN}/products/{handle}.js"

    response = request_get(json_url)
    if not response:
        return None

    try:
        return response.json()
    except Exception:
        return None


def extract_meta_content(soup, selector):
    tag = soup.select_one(selector)
    if tag:
        return clean_text(tag.get("content", ""))
    return ""


def parse_detail_from_html(product_url: str):
    """
    Fallback: parse HTML detail page nếu .js không có data.
    """
    response = request_get(product_url)
    if not response:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    with open(f"debug_product_{extract_handle(product_url)}.html", "w", encoding="utf-8") as f:
        f.write(response.text)

    title = (
        extract_meta_content(soup, 'meta[property="og:title"]')
        or clean_text(soup.select_one("h1").get_text(" ", strip=True)) if soup.select_one("h1") else ""
    )

    description = (
        extract_meta_content(soup, 'meta[property="og:description"]')
        or extract_meta_content(soup, 'meta[name="description"]')
    )

    image = extract_meta_content(soup, 'meta[property="og:image"]')

    price = ""
    price_meta = soup.select_one('meta[property="product:price:amount"]')
    if price_meta:
        price = normalize_price(price_meta.get("content", ""))

    if not price:
        text = clean_text(soup.get_text(" ", strip=True))
        price_match = re.search(r"\d{1,3}(?:[.,]\d{3})+\s*₫", text)
        if price_match:
            price = price_match.group(0).replace(" ", "")

    all_images = []
    for img in soup.select("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue

        src = urljoin(DOMAIN, src)
        if src not in all_images:
            all_images.append(src)

    return {
        "Name": title or handle_to_name(extract_handle(product_url)),
        "Price": price,
        "ComparePrice": "",
        "Description": description,
        "Vendor": "",
        "ProductType": "",
        "Tags": "",
        "Images": "\n".join(all_images),
        "MainImage": image,
        "Variants": "",
        "VariantCount": "",
        "Link": product_url,
        "Source": "html",
    }


def parse_detail_from_json(product_url: str, data: dict):
    """
    Parse product detail từ /products/{handle}.js.
    """
    handle = extract_handle(product_url)

    title = clean_text(data.get("title", "")) or handle_to_name(handle)
    description = strip_html(data.get("description", ""))

    vendor = clean_text(data.get("vendor", ""))
    product_type = clean_text(data.get("type", "") or data.get("product_type", ""))

    tags = data.get("tags", "")
    if isinstance(tags, list):
        tags = ", ".join([clean_text(x) for x in tags])
    else:
        tags = clean_text(tags)

    images = data.get("images", [])
    if isinstance(images, list):
        images_text = "\n".join([urljoin(DOMAIN, str(x)) for x in images])
        main_image = urljoin(DOMAIN, str(images[0])) if images else ""
    else:
        images_text = clean_text(images)
        main_image = images_text.split("\n")[0] if images_text else ""

    variants = data.get("variants", [])
    variant_lines = []

    price = ""
    compare_price = ""

    if variants:
        first_variant = variants[0]

        price = normalize_price(
            first_variant.get("price")
            or first_variant.get("price_min")
            or data.get("price")
        )

        compare_price = normalize_price(
            first_variant.get("compare_at_price")
            or first_variant.get("compare_price")
            or data.get("compare_at_price")
        )

        for variant in variants:
            variant_title = clean_text(variant.get("title", ""))
            variant_price = normalize_price(variant.get("price", ""))
            variant_compare_price = normalize_price(
                variant.get("compare_at_price")
                or variant.get("compare_price")
                or ""
            )
            sku = clean_text(variant.get("sku", ""))
            available = variant.get("available", "")

            variant_lines.append(
                f"Variant: {variant_title} | Price: {variant_price} | "
                f"Compare: {variant_compare_price} | SKU: {sku} | Available: {available}"
            )
    else:
        price = normalize_price(data.get("price", ""))
        compare_price = normalize_price(data.get("compare_at_price", ""))

    return {
        "Name": title,
        "Price": price,
        "ComparePrice": compare_price,
        "Description": description,
        "Vendor": vendor,
        "ProductType": product_type,
        "Tags": tags,
        "Images": images_text,
        "MainImage": main_image,
        "Variants": "\n".join(variant_lines),
        "VariantCount": len(variants) if variants else 0,
        "Link": product_url,
        "Source": "json",
    }


def crawl_product_detail(product_url: str):
    """
    Ưu tiên JSON endpoint.
    Nếu không được thì fallback qua HTML.
    """
    print(f"\nCrawling product detail: {product_url}")

    data = parse_json_from_product_js(product_url)

    if data:
        print("✅ Detail source: JSON")
        return parse_detail_from_json(product_url, data)

    print("⚠️ JSON unavailable, fallback to HTML")
    detail = parse_detail_from_html(product_url)
    detail["Source"] = "html"
    return detail


def main():
    print("======================================")
    print("STEP 1: Collect product links")
    print("======================================")

    product_links = collect_product_links()

    print("\n======================================")
    print(f"Collected unique product links: {len(product_links)}")
    print("======================================")

    if not product_links:
        print("❌ Không tìm thấy product link nào.")
        return

    details = []

    print("\n======================================")
    print("STEP 2: Crawl product detail")
    print("======================================")

    for idx, link in enumerate(product_links, start=1):
        print(f"\n[{idx}/{len(product_links)}]")
        detail = crawl_product_detail(link)
        if detail:
            details.append(detail)

        time.sleep(1)

    if not details:
        print("❌ Không crawl được detail sản phẩm nào.")
        return

    df = pd.DataFrame(details)

    columns = [
        "Name",
        "Price",
        "ComparePrice",
        "Description",
        "Vendor",
        "ProductType",
        "Tags",
        "MainImage",
        "Images",
        "Variants",
        "VariantCount",
        "Link",
        "Source",
    ]

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    df = df[columns]

    df.to_excel(OUTPUT_FILE, index=False)

    print("\n======================================")
    print(f"✅ Done! Total product details: {len(df)}")
    print(f"✅ Exported file: {OUTPUT_FILE}")
    print("======================================")


if __name__ == "__main__":
    main()