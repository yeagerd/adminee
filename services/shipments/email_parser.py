"""
Email parser for shipments service.

This module parses shipping notification emails from various carriers
to extract tracking information, order numbers, and delivery details.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from services.common.logging_config import get_logger
from services.shipments.utils import normalize_tracking_number

logger = get_logger(__name__)


@dataclass
class ParsedEmailData:
    """Represents parsed data from a shipping notification email."""

    carrier: str
    tracking_number: str
    order_number: Optional[str] = None
    tracking_link: Optional[str] = None
    recipient_name: Optional[str] = None
    estimated_delivery: Optional[str] = None
    vendor_name: Optional[str] = None
    package_description: Optional[str] = None
    status: Optional[str] = None
    vendor_url: Optional[str] = None
    is_valid_tracking: bool = True
    confidence_score: float = 0.0
    # Additional fields for shipment detection
    is_shipment_email: bool = False
    detected_carrier: Optional[str] = None
    tracking_numbers: Optional[List[str]] = None
    confidence: float = 0.0
    detected_from: str = "unknown"
    suggested_package_data: Optional[Dict] = None


class EmailParser:
    """Parser for shipping notification emails from various carriers."""

    def __init__(self):
        """Initialize the email parser with carrier patterns."""
        self.carrier_patterns = self._build_carrier_patterns()
        self.tracking_patterns = self._build_tracking_patterns()

    def _convert_to_markdown(self, content: str) -> str:
        """
        Convert email content to clean text using robust MIME decoding.

        This implements a more robust strategy for handling email content:
        1. Proper MIME parsing with correct charset and encoding handling
        2. Quoted-printable decoding using quopri.decodestring()
        3. HTML entity decoding with html.unescape()
        4. Comprehensive URL extraction from both HTML and plain text
        5. Pollution-free HTML normalization

        Args:
            content: Raw email content (HTML or plain text)

        Returns:
            Clean text suitable for parsing
        """
        if not content:
            return ""

        try:
            import base64
            import email
            import html
            import quopri
            from email import policy

            from bs4 import BeautifulSoup
        except ImportError as e:
            logger.warning(f"Required imports not available: {e}")
            return self._clean_non_mime_content(content)

        def decode_payload(part):
            """Decode email part payload with proper charset and encoding handling."""
            content_type = part.get_content_type()
            content_transfer_encoding = part.get(
                "Content-Transfer-Encoding", ""
            ).lower()
            payload = part.get_payload(decode=False)

            if part.get_content_charset() is None:
                charset = "utf-8"
            else:
                charset = part.get_content_charset()

            if content_transfer_encoding == "base64":
                payload = base64.b64decode(payload)
            elif content_transfer_encoding == "quoted-printable":
                payload = quopri.decodestring(payload)
            elif isinstance(payload, str):
                payload = payload.encode(charset, errors="ignore")

            try:
                return payload.decode(charset, errors="replace"), content_type
            except Exception:
                return payload.decode("utf-8", errors="replace"), content_type

        def extract_urls_from_html(html_content: str) -> List[str]:
            """Extract URLs from HTML content with proper decoding."""
            try:
                # Preprocess HTML to fix common malformed HTML issues
                html_content = self._preprocess_html_content(html_content)
                soup = BeautifulSoup(html_content, "html.parser")
                hrefs = []
                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    if href and isinstance(href, str):
                        hrefs.append(href)

                # Remove HTML tags, decode HTML entities
                raw_text = soup.get_text(separator=" ")
                raw_text = html.unescape(raw_text)

                # Merge quoted-printable-style line breaks
                raw_text = re.sub(r"=\r?\n", "", raw_text)

                # Match inline URLs
                inline_urls = re.findall(r'https?://[^\s"\'<>]+', raw_text)

                # Clean trailing punctuation
                inline_urls = [url.rstrip(".,;:)") for url in inline_urls]

                return list(set(hrefs + inline_urls))  # De-duplicate
            except Exception as e:
                logger.warning(f"HTML URL extraction failed: {e}")
                return []

        # Step 1: MIME Parser with robust decoding
        try:
            # Use Python's email parser to handle all MIME encoding
            msg = email.message_from_string(content, policy=policy.default)

            # Extract content from all parts
            html_content = None
            text_content = None
            all_urls = []

            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == "text/html" and html_content is None:
                    decoded_body, _ = decode_payload(part)
                    html_content = decoded_body
                    all_urls.extend(extract_urls_from_html(decoded_body))

                elif content_type == "text/plain" and text_content is None:
                    decoded_body, _ = decode_payload(part)
                    text_content = decoded_body

                    # Clean QP line breaks and extract URLs from plain text
                    decoded_body = re.sub(r"=\r?\n", "", decoded_body)
                    decoded_body = html.unescape(decoded_body)

                    inline_urls = re.findall(r'https?://[^\s"\'<>]+', decoded_body)
                    inline_urls = [url.rstrip(".,;:)") for url in inline_urls]
                    all_urls.extend(inline_urls)

            # Prefer HTML content, fall back to text
            if html_content:
                content = html_content
                logger.debug(f"Using HTML content (length: {len(content)})")
            elif text_content:
                content = text_content
                logger.debug(f"Using plain text content (length: {len(content)})")
            else:
                # Fall back to original content if no parts found
                logger.debug("No MIME parts found, using original content")
                content = self._clean_non_mime_content(content)

        except Exception as e:
            # If email parsing fails, fall back to original content
            logger.warning(
                f"Python `email` parsing failed, using original content: {e}"
            )
            content = self._clean_non_mime_content(content)

        # Step 2: HTML Cleaner - Remove style/script/meta/link
        if "<" in content and ">" in content:
            content = self._pollution_free_html_normalization(content)

        # Step 3: Final cleanup
        content = self._final_text_cleanup(content)

        return content

    def _preprocess_html_content(self, html_content: str) -> str:
        """
        Preprocess HTML content to fix common malformed HTML issues before parsing.

        This handles:
        - Malformed conditional comments (Outlook, etc.)
        - Invalid HTML entities
        - Broken tag sequences
        - Encoding issues
        """
        if not html_content:
            return ""

        # Fix malformed conditional comments
        # Pattern: <![[=...endif]--> should be <!--[if ...]-->
        html_content = re.sub(r"<!\[\[=([^]]*)\]-->", r"<!--[if \1]-->", html_content)

        # Fix other malformed conditional comments
        html_content = re.sub(r"<!\[\[([^]]*)\]-->", r"<!--[\1]-->", html_content)

        # Fix malformed HTML comments that start with <![
        html_content = re.sub(r"<!\[([^>]*)\]>", r"<!--[\1]-->", html_content)

        # Remove completely broken conditional comments
        html_content = re.sub(r"<!\[[^>]*\]>", "", html_content)

        # Fix common HTML entity issues
        html_content = re.sub(r"&([^a-zA-Z0-9#])", r"&amp;\1", html_content)

        # Fix broken tag sequences like <div s (incomplete tag)
        html_content = re.sub(
            r"<([a-zA-Z]+)\s+([^>]*?)(?=\s*[<>])", r"<\1 \2>", html_content
        )

        # Remove any remaining malformed tags that don't close properly
        html_content = re.sub(r"<([a-zA-Z]+)\s*$", "", html_content)

        # Fix common encoding issues
        html_content = html_content.replace("=\r\n", "")
        html_content = html_content.replace("=\n", "")

        return html_content

    def _pollution_free_html_normalization(self, html_content: str) -> str:
        """
        Pollution-free HTML normalization layer.

        This removes layout-only or style-only content before converting to text,
        while preserving critical shipping information.
        """
        try:
            from bs4 import BeautifulSoup

            # Preprocess HTML to fix common malformed HTML issues
            html_content = self._preprocess_html_content(html_content)

            # Parse HTML with BeautifulSoup - use more lenient parser for malformed HTML
            try:
                soup = BeautifulSoup(html_content, "html.parser")
            except Exception as e:
                logger.warning(f"HTML parser failed, trying lxml: {e}")
                try:
                    soup = BeautifulSoup(html_content, "lxml")
                except Exception as e2:
                    logger.warning(f"lxml parser also failed: {e2}")
                    # Fall back to basic text extraction
                    return self._basic_html_to_text(html_content)

            # Step 1: Remove layout-only elements that cause content pollution
            for tag in soup(["style", "script", "noscript", "meta", "link", "head"]):
                tag.decompose()

            # Step 2: Remove class attributes and other styling noise
            for tag in soup.find_all(True):
                # Remove class, style, and other presentation attributes
                for attr in [
                    "class",
                    "style",
                    "id",
                    "onclick",
                    "onload",
                    "onmouseover",
                ]:
                    if tag.has_attr(attr):
                        tag.attrs.pop(attr, None)

            # Step 3: Special handling for Amazon URLs - preserve them before text conversion
            amazon_urls = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "amazon.com" in href and any(
                    keyword in href
                    for keyword in [
                        "progress-tracker",
                        "order-details",
                        "track",
                        "ship",
                    ]
                ):
                    amazon_urls.append(href)
                    # Replace the link text with the full URL to preserve it
                    link.string = href

            # Step 3: Targeted table extraction (most shipping data appears in tables)
            tables = soup.find_all("table")
            table_content = []

            for table in tables:
                # Use heuristics to find tables containing tracking/order info
                table_text = table.get_text().lower()
                keywords = [
                    "tracking",
                    "order",
                    "item",
                    "ship",
                    "carrier",
                    "delivery",
                    "package",
                ]

                if any(keyword in table_text for keyword in keywords):
                    # Convert table to structured format
                    table_dict = self._extract_table_data(table)
                    if table_dict:
                        table_content.append(table_dict)

            # Step 4: Extract critical info before text conversion
            critical_info = self._extract_critical_info(soup)

            # Step 5: Convert to text while preserving critical information
            text_content = self._simple_html_to_text(soup, critical_info)

            # Step 6: Restore critical information that might have been lost
            text_content = self._restore_critical_info(text_content, critical_info)

            # Step 7: Add table content as structured text
            if table_content:
                table_text = self._format_table_content(table_content)
                text_content = table_text + "\n\n" + text_content

            return text_content

        except Exception as e:
            logger.error(f"HTML normalization failed: {e}")
            # Fall back to basic text extraction
            return self._basic_html_to_text(html_content)

    def _extract_table_data(self, table) -> Optional[dict]:
        """
        Extract structured data from a table that likely contains shipping information.
        """
        try:
            table_data = {}
            rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    # Look for key-value pairs
                    key_cell = cells[0].get_text().strip().lower()
                    value_cell = cells[1].get_text().strip()

                    # Map common shipping-related keys
                    if any(keyword in key_cell for keyword in ["tracking", "track"]):
                        table_data["tracking_number"] = value_cell
                    elif any(
                        keyword in key_cell
                        for keyword in ["order", "order #", "order number"]
                    ):
                        table_data["order_number"] = value_cell
                    elif any(
                        keyword in key_cell
                        for keyword in ["carrier", "shipping", "delivery"]
                    ):
                        table_data["carrier"] = value_cell
                    elif any(
                        keyword in key_cell
                        for keyword in ["item", "product", "description"]
                    ):
                        table_data["package_description"] = value_cell
                    elif any(
                        keyword in key_cell
                        for keyword in ["recipient", "deliver to", "ship to"]
                    ):
                        table_data["recipient_name"] = value_cell
                    elif any(
                        keyword in key_cell
                        for keyword in ["delivery", "estimated", "arrival"]
                    ):
                        table_data["estimated_delivery"] = value_cell

            return table_data if table_data else None

        except Exception as e:
            logger.warning(f"Table data extraction failed: {e}")
            return None

    def _format_table_content(self, table_content: list) -> str:
        """
        Format extracted table data as readable text.
        """
        formatted_lines = []
        for table_data in table_content:
            for key, value in table_data.items():
                if value:
                    formatted_lines.append(f"{key.replace('_', ' ').title()}: {value}")

        return "\n".join(formatted_lines)

    def _basic_html_to_text(self, html_content: str) -> str:
        """
        Basic HTML to text conversion as fallback.
        """
        try:
            from bs4 import BeautifulSoup

            # Preprocess HTML to fix common malformed HTML issues
            html_content = self._preprocess_html_content(html_content)

            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text()
        except Exception as e:
            logger.warning(f"Basic HTML to text conversion failed: {e}")
            # Remove HTML tags manually
            import re

            return re.sub(r"<[^>]+>", "", html_content)

    def _final_text_cleanup(self, content: str) -> str:
        """
        Final cleanup of text content.
        """
        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content)
        # Remove empty lines
        content = re.sub(r"\n\s*\n", "\n", content)
        # Remove leading/trailing whitespace
        content = content.strip()

        # Additional quoted-printable cleanup for any remaining artifacts
        content = re.sub(
            r"(\S+)\s*\|\s*\|\s*\1", r"\1", content
        )  # Remove "text | |text" patterns
        content = re.sub(
            r"(\S+)\s*\|\s*\1", r"\1", content
        )  # Remove "text |text" patterns

        # Remove Unicode control characters and encoding artifacts
        content = re.sub(r"[­\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", content)

        # Clean up any remaining quoted-printable artifacts
        content = re.sub(r"=20", " ", content)  # Space
        content = re.sub(r"=0A", "\n", content)  # Line feed
        content = re.sub(r"=0D", "\r", content)  # Carriage return
        content = re.sub(r"=3D", "=", content)  # Equals sign

        return content

    def _hybrid_html_to_text(self, html_content: str) -> str:
        """
        Convert HTML to text using a hybrid approach that preserves critical content.

        This method implements a pollution-free HTML normalization layer that:
        1. Removes layout-only elements that cause content pollution
        2. Extracts tables for targeted processing
        3. Applies context-aware regex extraction
        """
        try:
            from bs4 import BeautifulSoup

            # Preprocess HTML to fix common malformed HTML issues
            html_content = self._preprocess_html_content(html_content)

            # Parse HTML with BeautifulSoup - use more lenient parser for malformed HTML
            try:
                soup = BeautifulSoup(html_content, "html.parser")
            except Exception as e:
                logger.warning(f"HTML parser failed, trying lxml: {e}")
                try:
                    soup = BeautifulSoup(html_content, "lxml")
                except Exception as e2:
                    logger.warning(f"LXML parser also failed: {e2}")
                    # Fall back to regex-based extraction
                    critical_info = self._extract_critical_info_from_text(html_content)
                    return self._simple_html_to_text_fallback(
                        html_content, critical_info
                    )

            # Step 1: Pollution-Free HTML Normalization
            # Remove layout-only elements that cause content pollution
            for tag in soup(["style", "script", "noscript", "meta", "link", "head"]):
                tag.decompose()

            # Remove class and style attributes that contain layout noise
            for tag in soup.find_all(True):
                if hasattr(tag, "attrs"):
                    if "class" in tag.attrs:
                        del tag.attrs["class"]
                    if "style" in tag.attrs:
                        del tag.attrs["style"]
                    if "id" in tag.attrs and tag.attrs["id"].startswith(
                        ("css", "js", "style")
                    ):
                        del tag.attrs["id"]

            # Step 2: Targeted Table Extraction
            tables = soup.find_all("table")
            table_content = []

            for table in tables:
                # Check if table contains shipping-related keywords
                table_text = table.get_text().lower()
                shipping_keywords = [
                    "tracking",
                    "order",
                    "item",
                    "ship",
                    "carrier",
                    "delivery",
                    "package",
                    "shipping",
                ]

                if any(keyword in table_text for keyword in shipping_keywords):
                    # Convert table to structured format
                    table_rows = []
                    for row in table.find_all("tr"):
                        cells = [
                            cell.get_text(strip=True)
                            for cell in row.find_all(["td", "th"])
                        ]
                        if cells:  # Only add non-empty rows
                            table_rows.append(" | ".join(cells))

                    if table_rows:
                        table_content.append("\n".join(table_rows))
                        logger.debug(
                            f"Found shipping-related table with {len(table_rows)} rows"
                        )

            # Step 3: Extract remaining text content
            # Get text from non-table elements
            for tag in soup.find_all(["table"]):
                tag.decompose()  # Remove tables since we processed them separately

            remaining_text = soup.get_text()

            # Step 4: Combine table content with remaining text
            combined_content = "\n\n".join(table_content + [remaining_text])

            # Step 5: Apply context-aware regex extraction
            # Only apply regex to blocks containing shipping keywords
            anchor_keywords = [
                "tracking",
                "order",
                "item",
                "shipping",
                "delivery",
                "package",
                "carrier",
            ]

            # Split into paragraphs and filter
            paragraphs = combined_content.split("\n\n")
            relevant_paragraphs = []

            for para in paragraphs:
                para_lower = para.lower()
                if any(keyword in para_lower for keyword in anchor_keywords):
                    relevant_paragraphs.append(para)
                elif (
                    len(para.strip()) > 50
                ):  # Keep longer paragraphs that might contain data
                    relevant_paragraphs.append(para)

            final_content = "\n\n".join(relevant_paragraphs)

            # Clean up the final content
            final_content = re.sub(
                r"\n\s*\n", "\n\n", final_content
            )  # Remove excessive newlines
            final_content = re.sub(
                r"[ \t]+", " ", final_content
            )  # Normalize whitespace
            final_content = final_content.strip()

            logger.debug(f"Normalized HTML content length: {len(final_content)}")
            return final_content

        except ImportError:
            logger.warning(
                "BeautifulSoup not available, falling back to HTML tag removal"
            )
            # Fallback: just strip HTML tags
            return re.sub(r"<[^>]+>", "", html_content)

    def _extract_critical_info(self, soup) -> dict:
        """Extract critical information from HTML before conversion."""
        critical_info = {
            "order_numbers": [],
            "tracking_numbers": [],
            "urls": [],
            "product_descriptions": [],
            "recipient_names": [],
        }

        try:
            # Get all text content
            text_content = soup.get_text()
        except Exception as e:
            # If BeautifulSoup fails, try to get text content from the original HTML string
            logger.warning(f"BeautifulSoup get_text() failed: {e}")
            try:
                text_content = str(soup)
            except Exception:
                text_content = ""

        # If we still don't have good text content, fall back to regex-based extraction
        if not text_content or len(text_content) < 100:
            logger.debug(
                "BeautifulSoup text extraction failed, using fallback regex extraction"
            )
            return self._extract_critical_info_from_text(str(soup))

        # Extract order numbers from various patterns - be more specific
        order_patterns = [
            r"order.*#\s*([A-Z0-9\-]{8,20})",
            r"order.*number.*:?\s*([A-Z0-9\-]{8,20})",
            r"#([0-9]{3}-[0-9]{7}-[0-9]{7})",  # Amazon order format
            r"Order\s*#\s*([A-Z0-9\-]{8,20})",
        ]

        # Extract tracking numbers - be much more specific and context-aware
        tracking_patterns = [
            r"shipmentId=3D([A-Za-z0-9]{8,30})",  # Amazon shipment ID with 3D prefix
            r"shipmentId=([A-Za-z0-9]{8,30})",  # Amazon shipment ID pattern
            r"tracking.*number.*:?\s*([0-9A-Z]{8,30})",
            r"track.*:?\s*([0-9A-Z]{8,30})",
            r"Tracking.*ID.*:?\s*([0-9A-Z]{8,30})",
            # Only extract generic patterns if they're in a shipping context
            r"(?=.*(?:tracking|shipment|delivery|package))([0-9A-Z]{8,30})",
        ]

        # Use robust URL extraction that handles QP encoding, HTML tags, etc.
        urls = self._extract_urls_robustly(str(soup))
        critical_info["urls"].extend(urls)

        # Extract product descriptions - be more restrictive
        product_patterns = [
            r"([A-Za-z\s&|]{10,80}(?:\s*[-–]\s*[A-Za-z\s&|]{5,40})*)",  # Product names with separators, longer minimum
        ]

        # Extract recipient names - be more specific
        recipient_patterns = [
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)",  # Proper case First Last format
            r"Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",  # "Dear First Last" format
        ]

        # Extract patterns from text with better filtering
        for pattern in order_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # Additional filtering for order numbers
                if (
                    len(match) >= 8
                    and not self._is_common_false_positive(match)
                    and not re.search(r"[=&\?]", match)
                    and not re.match(r"^[0-9]{1,4}$", match)
                ):  # Don't accept very short numbers
                    critical_info["order_numbers"].append(match)

        for pattern in tracking_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # Handle Amazon tracking numbers with 3D prefix
                if pattern.startswith(r"shipmentId=3D"):
                    # This is an Amazon shipment ID with 3D prefix
                    tracking_number = f"3D{match}"
                else:
                    tracking_number = match

                # Much stricter filtering for tracking numbers
                if (
                    len(tracking_number) >= 8
                    and not self._is_common_false_positive(tracking_number)
                    and not re.search(r"[=&\?]", tracking_number)
                    and not re.match(
                        r"^[0-9]{1,6}$", tracking_number
                    )  # Don't accept very short numbers
                    and not re.match(
                        r"^[a-z]+$", tracking_number.lower()
                    )  # Don't accept all lowercase words
                    and not re.match(
                        r"^[A-Z]+$", tracking_number
                    )  # Don't accept all uppercase words
                    and re.search(r"[0-9]", tracking_number)
                ):  # Must contain at least one digit
                    critical_info["tracking_numbers"].append(tracking_number)

        # URLs are now extracted using the robust method above

        # Special handling for Amazon URLs - they often get truncated during HTML conversion
        if "amazon.com" in text_content:
            # The robust URL extraction above should already handle Amazon URLs
            # But let's also try to reconstruct any truncated ones we find
            amazon_urls = [url for url in critical_info["urls"] if "amazon.com" in url]
            for url in amazon_urls:
                reconstructed_url = self._reconstruct_amazon_url(url)
                if (
                    reconstructed_url != url
                    and reconstructed_url not in critical_info["urls"]
                ):
                    critical_info["urls"].append(reconstructed_url)

        for pattern in product_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # Much stricter filtering for product descriptions
                if (
                    10 <= len(match) <= 100
                    and not self._is_common_false_positive(match)
                    and not re.match(
                        r"^[a-z\s]+$", match.lower()
                    )  # Don't accept all lowercase
                    and not re.match(r"^[A-Z\s]+$", match)  # Don't accept all uppercase
                    and re.search(
                        r"[A-Z]", match
                    )  # Must contain at least one uppercase letter
                    and not any(
                        word in match.lower()
                        for word in [
                            "style",
                            "class",
                            "div",
                            "span",
                            "table",
                            "row",
                            "column",
                        ]
                    )
                ):
                    critical_info["product_descriptions"].append(match)

        for pattern in recipient_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # Stricter filtering for recipient names
                if (
                    len(match.split()) == 2  # Must be exactly two words
                    and not self._is_common_false_positive(match)
                    and not any(
                        word in match.lower()
                        for word in [
                            "style",
                            "class",
                            "div",
                            "span",
                            "table",
                            "row",
                            "column",
                            "content",
                            "header",
                            "footer",
                        ]
                    )
                ):
                    critical_info["recipient_names"].append(match)

        # Remove duplicates while preserving order
        for key in critical_info:
            seen = set()
            unique_items = []
            for item in critical_info[key]:
                if item not in seen:
                    seen.add(item)
                    unique_items.append(item)
            critical_info[key] = unique_items

        return critical_info

    def _reconstruct_amazon_url(self, url: str) -> str:
        """
        Reconstruct truncated Amazon URLs by fixing common truncation issues.
        """
        if not url or "amazon.com" not in url:
            return url

        # Fix common truncation patterns
        reconstructed_url = url

        # Fix "ncoding=UTF8" -> "pro&_encoding=UTF8" (missing "pro")
        if "ncoding=UTF8" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "ncoding=UTF8", "pro&_encoding=UTF8"
            )

        # Fix "gress-tracker" -> "progress-tracker" (missing "pro")
        if "gress-tracker" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "gress-tracker", "progress-tracker"
            )

        # Fix "proprogress-tracker" -> "progress-tracker" (double "pro")
        if "proprogress-tracker" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "proprogress-tracker", "progress-tracker"
            )

        # Fix "pro&_encoding=UTF8" -> "progress-tracker/package?_encoding=UTF8" (missing "gress-tracker/package?")
        if (
            "pro&_encoding=UTF8" in reconstructed_url
            and "progress-tracker" not in reconstructed_url
        ):
            reconstructed_url = reconstructed_url.replace(
                "pro&_encoding=UTF8", "progress-tracker/package?_encoding=UTF8"
            )

        # Fix "_epro&_encoding=UTF8" -> "progress-tracker/package?_encoding=UTF8" (missing "progress-tracker/package?")
        if "_epro&_encoding=UTF8" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "_epro&_encoding=UTF8", "progress-tracker/package?_encoding=UTF8"
            )
        # Fix "_epro&_encoding" -> "_encoding" (extra "pro")
        elif "_epro&_encoding" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "_epro&_encoding", "_encoding"
            )

        # Fix "pro&_encoding=UTF8" -> "progress-tracker/package?_encoding=UTF8" (missing "gress-tracker/package?")
        if (
            "pro&_encoding=UTF8" in reconstructed_url
            and "progress-tracker" not in reconstructed_url
        ):
            reconstructed_url = reconstructed_url.replace(
                "pro&_encoding=UTF8", "progress-tracker/package?_encoding=UTF8"
            )

        # Fix "der-details" -> "order-details" (missing "or")
        if "der-details" in reconstructed_url:
            reconstructed_url = reconstructed_url.replace(
                "der-details", "order-details"
            )

        # Fix "css/order-details" -> "gp/css/order-details" (missing "gp/")
        if (
            "/css/order-details" in reconstructed_url
            and "gp/css/order-details" not in reconstructed_url
        ):
            reconstructed_url = reconstructed_url.replace(
                "/css/order-details", "/gp/css/order-details"
            )

        # Fix "your-account" -> "gp/your-account" (missing "gp/")
        if (
            "/your-account" in reconstructed_url
            and "gp/your-account" not in reconstructed_url
        ):
            reconstructed_url = reconstructed_url.replace(
                "/your-account", "/gp/your-account"
            )

        # Ensure proper URL structure for progress-tracker URLs
        if (
            "progress-tracker" in reconstructed_url
            and "package?" not in reconstructed_url
        ):
            # Add common Amazon progress-tracker parameters if missing
            if "?" not in reconstructed_url:
                reconstructed_url += "?"
            if "package" not in reconstructed_url:
                reconstructed_url += "package"

        return reconstructed_url

    def _restore_critical_info(self, text: str, critical_info: dict) -> str:
        """Restore critical information that might have been lost during conversion."""
        restored_text = text

        # Restore order numbers if they're missing
        for order_num in critical_info["order_numbers"]:
            if order_num not in restored_text:
                # Add order number if it's not present
                restored_text += f"\nOrder # {order_num}"

        # Restore tracking numbers if they're missing
        for tracking_num in critical_info["tracking_numbers"]:
            if tracking_num not in restored_text:
                # Add tracking number if it's not present
                restored_text += f"\nTracking: {tracking_num}"
                logger.debug(f"Restored tracking number: {tracking_num}")

        # Restore URLs if they're missing or corrupted
        for url in critical_info["urls"]:
            if "progress-tracker" in url and url not in restored_text:
                # Check if URL is URL-encoded in the text
                encoded_url = (
                    url.replace("/", "%2F")
                    .replace("?", "%3F")
                    .replace("=", "%3D")
                    .replace("&", "%26")
                )
                if encoded_url in restored_text:
                    # Replace encoded URL with readable version
                    restored_text = restored_text.replace(encoded_url, url)

        # Restore product descriptions if they're missing
        for product in critical_info["product_descriptions"]:
            if product not in restored_text and len(product) > 10:
                # Add product description if it's not present
                restored_text += f"\nProduct: {product}"

        return restored_text

    def _simple_html_to_text(self, soup, critical_info: dict) -> str:
        """Simple HTML to text conversion that preserves more content."""
        # Remove problematic elements but keep more content
        for element in soup(["script", "style", "meta", "link", "head"]):
            element.decompose()

        # Get text content with better preservation
        text = soup.get_text(separator=" ", strip=True)

        # Clean up the text more carefully
        # Remove excessive whitespace but preserve structure
        text = re.sub(r"[ \t]+", " ", text)  # Normalize horizontal whitespace
        text = re.sub(
            r"\n\s*\n\s*\n+", "\n\n", text
        )  # Remove excessive newlines but keep some structure

        # Remove Unicode control characters that markdownify adds
        text = re.sub(
            r"[\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u2064\u206a-\u206f]",
            "",
            text,
        )
        text = re.sub(r"\xad", "", text)  # Remove soft hyphens

        # Restore critical information
        text = self._restore_critical_info(text, critical_info)

        return text.strip()

    def _extract_critical_info_from_text(self, text_content: str) -> dict:
        """Extract critical information from text content when HTML parsing fails."""
        critical_info = {
            "order_numbers": [],
            "tracking_numbers": [],
            "urls": [],
            "product_descriptions": [],
            "recipient_names": [],
        }

        # Extract order numbers from various patterns
        order_patterns = [
            r"order.*#\s*([A-Z0-9\-]+)",
            r"order.*number.*:?\s*([A-Z0-9\-]+)",
            r"#([0-9]{3}-[0-9]{7}-[0-9]{7})",  # Amazon order format
        ]

        # Extract tracking numbers - more specific patterns
        tracking_patterns = [
            r"shipmentId=([A-Za-z0-9]{8,30})",  # Amazon shipment ID pattern
            r"tracking.*number.*:?\s*([0-9A-Z]{8,30})",
            r"track.*:?\s*([0-9A-Z]{8,30})",
            r"([0-9A-Z]{8,30})",  # Generic tracking number pattern (last resort)
        ]

        # Extract URLs
        url_patterns = [
            r'https?://[^\s<>"]+',
        ]

        # Extract product descriptions
        product_patterns = [
            r"([A-Za-z\s&|]+(?:\s*[-–]\s*[A-Za-z\s&|]+)*)",  # Product names with separators
        ]

        # Extract recipient names
        recipient_patterns = [
            r"([A-Za-z]+\s+[A-Za-z]+)",  # First Last format
        ]

        # Extract patterns from text
        for pattern in order_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            critical_info["order_numbers"].extend(matches)

        for pattern in tracking_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            # Filter out common false positives
            for match in matches:
                if not self._is_common_false_positive(match):
                    critical_info["tracking_numbers"].append(match)

        for pattern in url_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            critical_info["urls"].extend(matches)

        for pattern in product_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            # Filter out very short or very long matches
            for match in matches:
                if 5 <= len(match) <= 100:
                    critical_info["product_descriptions"].append(match)

        for pattern in recipient_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            critical_info["recipient_names"].extend(matches)

        # Remove duplicates while preserving order
        for key in critical_info:
            seen = set()
            unique_items = []
            for item in critical_info[key]:
                if item not in seen:
                    seen.add(item)
                    unique_items.append(item)
            critical_info[key] = unique_items

        return critical_info

    def _simple_html_to_text_fallback(
        self, html_content: str, critical_info: dict
    ) -> str:
        """Simple HTML to text conversion when BeautifulSoup fails."""
        # Remove HTML tags
        text = re.sub(r"<[^>]*>", " ", html_content)

        # Clean up the text
        text = re.sub(r"\s+", " ", text)  # Normalize whitespace
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Remove excessive newlines

        # Remove Unicode control characters
        text = re.sub(
            r"[\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u2064\u206a-\u206f]",
            "",
            text,
        )
        text = re.sub(r"\xad", "", text)  # Remove soft hyphens

        # Restore critical information
        text = self._restore_critical_info(text, critical_info)

        return text.strip()

    def _clean_non_mime_content(self, content: str) -> str:
        """
        Clean non-MIME content (simple text, quoted-printable, etc.).
        This is used as a fallback when email parsing fails or no HTML is found.
        """
        # Decode quoted-printable encoding
        content = re.sub(
            r"=([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), content
        )
        content = re.sub(r"=\n", "", content)  # Remove line continuations
        content = re.sub(r"=3D", "=", content)  # Common encoding for equals sign
        content = re.sub(r"=20", " ", content)  # Common encoding for space
        content = re.sub(r"=0A", "\n", content)  # Common encoding for newline
        content = re.sub(r"=0D", "\r", content)  # Common encoding for carriage return

        # Remove email headers and boundaries
        content = re.sub(r"------=_Part_\d+_\d+\.\d+.*?\n", "", content)
        content = re.sub(r"Content-Type:.*?\n", "", content)
        content = re.sub(r"Content-Transfer-Encoding:.*?\n", "", content)
        content = re.sub(r"charset=.*?\n", "", content)

        # Remove base64 encoded content
        content = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[IMAGE]", content)
        content = re.sub(r"[A-Za-z0-9+/]{50,}={0,2}", "[ENCODED_DATA]", content)

        # Remove HTML entities
        content = re.sub(r"&nbsp;", " ", content)
        content = re.sub(r"&zwnj;", "", content)
        content = re.sub(r"&zwj;", "", content)
        content = re.sub(r"&amp;", "&", content)
        content = re.sub(r"&lt;", "<", content)
        content = re.sub(r"&gt;", ">", content)
        content = re.sub(r"&quot;", '"', content)
        content = re.sub(r"&#39;", "'", content)

        # Remove broken HTML entities (with spaces)
        content = re.sub(r"&\s*nbsp;", " ", content)
        content = re.sub(r"&\s*zwnj;", "", content)
        content = re.sub(r"&\s*zwj;", "", content)
        content = re.sub(r"&\s*amp;", "&", content)
        content = re.sub(r"&\s*lt;", "<", content)
        content = re.sub(r"&\s*gt;", ">", content)
        content = re.sub(r"&\s*quot;", '"', content)
        content = re.sub(r"&\s*#39;", "'", content)

        # Remove HTML comments
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

        # Remove CSS blocks (but be more careful)
        content = re.sub(
            r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE
        )

        # Remove email headers and metadata
        content = re.sub(r"x-[a-zA-Z-]+[^\\n]*", "", content, flags=re.IGNORECASE)
        content = re.sub(
            r"[a-zA-Z-]+-[a-zA-Z-]+[^\\n]*", "", content
        )  # Generic header patterns

        return content

    def _build_carrier_patterns(self) -> Dict[str, Dict]:
        """Build patterns for detecting carriers from email content."""
        return {
            "AMAZON": {
                "sender_patterns": [
                    r"shipment-tracking@amazon\.com",
                    r"delivery-updates@amazon\.com",
                    r".*@amazon\.com",
                    r"bugs\.bunny@amazon\.com",  # Specific test email
                ],
                "subject_patterns": [
                    r"amazon.*ship",
                    r"your.*order.*ship",
                    r"amazon.*package",
                    r"your.*package.*ship",
                    r"shipped.*amazon",
                    r"delivered.*amazon",
                    r"shipped:.*",  # Amazon shipping subject pattern
                    r"delivered:.*",  # Amazon delivery subject pattern
                    r"ordered:.*",  # Amazon order confirmation pattern
                ],
                "body_patterns": [
                    r"amazon\.com",
                    r"your.*amazon.*order",
                    r"amazon.*order.*#",
                    r"amazon\.com/progress-tracker",
                    r"progress-tracker",
                    r"order-details",
                ],
            },
            "UPS": {
                "sender_patterns": [
                    r"noreply@ups\.com",
                    r"ups@notifications\.ups\.com",
                    r".*@ups\.com",
                ],
                "subject_patterns": [
                    r"ups.*ship",
                    r"track.*ups",
                    r"ups.*track",
                    r"ups.*delivery",
                    r"ups.*package",
                ],
                "body_patterns": [
                    r"ups.*ground",
                    r"ups.*express",
                    r"ups.*2nd.*day",
                    r"ups.*next.*day",
                    r"ups\.com",
                ],
            },
            "FEDEX": {
                "sender_patterns": [
                    r"fedex@fedex\.com",
                    r"notifications@fedex\.com",
                    r".*@fedex\.com",
                ],
                "subject_patterns": [
                    r"fedex.*ship",
                    r"track.*fedex",
                    r"fedex.*track",
                    r"fedex.*delivery",
                    r"fedex.*package",
                ],
                "body_patterns": [
                    r"fedex.*home.*delivery",
                    r"fedex.*express",
                    r"fedex.*ground",
                    r"fedex.*saver",
                    r"fedex\.com",
                ],
            },
            "USPS": {
                "sender_patterns": [
                    r"USPS@usps\.com",
                    r"noreply@usps\.com",
                    r".*@usps\.com",
                ],
                "subject_patterns": [
                    r"usps.*ship",
                    r"postal.*track",
                    r"usps.*track",
                    r"usps.*delivery",
                    r"usps.*package",
                ],
                "body_patterns": [
                    r"usps.*priority.*mail",
                    r"usps.*first.*class",
                    r"usps.*ground",
                    r"usps.*express",
                    r"usps\.com",
                ],
            },
            "DHL": {
                "sender_patterns": [r"dhl@dhl\.com", r".*@dhl\.com"],
                "subject_patterns": [
                    r"dhl.*ship",
                    r"dhl.*track",
                    r"dhl.*delivery",
                    r"dhl.*package",
                ],
                "body_patterns": [
                    r"dhl.*express",
                    r"dhl.*ground",
                    r"dhl.*worldwide",
                    r"dhl\.com",
                ],
            },
        }

    def _build_tracking_patterns(self) -> Dict[str, str]:
        """Build regex patterns for tracking numbers by carrier."""
        return {
            "UPS": r"1Z[0-9A-Z]{16}|[0-9]{24,26}",  # 1Z + 16 chars OR 24-26 digits
            "FEDEX": r"\b[0-9]{12}\b",  # 12 digits
            "USPS": r"\b[0-9]{18,22}\b",  # 18-22 digits
            "DHL": r"\b[0-9]{10}\b",  # 10 digits
            "ONTRAC": r"\bC[0-9]{15}\b",  # C + 15 digits
            "GENERIC": r"\b[0-9A-Z]{8,30}\b",  # Generic pattern for unknown carriers
        }

    def parse_email(
        self,
        subject: str,
        sender: str,
        body: str,
        email_date: Optional[str] = None,
    ) -> ParsedEmailData:
        """
        Parse a shipping notification email using template fingerprinting.

        This implements the expert strategy of vendor-specific parsing for high-volume vendors.
        Compatible with both Gmail and Microsoft Graph APIs.

        Args:
            subject: Email subject line
            sender: Sender email address
            body: Email body text
            email_date: Email date (optional)

        Returns:
            ParsedEmailData object with extracted information
        """
        try:
            # Step 1: Template fingerprinting - use vendor-specific parsing for high-volume vendors
            vendor_url = self._extract_vendor_from_email(sender)

            # Check if we have a template for this vendor
            if vendor_url == "amazon.com":
                parsed_data = self._parse_amazon_shipping_email(
                    subject, sender, body, email_date
                )
            else:
                # Step 2: Generic parsing for unknown vendors
                parsed_data = self._parse_generic_shipping_email(
                    subject, sender, body, email_date
                )

            # Step 3: Add shipment detection fields
            parsed_data = self._add_shipment_detection_fields(
                parsed_data, subject, sender, body
            )

            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return ParsedEmailData(
                carrier="UNKNOWN",
                tracking_number="",
                vendor_name=None,
                is_valid_tracking=False,
                confidence_score=0.0,
                is_shipment_email=False,
                confidence=0.0,
                detected_from="unknown",
            )

    def _add_shipment_detection_fields(
        self, parsed_data: ParsedEmailData, subject: str, sender: str, body: str
    ) -> ParsedEmailData:
        """
        Add shipment detection fields to the parsed data.
        """
        # Initialize detection fields
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        body_lower = body.lower()

        # Initialize result object
        result = parsed_data
        result.detected_carrier = result.carrier
        result.tracking_numbers = (
            [result.tracking_number] if result.tracking_number else []
        )
        result.confidence = result.confidence_score
        result.is_shipment_email = False
        result.detected_from = "unknown"
        result.suggested_package_data = None

        # Check sender domain
        detected_carrier = self._detect_carrier_from_sender(sender_lower)
        if detected_carrier:
            result.detected_carrier = detected_carrier
            result.is_shipment_email = True
            result.confidence += 0.4
            result.detected_from = "sender"

        # Check subject line
        subject_has_keywords = self._has_shipment_keywords(subject_lower)
        if subject_has_keywords:
            result.is_shipment_email = True
            result.confidence += 0.3
            if result.detected_from == "sender":
                result.detected_from = "subject"
            else:
                result.detected_from = "multiple"

        # Check body
        body_has_keywords = self._has_shipment_keywords(body_lower)
        if body_has_keywords:
            result.is_shipment_email = True
            result.confidence += 0.2
            if result.detected_from == "sender":
                result.detected_from = "body"
            else:
                result.detected_from = "multiple"

        # Extract tracking numbers
        all_text = f"{subject} {body}"
        tracking_numbers = self._extract_tracking_numbers(all_text, detected_carrier)
        if tracking_numbers:
            result.tracking_numbers = tracking_numbers

        # If no carrier detected from sender but we have tracking numbers, try to detect from tracking number
        if not detected_carrier and tracking_numbers:
            detected_carrier = self._detect_carrier_from_tracking_number(
                tracking_numbers[0], body
            )
            if detected_carrier:
                result.detected_carrier = detected_carrier
                result.confidence += 0.2

        # Boost confidence if tracking numbers found
        if tracking_numbers:
            result.confidence += 0.3

        # Cap confidence at 1.0
        result.confidence = min(result.confidence, 1.0)

        # Generate suggested package data
        if result.is_shipment_email and tracking_numbers:
            result.suggested_package_data = self._generate_suggested_package_data(
                tracking_numbers[0], detected_carrier, subject, body
            )

        return result

    def _parse_generic_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        Generic parsing for unknown vendors.
        """
        # Convert email content to clean text using pollution-free normalization
        cleaned_body = self._convert_to_markdown(body)
        logger.debug(f"Converted email body to text (length: {len(cleaned_body)})")

        # Extract vendor name from email address
        vendor_url = self._extract_vendor_from_email(sender)

        # First, try to extract tracking information from URLs (most reliable)
        tracking_number, url_carrier, tracking_link = self._extract_tracking_from_urls(
            cleaned_body
        )

        # Apply vendor URL heuristic early: if vendor URL isn't amazon.com, exclude AMAZON from detection
        exclude_amazon = vendor_url and vendor_url != "amazon.com"

        # Extract tracking number using traditional methods if not found in URLs
        if not tracking_number:
            # Try traditional carrier detection first to get a carrier for tracking extraction
            temp_carrier = self._detect_carrier(
                subject, sender, cleaned_body, vendor_url, exclude_amazon=exclude_amazon
            )
            tracking_number = self._extract_tracking_number(cleaned_body, temp_carrier)

        # If still no tracking number, try with UNKNOWN carrier (more aggressive extraction)
        if not tracking_number:
            tracking_number = self._extract_tracking_number(cleaned_body, "UNKNOWN")

        # Now determine carrier with priority: Amazon vendor_url > Tracking Number > URL > Subject > Traditional
        if vendor_url == "amazon.com":
            # If vendor_url is amazon.com, assume Amazon is the carrier
            carrier = "AMAZON"
        elif tracking_number:
            # Use tracking number to determine carrier (second priority)
            carrier = self._detect_carrier_from_tracking(
                tracking_number, tracking_link, cleaned_body
            )
            if carrier == "UNKNOWN":
                # Fall back to URL-based carrier detection
                if url_carrier != "UNKNOWN":
                    carrier = url_carrier
                else:
                    # Fall back to traditional carrier detection
                    carrier = self._detect_carrier(
                        subject,
                        sender,
                        cleaned_body,
                        vendor_url,
                        exclude_amazon=exclude_amazon,
                    )
        elif url_carrier != "UNKNOWN":
            carrier = url_carrier
        else:
            # Fall back to traditional carrier detection
            carrier = self._detect_carrier(
                subject, sender, cleaned_body, vendor_url, exclude_amazon=exclude_amazon
            )

        # Validate tracking number
        is_valid = self._validate_tracking_number(tracking_number, carrier)

        # Extract additional information
        order_number = self._extract_order_number(cleaned_body, subject)

        # If we didn't find a tracking link initially, try again with carrier info
        if not tracking_link:
            tracking_link = self._extract_tracking_link(
                cleaned_body, carrier, tracking_number, order_number
            )
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        # Extract vendor name from sender domain (simplified approach)
        vendor_name = self._extract_vendor_name_from_sender(sender)

        # If no vendor name from sender, try to extract from vendor URL
        if not vendor_name and vendor_url:
            vendor_name = self._extract_vendor_name_from_url(vendor_url)

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name=vendor_name,
            package_description=package_description,
            status=status,
            vendor_url=vendor_url,
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_amazon_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        Amazon-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        # Amazon-specific patterns - always use AMAZON as carrier
        carrier = "AMAZON"

        # Extract tracking information from URLs first (most reliable)
        tracking_number, url_carrier, tracking_link = self._extract_tracking_from_urls(
            cleaned_body
        )

        # If no tracking number from URLs, try Amazon-specific extraction
        if not tracking_number:
            tracking_number = self._extract_amazon_shipment_id(cleaned_body)

        # If still no tracking link, try Amazon-specific URL extraction
        if not tracking_link:
            tracking_link = self._extract_amazon_tracking_url(cleaned_body)

        order_number = self._extract_order_number(cleaned_body, subject)

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="Amazon",
            package_description=package_description,
            status=status,
            vendor_url="amazon.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_homedepot_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        Home Depot-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        # Home Depot often uses FedEx
        carrier = "FEDEX"
        tracking_number = self._extract_tracking_number(cleaned_body, carrier)
        order_number = self._extract_order_number(cleaned_body, subject)
        tracking_link = self._extract_tracking_link(
            cleaned_body, carrier, tracking_number, order_number
        )

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="Home Depot",
            package_description=package_description,
            status=status,
            vendor_url="homedepot.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_ebay_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        eBay-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        # eBay often uses USPS for domestic shipping
        carrier = "USPS"
        tracking_number = self._extract_tracking_number(cleaned_body, carrier)
        order_number = self._extract_order_number(cleaned_body, subject)
        tracking_link = self._extract_tracking_link(
            cleaned_body, carrier, tracking_number, order_number
        )

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="eBay",
            package_description=package_description,
            status=status,
            vendor_url="ebay.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_ups_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        UPS-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        carrier = "UPS"
        tracking_number = self._extract_tracking_number(cleaned_body, carrier)
        order_number = self._extract_order_number(cleaned_body, subject)
        tracking_link = self._extract_tracking_link(
            cleaned_body, carrier, tracking_number, order_number
        )

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="UPS",
            package_description=package_description,
            status=status,
            vendor_url="ups.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_fedex_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        FedEx-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        carrier = "FEDEX"
        tracking_number = self._extract_tracking_number(cleaned_body, carrier)
        order_number = self._extract_order_number(cleaned_body, subject)
        tracking_link = self._extract_tracking_link(
            cleaned_body, carrier, tracking_number, order_number
        )

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="FedEx",
            package_description=package_description,
            status=status,
            vendor_url="fedex.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _parse_usps_shipping_email(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> ParsedEmailData:
        """
        USPS-specific shipping email parser.
        """
        cleaned_body = self._convert_to_markdown(body)

        carrier = "USPS"
        tracking_number = self._extract_tracking_number(cleaned_body, carrier)
        order_number = self._extract_order_number(cleaned_body, subject)
        tracking_link = self._extract_tracking_link(
            cleaned_body, carrier, tracking_number, order_number
        )

        # Extract other fields
        recipient_name = self._extract_recipient_name(cleaned_body)
        estimated_delivery = self._extract_delivery_date(cleaned_body, email_date)
        package_description = self._extract_package_description(cleaned_body)
        status = self._extract_status(subject, cleaned_body)

        is_valid = self._validate_tracking_number(tracking_number, carrier)
        confidence_score = self._calculate_confidence(
            carrier, tracking_number, order_number, tracking_link
        )

        return ParsedEmailData(
            carrier=carrier,
            tracking_number=tracking_number,
            order_number=order_number,
            tracking_link=tracking_link,
            recipient_name=recipient_name,
            estimated_delivery=estimated_delivery,
            vendor_name="USPS",
            package_description=package_description,
            status=status,
            vendor_url="usps.com",
            is_valid_tracking=is_valid,
            confidence_score=confidence_score,
        )

    def _extract_vendor_from_email(self, sender: str) -> Optional[str]:
        """Extract vendor URL from email address."""
        if not sender:
            return None

        # Extract domain from email address
        if "@" in sender:
            domain = sender.split("@")[-1].lower()

            # Take the last X.Y from the domain
            parts = domain.split(".")
            if len(parts) >= 2:
                return ".".join(parts[-2:])

            return domain

        return None

    def _extract_vendor_name_from_sender(self, sender: str) -> Optional[str]:
        """Extract vendor name from sender email address."""
        # Extract domain from email address
        if "@" not in sender:
            return None

        domain = sender.split("@")[1].lower()

        # Take the last two parts of the domain and format as a readable name
        parts = domain.split(".")
        if len(parts) >= 2:
            base_name = parts[-2].replace("-", " ").replace("_", " ").title()
            return base_name

        return None

    def _extract_vendor_name_from_url(self, vendor_url: str) -> Optional[str]:
        """Extract vendor name from vendor URL (X from X.Y format)."""
        if not vendor_url:
            return None

        # Extract the X part from X.Y format
        parts = vendor_url.split(".")
        if len(parts) >= 2:
            base_name = parts[-2].replace("-", " ").replace("_", " ").title()
            return base_name

        return None

    def _detect_carrier(
        self,
        subject: str,
        sender: str,
        body: str,
        vendor_name: Optional[str] = None,
        exclude_amazon: bool = False,
    ) -> str:
        """Detect the shipping carrier from email content."""
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        body_lower = body.lower()

        # Check if vendor name is a known carrier
        if vendor_name in ["ups.com", "fedex.com", "usps.com", "dhl.com", "amazon.com"]:
            carrier_map = {
                "ups.com": "UPS",
                "fedex.com": "FEDEX",
                "usps.com": "USPS",
                "dhl.com": "DHL",
                "amazon.com": "AMAZON",
            }
            return carrier_map[vendor_name]

        # Special case for Amazon - check sender email first
        if "amazon.com" in sender_lower:
            return "AMAZON"

        # Also check for Amazon in the body content
        if "amazon.com" in body_lower:
            return "AMAZON"

        # Score each carrier based on patterns
        carrier_scores = {}

        for carrier, patterns in self.carrier_patterns.items():
            # Skip AMAZON if exclude_amazon is True
            if exclude_amazon and carrier == "AMAZON":
                continue

            score = 0

            # Check sender patterns
            for pattern in patterns["sender_patterns"]:
                if re.search(pattern, sender_lower, re.IGNORECASE):
                    score += 3  # High weight for sender

            # Check subject patterns
            for pattern in patterns["subject_patterns"]:
                if re.search(pattern, subject_lower, re.IGNORECASE):
                    score += 2  # Medium weight for subject

            # Check body patterns
            for pattern in patterns["body_patterns"]:
                if re.search(pattern, body_lower, re.IGNORECASE):
                    score += 1  # Lower weight for body

            if score > 0:
                carrier_scores[carrier] = score

        # Return the carrier with the highest score
        if carrier_scores:
            return max(carrier_scores, key=carrier_scores.get)

        return "UNKNOWN"

    def _detect_carrier_from_tracking(
        self, tracking_number: str, tracking_link: Optional[str], email_body: str = ""
    ) -> str:
        """
        Attempt to detect carrier from tracking number or tracking link.
        This is a heuristic and might not be accurate for all carriers.
        """
        if not tracking_number and not tracking_link:
            return "UNKNOWN"

        if tracking_number:
            # First, check if we have a tracking link that can help identify the carrier
            if tracking_link:
                if "fedex.com" in tracking_link:
                    return "FEDEX"
                elif "ups.com" in tracking_link:
                    return "UPS"
                elif "usps.com" in tracking_link:
                    return "USPS"
                elif "dhl.com" in tracking_link:
                    return "DHL"

            # Try to identify carrier based on tracking number format
            # UPS: 1Z + 16 alphanumeric characters, or 26 digits
            if re.match(r"^1Z[0-9A-Z]{16}$", tracking_number) or re.match(
                r"^[0-9]{26}$", tracking_number
            ):
                return "UPS"
            # FedEx: 12 digits (Ground) or 15 digits (Express)
            elif re.match(r"^[0-9]{12}$", tracking_number) or re.match(
                r"^[0-9]{15}$", tracking_number
            ):
                return "FEDEX"
            # USPS: 20-22 digits (Priority Mail, First Class)
            elif re.match(r"^[0-9]{20,22}$", tracking_number):
                return "USPS"
            # For 10-digit numbers, we need to be more careful
            elif re.match(r"^[0-9]{10}$", tracking_number):
                # FedEx Ground 10-digit numbers typically start with 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
                # DHL Express 10-digit numbers typically start with specific patterns
                # Look for carrier mentions in the email body to help disambiguate
                if email_body:
                    body_lower = email_body.lower()
                    if "fedex" in body_lower:
                        return "FEDEX"
                    elif "dhl" in body_lower:
                        return "DHL"
                    elif "ups" in body_lower:
                        return "UPS"
                    elif "usps" in body_lower:
                        return "USPS"
                # If no carrier mentions found, return UNKNOWN
                return "UNKNOWN"
            # Additional patterns for longer tracking numbers
            elif re.match(r"^[0-9]{24,26}$", tracking_number):
                # 24-26 digit numbers are often UPS
                return "UPS"
            elif re.match(r"^[0-9]{18,20}$", tracking_number):
                # 18-20 digit numbers are often USPS
                return "USPS"
            # For generic patterns, we rely on the main carrier detection
            return "UNKNOWN"

        if tracking_link:
            # Extract domain from tracking link
            if "amazon.com" in tracking_link:
                return "AMAZON"
            elif "ups.com" in tracking_link:
                return "UPS"
            elif "fedex.com" in tracking_link:
                return "FEDEX"
            elif "usps.com" in tracking_link:
                return "USPS"
            elif "dhl.com" in tracking_link:
                return "DHL"
            # For other domains, we rely on the main carrier detection
            return "UNKNOWN"

        return "UNKNOWN"

    def _detect_carrier_from_subject(self, subject: str) -> str:
        """
        Attempt to detect carrier from subject line patterns.
        This is a heuristic based on common subject line formats.
        """
        if not subject:
            return "UNKNOWN"

        subject_lower = subject.lower()

        # Check for specific vendor patterns in subject
        if "amazon" in subject_lower:
            return "AMAZON"
        elif "ups" in subject_lower:
            return "UPS"
        elif "fedex" in subject_lower or "fedex" in subject_lower:
            return "FEDEX"
        elif "usps" in subject_lower:
            return "USPS"
        elif "dhl" in subject_lower:
            return "DHL"
        elif "ebay" in subject_lower:
            # eBay often uses USPS for domestic shipping
            return "USPS"
        elif "lulu" in subject_lower:
            # Lulu often uses UPS
            return "UPS"
        elif "dk hardware" in subject_lower:
            # DK Hardware often uses USPS
            return "USPS"
        elif "foodservicedirect" in subject_lower:
            # FoodServiceDirect often uses DHL
            return "DHL"
        elif "macys" in subject_lower or "macy" in subject_lower:
            # Macy's often uses UPS
            return "UPS"

        return "UNKNOWN"

    def _extract_tracking_number(self, body: str, carrier: str) -> str:
        """
        Extract tracking number from email body using scoped regex patterns.

        This implements the expert strategy of applying regex only to:
        1. Selected HTML blocks (like tables that passed semantic filtering)
        2. Text around keyword anchors
        """
        # The body should already be cleaned and converted to text
        decoded_body = body

        # Special handling for Amazon - extract shipment ID from tracking URLs
        if carrier == "AMAZON":
            return self._extract_amazon_shipment_id(decoded_body)

        # Step 1: Context-aware extraction - only look in blocks containing shipping keywords
        anchor_keywords = [
            "tracking",
            "order",
            "item",
            "shipping",
            "delivery",
            "package",
            "carrier",
            "ship",
            "amazon",
        ]

        # Split into paragraphs and only process relevant ones
        paragraphs = decoded_body.split("\n\n")

        for para in paragraphs:
            para_lower = para.lower()
            if any(keyword in para_lower for keyword in anchor_keywords):
                # Apply tracking number patterns only to this relevant paragraph
                tracking_number = self._extract_tracking_from_paragraph(para, carrier)
                if tracking_number:
                    return tracking_number

        # Step 2: If context-aware extraction found nothing, try global extraction
        logger.debug("Context-aware extraction failed, trying global extraction")
        return self._extract_tracking_from_paragraph(decoded_body, carrier)

    def _extract_tracking_from_paragraph(self, text: str, carrier: str) -> str:
        """
        Extract tracking number from a specific text block using contextual regex.
        """
        # First, look for tracking numbers in URLs and JSON-like structures
        url_patterns = [
            r"trackNums=([0-9A-Z]{8,30})",
            r"tracknum=([0-9A-Z]{8,30})",
            r"trknbr=([0-9A-Z]{8,30})",
            r"tLabels=([0-9A-Z]{8,30})",
            r"trackingNumber=([0-9A-Z]{8,30})",
            r"tracking_id=([0-9A-Z]{8,30})",
            r"trackingId=([0-9A-Z]{8,30})",
            r"\"tracking_id\":\"([0-9A-Z]{8,30})\"",
            r"\"trackingId\":\"([0-9A-Z]{8,30})\"",
            r"\"tracking_number\":\"([0-9A-Z]{8,30})\"",
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_tracking_candidate(match):
                    return match

        # Look for explicit tracking number patterns with context
        # Use contextual regex: 'Tracking Number: ZY12345678' not just random 10-char uppercase
        contextual_patterns = [
            r"(?:tracking\s*number|track|shipment\s*id)[\s:]*([A-Z0-9]{8,30})",
            r"(?:Tracking\s*Number|Track|Shipment\s*ID)[\s:]*([A-Z0-9]{8,30})",
            r"Tracking\s*ID:\s*([A-Z0-9]{8,30})",
            r"Shipment\s*ID:\s*([A-Z0-9]{8,30})",
        ]

        for pattern in contextual_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_tracking_candidate(match):
                    return match

        # Use carrier-specific patterns first (highest priority)
        if carrier in self.tracking_patterns:
            pattern = self.tracking_patterns[carrier]
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_tracking_candidate(match):
                    return match

        # Try all carrier patterns (even if carrier is UNKNOWN)
        for carrier_name, pattern in self.tracking_patterns.items():
            if carrier_name != "GENERIC":
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if self._is_valid_tracking_candidate(match):
                        return match

        # Try generic patterns for unknown carriers (but be more strict)
        generic_pattern = self.tracking_patterns.get("GENERIC", r"\b[A-Z0-9]{8,30}\b")
        matches = re.findall(generic_pattern, text, re.IGNORECASE)

        # For generic patterns, be more selective
        for match in matches:
            if self._is_valid_tracking_candidate(match):
                # Don't return order numbers as tracking numbers
                # Order numbers are typically found in subject lines with # prefix
                # If this looks like an order number (10 digits, no letters), skip it
                if re.match(r"^[0-9]{10}$", match) and not re.search(
                    r"1Z[A-Z0-9]{16}", text
                ):
                    continue
                return match

        return ""

    def _is_valid_tracking_candidate(self, text: str) -> bool:
        """
        Validate if a text candidate is likely a real tracking number.
        """
        if not text or len(text) < 8:
            return False

        # Don't accept strings that look like URL parameters
        if re.search(r"[=&\?]", text):
            return False

        # Don't accept common false positives
        if self._is_common_false_positive(text):
            return False

        # Must contain at least one digit
        if not re.search(r"[0-9]", text):
            return False

        # Don't accept all lowercase words
        if re.match(r"^[a-z]+$", text.lower()):
            return False

        # Don't accept all uppercase words
        if re.match(r"^[A-Z]+$", text):
            return False

        return True

    def _extract_tracking_from_urls(self, body: str) -> tuple[str, str, Optional[str]]:
        """
        Extract tracking number, carrier, and tracking link from URLs in email body.
        Returns (tracking_number, carrier, tracking_link)

        Note: This method now expects cleaned markdown content, not raw HTML.
        """
        # The body should already be cleaned and converted to markdown
        # No need for additional quoted-printable decoding here
        decoded_body = body

        # URL patterns that include both the URL and tracking number
        url_patterns = [
            # UPS patterns
            (
                r"(https?://[^\s]*ups\.com[^\s]*track[^\s]*trackNums=([0-9A-Z]{8,30}))",
                "UPS",
            ),
            (
                r"(https?://[^\s]*ups\.com[^\s]*track[^\s]*tracknum=([0-9A-Z]{8,30}))",
                "UPS",
            ),
            # FedEx patterns
            (
                r"(https?://[^\s]*fedex\.com[^\s]*fedextrack[^\s]*trknbr=([0-9A-Z]{8,30}))",
                "FEDEX",
            ),
            # USPS patterns
            (
                r"(https?://[^\s]*usps\.com[^\s]*TrackConfirmAction[^\s]*tLabels=([0-9A-Z]{8,30}))",
                "USPS",
            ),
            (
                r"(https?://[^\s]*tools\.usps\.com[^\s]*TrackConfirmAction[^\s]*tLabels=([0-9A-Z]{8,30}))",
                "USPS",
            ),
            # DHL patterns
            (
                r"(https?://[^\s]*dhl\.com[^\s]*tracking[^\s]*AWB=([0-9A-Z]{8,30}))",
                "DHL",
            ),
            # Amazon patterns - handle both encoded and decoded versions
            (
                r"(https?://[^\s]*amazon\.com[^\s]*progress-tracker[^\s]*shipmentId=([0-9A-Z]{8,30}))",
                "AMAZON",
            ),
            (
                r"(https?://[^\s]*amazon\.com[^\s]*progress-tracker[^\s]*shipmentId=3D([0-9A-Z]{8,30}))",
                "AMAZON",
            ),
            # Generic patterns
            (
                r"\"tracking_url\":\"(https?://[^\s]*)\".*?\"tracking_id\":\"([0-9A-Z]{8,30})\"",
                "UNKNOWN",
            ),
            (
                r"\"trackingId\":\"([0-9A-Z]{8,30})\".*?\"tracking_url\":\"(https?://[^\s]*)\"",
                "UNKNOWN",
            ),
        ]

        for pattern, detected_carrier in url_patterns:
            matches = re.findall(pattern, decoded_body, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:  # URL and tracking number
                    url, tracking_number = match
                    if not self._is_common_false_positive(tracking_number):
                        # Handle URL encoding for Amazon shipment IDs
                        if detected_carrier == "AMAZON" and "shipmentId=3D" in url:
                            # The tracking number is missing the 3D prefix, add it back
                            tracking_number = "3D" + tracking_number

                        # Determine carrier from URL domain if not already specified
                        if detected_carrier == "UNKNOWN":
                            if "ups.com" in url:
                                detected_carrier = "UPS"
                            elif "fedex.com" in url:
                                detected_carrier = "FEDEX"
                            elif "usps.com" in url or "tools.usps.com" in url:
                                detected_carrier = "USPS"
                            elif "dhl.com" in url:
                                detected_carrier = "DHL"
                            elif "amazon.com" in url:
                                detected_carrier = "AMAZON"
                        return tracking_number, detected_carrier, url
                elif (
                    len(match) == 1
                ):  # Single match (URL with embedded tracking number)
                    url = match
                    # Extract tracking number from URL
                    tracking_match = re.search(r"([0-9A-Z]{8,30})", url)
                    if tracking_match:
                        tracking_number = tracking_match.group(1)
                        if not self._is_common_false_positive(tracking_number):
                            return tracking_number, detected_carrier, url

        return "", "UNKNOWN", None

    def _extract_amazon_shipment_id(self, body: str) -> str:
        """Extract Amazon shipment ID from tracking URLs."""
        # Look for shipment ID in Amazon tracking URLs
        # The body should already be cleaned, so we only need clean patterns
        shipment_patterns = [
            r"shipmentId=([A-Za-z0-9]+)",  # Clean version
            r"shipment_id=([A-Za-z0-9]+)",
            r"shipment=([A-Za-z0-9]+)",
        ]

        # Look for shipment ID patterns in the cleaned body
        for pattern in shipment_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                shipment_id = match.group(1)
                if len(shipment_id) >= 8:  # Amazon shipment IDs are typically 8+ chars
                    # Check if this looks like an Amazon shipment ID that might be missing the "3D" prefix
                    if (
                        len(shipment_id) == 8
                        and shipment_id.isalnum()
                        and not shipment_id.startswith("3D")
                    ):
                        # This might be a truncated Amazon shipment ID missing the "3D" prefix
                        # Look for the full ID in the URL
                        full_id_pattern = rf"shipmentId=3D{shipment_id}"
                        if re.search(full_id_pattern, body, re.IGNORECASE):
                            full_id = f"3D{shipment_id}"
                            logger.debug(
                                f"Found full Amazon shipment ID with 3D prefix: {full_id}"
                            )
                            return full_id

                    logger.debug(f"Found Amazon shipment ID: {shipment_id}")
                    return shipment_id

        # Also look for the "3D" prefix pattern directly
        three_d_pattern = r"shipmentId=3D([A-Za-z0-9]+)"
        match = re.search(three_d_pattern, body, re.IGNORECASE)
        if match:
            shipment_id = f"3D{match.group(1)}"
            if len(shipment_id) >= 10:  # 3D + 8+ chars
                logger.debug(f"Found Amazon shipment ID with 3D prefix: {shipment_id}")
                return shipment_id

        # Debug: check if we can find any Amazon URLs in the body
        amazon_urls = re.findall(
            r"https?://[^\s]*amazon\.com[^\s]*", body, re.IGNORECASE
        )
        if amazon_urls:
            logger.debug(
                f"Found Amazon URLs in body: {amazon_urls[:3]}"
            )  # Show first 3

        return ""

    def _is_common_false_positive(self, text: str) -> bool:
        """Check if a potential tracking number is a common false positive."""
        # Common false positives in email content
        false_positives = [
            "delivered",
            "shipped",
            "ordered",
            "tracking",
            "package",
            "order",
            "delivery",
            "arriving",
            "estimated",
            "expected",
            "quantity",
            "total",
            "usd",
            "price",
            "cost",
            "amount",
            "shipping",
            "confirmed",
            "processing",
            "pending",
            "cancelled",
            "refunded",
            "handling",
            "tax",
            "content",
            "important",
            "font",
            "style",
            "script",
            "css",
            "javascript",
            "background",
            "color",
            "border",
            "margin",
            "padding",
            "width",
            "height",
            "display",
            "position",
            "absolute",
            "relative",
            "fixed",
            "static",
            "overflow",
            "hidden",
            "visible",
            "auto",
            "scroll",
            "none",
            "block",
            "inline",
            "flex",
            "grid",
            "table",
            "row",
            "column",
            "center",
            "left",
            "right",
            "top",
            "bottom",
            "middle",
            "start",
            "end",
            "justify",
            "align",
            "items",
            "self",
            "space",
            "between",
            "around",
            "evenly",
            "wrap",
            "nowrap",
            "reverse",
            "grow",
            "shrink",
            "basis",
            "z",
            "index",
            "opacity",
            "visibility",
            "collapse",
            "inherit",
            "initial",
            "unset",
            "revert",
            "recipient",
            "valued",
            "dear",
            "hello",
            "hi",
            "fedextrack",
            "information",
            "bankcard",
            "opt",
            "classic",
            "distance",
            "pex",
            "fedex",
            "ups",
            "usps",
            "dhl",
            "amazon",
            "shipment",
            "december",
            "reference",
        ]

        # Check if it's a common false positive
        if text.lower() in false_positives:
            return True

        # Check for timestamp patterns (Unix timestamps)
        if re.match(r"^\d{10,13}$", text):
            # But don't flag valid tracking numbers as timestamps
            if len(text) == 12:  # FedEx tracking numbers are 12 digits
                return False
            if len(text) == 10 and text.startswith("1"):  # DHL tracking numbers
                return False
            # Don't flag 10-digit numbers as timestamps - they could be order numbers
            if len(text) == 10:
                return False
            return True

        # Check for CSS color codes
        if re.match(r"^#[0-9A-Fa-f]{3,6}$", text):
            return True

        # Check for CSS units
        if re.match(r"^\d+(\.\d+)?(px|em|rem|%|vh|vw|pt|pc|in|cm|mm)$", text):
            return True

        # Check for common CSS values
        if text.lower() in ["auto", "none", "inherit", "initial", "unset"]:
            return True

        # Check for very short or very long strings
        if len(text) < 6 or len(text) > 30:
            return True

        # Check for CSS class names that start with common prefixes
        if text.startswith(
            ("package", "item", "product", "order", "tracking", "shipping", "delivery")
        ):
            return True

        # Don't filter out strings that contain both letters and numbers (likely real tracking numbers)
        if re.search(r"[A-Za-z]", text) and re.search(r"[0-9]", text):
            return False

        return False

    def _validate_tracking_number(self, tracking_number: str, carrier: str) -> bool:
        """Validate tracking number format for the detected carrier."""
        if not tracking_number:
            return False

        if carrier == "UPS":
            # UPS: 1Z + 16 alphanumeric characters
            return bool(re.match(r"^1Z[0-9A-Z]{16}$", tracking_number))
        elif carrier == "FEDEX":
            # FedEx: 12 digits
            return bool(re.match(r"^[0-9]{12}$", tracking_number))
        elif carrier == "USPS":
            # USPS: 20-22 digits
            return bool(re.match(r"^[0-9]{20,22}$", tracking_number))
        elif carrier == "DHL":
            # DHL: 10 digits
            return bool(re.match(r"^[0-9]{10}$", tracking_number))
        elif carrier == "AMAZON":
            # Amazon can use various carriers, so be more lenient
            return len(tracking_number) >= 8

        # For unknown carriers, be more strict
        return False

    def _extract_order_number(self, body: str, subject: str = "") -> Optional[str]:
        """Extract order number from email body and subject using context-aware patterns."""
        # First, check the subject line for order numbers (highest priority)
        if subject:
            subject_patterns = [
                r"order\s*#\s*([A-Z0-9\-]+)",
                r"Order#\s*DKH-([0-9]+)",
                r"Order\s*#\s*DKH-([0-9]+)",
                r"order\s+([A-Z0-9\-]+)\s+has",
                r"order\s+([A-Z0-9\-]+)\s+is",
                r"order\s+([A-Z0-9\-]+)\s+was",
                r"#([A-Z0-9\-]+)\s+shipped",
                r"#([A-Z0-9\-]+)\s+delivered",
                r"#([A-Z0-9\-]+)\s+confirmed",
                # More specific patterns to avoid false positives
                r"order\s+#([A-Z0-9\-]+)",
                r"order\s*#([A-Z0-9\-]+)",
                # Pattern for order numbers in format "#2785257654"
                r"#([0-9]+)",
            ]

            for pattern in subject_patterns:
                matches = re.findall(pattern, subject, re.IGNORECASE)
                for match in matches:
                    if not self._is_common_false_positive(match):
                        return match

        # Context-aware extraction from body: only look in relevant paragraphs
        anchor_keywords = [
            "order",
            "item",
            "purchase",
            "confirmation",
            "receipt",
            "invoice",
        ]

        # Split into paragraphs and only process relevant ones
        paragraphs = body.split("\n\n")

        for para in paragraphs:
            para_lower = para.lower()
            if any(keyword in para_lower for keyword in anchor_keywords):
                # Apply order number patterns only to this relevant paragraph

                # Specific patterns for different vendors
                specific_patterns = [
                    r"Order\s*#\s*([A-Z0-9\-]+)",
                    r"Order\s*Number\s*:?\s*([A-Z0-9\-]+)",
                    r"Order\s*ID\s*:?\s*([A-Z0-9\-]+)",
                    r"Order\s*Reference\s*:?\s*([A-Z0-9\-]+)",
                    r"Purchase\s*Order\s*:?\s*([A-Z0-9\-]+)",
                    r"Confirmation\s*#\s*([A-Z0-9\-]+)",
                    r"Receipt\s*#\s*([A-Z0-9\-]+)",
                    r"Invoice\s*#\s*([A-Z0-9\-]+)",
                    # Amazon specific patterns
                    r"#([0-9]{3}-[0-9]{7}-[0-9]{7})",
                    # AliExpress patterns
                    r"Order\s*([0-9]{10,})",
                    # eBay patterns
                    r"Item\s*#\s*([0-9]+)",
                    # Walmart patterns
                    r"Order\s*([0-9]{10,})",
                    # Home Depot patterns
                    r"Order\s*#\s*DKH-([0-9]+)",
                    # DK Hardware patterns
                    r"Order\s*#\s*DKH-([0-9]+)",
                ]

                for pattern in specific_patterns:
                    match = re.search(pattern, para, re.IGNORECASE)
                    if match:
                        order_num = match.group(1)
                        # Filter out common false positives
                        if (
                            len(order_num) > 3
                            and not (order_num.isdigit() and len(order_num) <= 4)
                            and order_num.lower()
                            not in [
                                "estimated",
                                "delivery",
                                "tracking",
                                "number",
                                "expected",
                                "reference",
                                "here",
                                "info",
                                "no",
                                "nbsp",
                                "ready",
                                "shipped",
                                "arrives",
                                "collapse",
                                "bottom",
                                "box",
                                "styles",
                                "content",
                                "padding",
                                "line",
                                "decoration",
                                "stylesheet",
                                "ingnumber",
                                "clickthrugh",
                                "dtccomnew",
                                "numberrow",
                                "information",
                                "bankcard",
                            ]
                        ):
                            return order_num

        return None

    def _extract_tracking_link(
        self,
        body: str,
        carrier: str,
        tracking_number: str,
        order_number: Optional[str] = None,
    ) -> Optional[str]:
        """Extract tracking link from email body."""
        # Comprehensive patterns for tracking links
        link_patterns = {
            "UPS": [
                r"https?://[^\s]*ups\.com[^\s]*track[^\s]*",
                r"https?://[^\s]*wwwapps\.ups\.com[^\s]*WebTracking[^\s]*",
            ],
            "FEDEX": [
                r"https?://[^\s]*fedex\.com[^\s]*fedextrack[^\s]*",
                r"https?://[^\s]*fedex\.com[^\s]*track[^\s]*",
            ],
            "USPS": [
                r"https?://[^\s]*usps\.com[^\s]*TrackConfirmAction[^\s]*",
                r"https?://[^\s]*tools\.usps\.com[^\s]*TrackConfirmAction[^\s]*",
                r"https?://[^\s]*tools\.usps\.com[^\s]*go[^\s]*",
            ],
            "AMAZON": [
                r"https?://[^\s]*amazon\.com[^\s]*progress-tracker[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*order-details[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*css/order-details[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*gp/css/order-details[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*gp/your-account[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*orders[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*track[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*ship[^\s]*",
                r"https?://[^\s]*amazon\.com[^\s]*deliver[^\s]*",
            ],
            "DHL": [
                r"https?://[^\s]*dhl\.com[^\s]*tracking[^\s]*",
                r"https?://[^\s]*dhl\.com[^\s]*express/tracking[^\s]*",
            ],
        }

        # Special handling for Amazon URLs
        if carrier == "AMAZON":
            # Custom method to extract Amazon URLs from cleaned content
            amazon_url = self._extract_amazon_tracking_url(body)
            if amazon_url:
                return amazon_url

        # Try to find existing tracking links for other carriers
        if carrier in link_patterns:
            for pattern in link_patterns[carrier]:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    # Clean and return the first match
                    found_link = self._clean_url(matches[0])

                    # For other carriers, ensure the link contains the tracking number if we have one
                    if tracking_number and tracking_number in found_link:
                        return found_link
                    elif not tracking_number:
                        return found_link

        # Don't generate links - only return what we actually find in the email
        return None

    def _extract_amazon_tracking_url(self, body: str) -> Optional[str]:
        """Extract Amazon tracking URL from cleaned content."""
        # Use robust URL extraction to handle QP encoding, HTML tags, etc.
        urls = self._extract_urls_robustly(body)

        # Filter for Amazon tracking URLs
        amazon_tracking_urls = []
        for url in urls:
            if "amazon.com" in url and any(
                keyword in url
                for keyword in ["progress-tracker", "order-details", "track", "ship"]
            ):
                amazon_tracking_urls.append(url)

        # Priority 1: progress-tracker URLs (most reliable)
        progress_tracker_urls = [
            url for url in amazon_tracking_urls if "progress-tracker" in url
        ]
        if progress_tracker_urls:
            url = progress_tracker_urls[0]
            # Reconstruct truncated Amazon URLs
            reconstructed_url = self._reconstruct_amazon_url(url)
            cleaned_url = self._clean_url(reconstructed_url)
            return cleaned_url

        # Priority 2: order-details URLs
        order_details_urls = [
            url for url in amazon_tracking_urls if "order-details" in url
        ]
        if order_details_urls:
            url = order_details_urls[0]
            reconstructed_url = self._reconstruct_amazon_url(url)
            cleaned_url = self._clean_url(reconstructed_url)
            return cleaned_url

        # Priority 3: any other Amazon tracking URL
        if amazon_tracking_urls:
            url = amazon_tracking_urls[0]
            reconstructed_url = self._reconstruct_amazon_url(url)
            cleaned_url = self._clean_url(reconstructed_url)
            return cleaned_url

        return None

    def _clean_url(self, url: str) -> str:
        """Clean up URL by removing encoding artifacts and truncation."""
        # The URL should already be cleaned from markdown conversion
        # Just do basic cleanup

        # Remove HTML tag artifacts (">Click, etc.)
        if '">' in url:
            url = url.split('">')[0]

        # For Amazon URLs, be very careful about truncation
        if "amazon.com" in url:
            # Don't truncate Amazon URLs - they might be intentionally long
            # Only remove obvious HTML artifacts
            if url.endswith("=") and not any(
                param in url for param in ["orderId=", "shipmentId=", "packageIndex="]
            ):
                url = url[:-1]
        else:
            # Remove truncated URLs (those ending with =) for non-Amazon URLs
            if url.endswith("="):
                url = url[:-1]

        # Remove incomplete URLs (those ending with partial parameters)
        # But don't do this for Amazon URLs since they might be intentionally long
        if "=" in url and not url.endswith("=") and "amazon.com" not in url:
            # Find the last complete parameter
            parts = url.split("&")
            clean_parts = []
            for part in parts:
                if "=" in part and not part.endswith("="):
                    clean_parts.append(part)
                elif "=" not in part:
                    clean_parts.append(part)
            if clean_parts:
                url = "&".join(clean_parts)

        # For Amazon URLs, ensure we don't truncate them
        if "amazon.com" in url and "progress-tracker" in url:
            # Don't apply any truncation to Amazon progress-tracker URLs
            # Also fix common truncation issues
            if "ncoding=UTF8" in url:
                url = url.replace("ncoding=UTF8", "pro&_encoding=UTF8")
            if "gress-tracker" in url:
                url = url.replace("gress-tracker", "progress-tracker")
            pass

        # Ensure we have the full URL with all parameters
        # Don't truncate URLs that are already complete
        return url

    def _generate_tracking_link(
        self, carrier: str, tracking_number: str, order_number: Optional[str] = None
    ) -> str:
        """Generate tracking link for a carrier and tracking number."""
        base_urls = {
            "UPS": f"https://www.ups.com/track?tracknum={tracking_number}",
            "FEDEX": f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}",
            "USPS": f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}",
            "DHL": f"https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}",
            "AMAZON": f"https://www.amazon.com/gp/your-account/order-details/ref=oh_aui_or_od?ie=UTF8&orderID={order_number or tracking_number}",
        }

        return base_urls.get(carrier, "")

    def _extract_recipient_name(self, body: str) -> Optional[str]:
        """Extract recipient name from email body using context-aware patterns."""
        # Context-aware extraction: only look in blocks containing recipient-related keywords
        anchor_keywords = [
            "dear",
            "hello",
            "hi",
            "recipient",
            "deliver",
            "ship",
            "address",
            "customer",
        ]

        # Split into paragraphs and only process relevant ones
        paragraphs = body.split("\n\n")

        for para in paragraphs:
            para_lower = para.lower()
            if any(keyword in para_lower for keyword in anchor_keywords):
                # Apply recipient name patterns only to this relevant paragraph

                # Look for "Dear First Last" pattern
                dear_pattern = r"Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(dear_pattern, para)
                if match:
                    name = match.group(1)
                    # Validate it's a reasonable name
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

                # Look for "Hello First Last" pattern
                hello_pattern = r"Hello\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(hello_pattern, para)
                if match:
                    name = match.group(1)
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

                # Look for "Hi First Last" pattern
                hi_pattern = r"Hi\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(hi_pattern, para)
                if match:
                    name = match.group(1)
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

                # Look for "Recipient: First Last" pattern
                recipient_pattern = r"Recipient\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(recipient_pattern, para)
                if match:
                    name = match.group(1)
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

                # Look for "Ship to: First Last" pattern
                ship_to_pattern = r"Ship\s+to\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(ship_to_pattern, para)
                if match:
                    name = match.group(1)
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

                # Look for "Deliver to: First Last" pattern
                deliver_to_pattern = r"Deliver\s+to\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
                match = re.search(deliver_to_pattern, para)
                if match:
                    name = match.group(1)
                    if len(name.split()) == 2 and all(
                        len(word) >= 2 for word in name.split()
                    ):
                        return name

        return None

    def _extract_delivery_date(
        self, body: str, email_date: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract estimated delivery date from email body.

        Args:
            body: Email body text
            email_date: Email send date in ISO format for relative date resolution

        Returns:
            Standardized date in YYYY-MM-DD format or None if not found
        """
        from datetime import timedelta

        # Parse email date if provided
        email_datetime = None
        if email_date:
            try:
                email_datetime = datetime.fromisoformat(
                    email_date.replace("Z", "+00:00")
                )
            except Exception:
                # If parsing fails, use current date as fallback
                email_datetime = datetime.now()

        # Enhanced patterns for various date formats
        patterns = [
            # Full dates with year
            r"estimated.*?delivery.*?:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"expected.*?delivery.*?:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"delivery.*?date.*?:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"arrive.*?by.*?([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"delivery.*?by.*?([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"arriving.*?([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            # Dates without year (will use email date year or current year)
            r"estimated.*?delivery.*?:?\s*([A-Za-z]+\s+\d{1,2})",
            r"expected.*?delivery.*?:?\s*([A-Za-z]+\s+\d{1,2})",
            r"delivery.*?date.*?:?\s*([A-Za-z]+\s+\d{1,2})",
            r"arrive.*?by.*?([A-Za-z]+\s+\d{1,2})",
            r"delivery.*?by.*?([A-Za-z]+\s+\d{1,2})",
            r"arriving.*?([A-Za-z]+\s+\d{1,2})",
            # Abbreviated month formats
            r"estimated.*?delivery.*?:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            r"expected.*?delivery.*?:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            r"delivery.*?date.*?:?\s*([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            r"arrive.*?by.*?([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            r"delivery.*?by.*?([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            r"arriving.*?([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            # Abbreviated month without year
            r"estimated.*?delivery.*?:?\s*([A-Za-z]{3}\s+\d{1,2})",
            r"expected.*?delivery.*?:?\s*([A-Za-z]{3}\s+\d{1,2})",
            r"delivery.*?date.*?:?\s*([A-Za-z]{3}\s+\d{1,2})",
            r"arrive.*?by.*?([A-Za-z]{3}\s+\d{1,2})",
            r"delivery.*?by.*?([A-Za-z]{3}\s+\d{1,2})",
            r"arriving.*?([A-Za-z]{3}\s+\d{1,2})",
            # Day of week formats
            r"estimated.*?delivery.*?:?\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"expected.*?delivery.*?:?\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"delivery.*?date.*?:?\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"arrive.*?by.*?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"delivery.*?by.*?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            r"arriving.*?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            # Abbreviated day of week
            r"estimated.*?delivery.*?:?\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            r"expected.*?delivery.*?:?\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            r"delivery.*?date.*?:?\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            r"arrive.*?by.*?(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            r"delivery.*?by.*?(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            r"arriving.*?(Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
            # Relative dates
            r"estimated.*?delivery.*?:?\s*(today|tomorrow|next\s+week)",
            r"expected.*?delivery.*?:?\s*(today|tomorrow|next\s+week)",
            r"delivery.*?date.*?:?\s*(today|tomorrow|next\s+week)",
            r"arrive.*?by.*?(today|tomorrow|next\s+week)",
            r"delivery.*?by.*?(today|tomorrow|next\s+week)",
            r"arriving.*?(today|tomorrow|next\s+week)",
            # Date ranges (take first date)
            r"arriving\s+([A-Za-z]+\s+\d{1,2}\s*-\s*[A-Za-z]+\s+\d{1,2})",
            r"delivery.*?([A-Za-z]+\s+\d{1,2}\s*-\s*[A-Za-z]+\s+\d{1,2})",
            # Generic patterns (lower priority)
            r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})",
            # Specific patterns found in emails
            r"([A-Za-z]+,?\s+[A-Za-z]+\s+\d{1,2})",  # Monday, May 13
            r"([A-Za-z]{3},?\s+[A-Za-z]+\s+\d{1,2})",  # Mon, Nov 25
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()

                # Handle relative dates first
                if date_str.lower() in ["today", "tomorrow", "next week"]:
                    if email_datetime:
                        if date_str.lower() == "today":
                            return email_datetime.strftime("%Y-%m-%d")
                        elif date_str.lower() == "tomorrow":
                            tomorrow = email_datetime + timedelta(days=1)
                            return tomorrow.strftime("%Y-%m-%d")
                        elif date_str.lower() == "next week":
                            next_week = email_datetime + timedelta(days=7)
                            return next_week.strftime("%Y-%m-%d")
                    continue

                # Handle day of week (find next occurrence after email date)
                day_names = {
                    "monday": 0,
                    "mon": 0,
                    "tuesday": 1,
                    "tue": 1,
                    "wednesday": 2,
                    "wed": 2,
                    "thursday": 3,
                    "thu": 3,
                    "friday": 4,
                    "fri": 4,
                    "saturday": 5,
                    "sat": 5,
                    "sunday": 6,
                    "sun": 6,
                }

                if date_str.lower() in day_names:
                    if email_datetime:
                        target_day = day_names[date_str.lower()]
                        current_day = email_datetime.weekday()
                        days_ahead = target_day - current_day

                        # If target day is today or in the past, find next week
                        if days_ahead <= 0:
                            days_ahead += 7

                        target_date = email_datetime + timedelta(days=days_ahead)
                        return target_date.strftime("%Y-%m-%d")
                    continue

                # Handle date ranges (take first date)
                if " - " in date_str:
                    first_date = date_str.split(" - ")[0].strip()
                    date_str = first_date

                # Try various date formats
                date_formats = [
                    "%B %d, %Y",  # January 15, 2024
                    "%B %d %Y",  # January 15 2024
                    "%b %d, %Y",  # Jan 15, 2024
                    "%b %d %Y",  # Jan 15 2024
                    "%B %d",  # January 15 (no year)
                    "%b %d",  # Jan 15 (no year)
                ]

                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)

                        # If no year in format, use a reasonable year
                        if "%Y" not in fmt:
                            # Use email date year if available, but be smart about it
                            if email_datetime:
                                # If email date is in the future (like 2025), use current year instead
                                current_year = datetime.now().year
                                if email_datetime.year > current_year + 1:
                                    parsed_date = parsed_date.replace(year=current_year)
                                else:
                                    parsed_date = parsed_date.replace(
                                        year=email_datetime.year
                                    )
                            else:
                                parsed_date = parsed_date.replace(
                                    year=datetime.now().year
                                )

                        return parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        continue

        return None

    def _extract_shipper_name(self, body: str) -> Optional[str]:
        """Extract shipper name from email body."""
        patterns = [
            r"from.*:?\s*([A-Za-z\s]+)",
            r"shipper.*:?\s*([A-Za-z\s]+)",
            r"sent.*by.*:?\s*([A-Za-z\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 50:
                    return name

        return None

    def _extract_package_description(self, body: str) -> Optional[str]:
        """Extract package description from email body."""
        # Look for package description patterns
        patterns = [
            r"package.*details?.*:?\s*([^.\n]+)",
            r"items?.*:?\s*([^.\n]+)",
            r"description.*:?\s*([^.\n]+)",
            r"contents?.*:?\s*([^.\n]+)",
            r"\*\s*([^*\n]+?)(?:\s*Quantity:|$)",  # Amazon-style item lists
            r"product.*:?\s*([^.\n]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            for match in matches:
                match = match.strip()
                if (
                    match
                    and len(match) > 3
                    and not self._is_common_false_positive(match)
                ):
                    return match

        return None

    def _extract_status(self, subject: str, body: str) -> Optional[str]:
        """Extract shipping status from email subject and body."""
        # Common shipping status keywords - order matters (more specific first)
        status_patterns = {
            "confirmed": [
                r"order.*confirmed",
                r"confirmed",
                r"order.*received",
                r"thanks.*for.*your.*order",
                r"order.*placed",
                r"order.*processed",
                r"ready.*to.*ship",
            ],
            "out_for_delivery": [
                r"out.*for.*delivery",
                r"out.*for.*delivery.*today",
                r"package.*out.*for.*delivery",
                r"delivery.*today",
            ],
            "delivered": [
                r"delivered",
                r"delivery.*complete",
                r"package.*delivered",
                r"order.*delivered",
                r"successfully.*delivered",
                r"delivery.*confirmed",
            ],
            "exception": [
                r"exception",
                r"delivery.*exception",
                r"package.*exception",
                r"shipment.*exception",
                r"delivery.*failed",
                r"failed.*delivery",
            ],
            "in_transit": [
                r"in.*transit",
                r"on.*the.*way",
                r"package.*in.*transit",
                r"shipment.*in.*transit",
                r"on.*its.*way",
            ],
            "shipped": [
                r"shipped",
                r"shipment.*sent",
                r"package.*shipped",
                r"order.*shipped",
                r"your.*package.*has.*been.*shipped",
                r"shipment.*notification",
            ],
            "pending": [
                r"pending",
                r"order.*pending",
                r"shipment.*pending",
                r"package.*pending",
                r"processing",
                r"order.*processing",
            ],
            "packing": [
                r"packing",
                r"being.*packed",
                r"preparing.*shipment",
            ],
        }

        # Check subject first (often more reliable for status)
        subject_lower = subject.lower()
        body_lower = body.lower()

        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if re.search(pattern, subject_lower, re.IGNORECASE):
                    return status.replace("_", " ").title()

        # Check body if not found in subject
        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if re.search(pattern, body_lower, re.IGNORECASE):
                    return status.replace("_", " ").title()

        # Check for specific carrier status patterns
        if "amazon" in body_lower:
            if "shipped" in body_lower:
                return "Shipped"
            elif "delivered" in body_lower:
                return "Delivered"
            elif "out for delivery" in body_lower:
                return "Out For Delivery"

        return None

    def _calculate_confidence(
        self,
        carrier: str,
        tracking_number: str,
        order_number: Optional[str],
        tracking_link: Optional[str],
    ) -> float:
        """Calculate confidence score for the parsed data."""
        score = 0.0

        # Base score for carrier detection
        if carrier != "UNKNOWN":
            score += 0.3

        # Score for valid tracking number
        if tracking_number and self._validate_tracking_number(tracking_number, carrier):
            score += 0.4

        # Score for order number
        if order_number:
            score += 0.1

        # Score for tracking link
        if tracking_link:
            score += 0.1

        # Bonus for high-confidence carriers
        if carrier in ["UPS", "FEDEX", "USPS"]:
            score += 0.1

        return min(score, 1.0)

    def parse_multiple_tracking_numbers(self, body: str) -> List[str]:
        """Extract multiple tracking numbers from email body."""
        tracking_numbers = []

        # Try each carrier pattern
        for carrier, pattern in self.tracking_patterns.items():
            if carrier != "GENERIC":
                matches = re.findall(pattern, body, re.IGNORECASE)
                tracking_numbers.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_numbers = []
        for number in tracking_numbers:
            if number not in seen:
                seen.add(number)
                unique_numbers.append(number)

        return unique_numbers

    def _should_use_llm(
        self, subject: str, sender: str, body: str, parsed_data: ParsedEmailData
    ) -> bool:
        """
        Determine if we should use LLM for parsing this email.

        This implements the expert strategy of using LLM for section classification
        to identify likely shipping-related blocks for targeted extraction.
        """
        # Always use LLM for complex or malformed emails
        if self._has_complex_format(body):
            logger.debug("LLM needed: Complex email format detected")
            return True

        # Use LLM if we have missing critical fields
        missing_critical_fields = []

        if not parsed_data.tracking_number:
            missing_critical_fields.append("tracking number")
        if not parsed_data.order_number:
            missing_critical_fields.append("order number")
        if not parsed_data.package_description:
            missing_critical_fields.append("package description")
        if not parsed_data.recipient_name:
            missing_critical_fields.append("recipient name")

        # If we're missing 2 or more critical fields, use LLM
        if len(missing_critical_fields) >= 2:
            logger.info(f"Using LLM for email - Subject: {subject}, Sender: {sender}")
            return True

        # Use LLM for section classification on all emails to improve accuracy
        # This implements the expert strategy of using LLM to segment email content
        # into labeled sections for better extraction
        return True

    def _has_complex_format(self, body: str) -> bool:
        """Check if email has complex formatting that might need LLM processing."""
        # Since we now convert to markdown first, we check for markdown complexity
        # instead of HTML complexity

        # Check for complex markdown structures
        has_tables = body.count("|") > 10  # Markdown tables
        has_lists = body.count("- ") > 5 or body.count("* ") > 5  # Markdown lists
        has_links = body.count("[") > 5 and body.count("](") > 5  # Markdown links

        # Check for multiple languages or unusual characters
        has_unicode = bool(re.search(r"[^\x00-\x7F]", body))

        # Check for complex formatting patterns
        has_complex_formatting = (
            has_tables
            or has_lists
            or has_links
            or has_unicode
            or body.count("\n\n") > 10  # Many paragraph breaks
        )

        return has_complex_formatting

    def _validate_email_content_for_llm(self, body: str) -> tuple[bool, list[str]]:
        """
        Validate email content before sending to LLM to ensure it's safe and clean.

        Args:
            body: Email body content (should be cleaned markdown)

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Since we now convert to markdown first, most dangerous content should be removed
        # But we still check for any remaining issues

        # Check for potentially dangerous content that might have slipped through
        if re.search(r"<script[^>]*>", body, re.IGNORECASE):
            issues.append("Contains JavaScript code")

        if re.search(r"javascript:", body, re.IGNORECASE):
            issues.append("Contains JavaScript URLs")

        if re.search(r"data:text/html", body, re.IGNORECASE):
            issues.append("Contains embedded HTML data URLs")

        if re.search(r"data:application/", body, re.IGNORECASE):
            issues.append("Contains embedded application data")

        # Check for excessive encoding artifacts (should be minimal after cleaning)
        if body.count("=") > len(body) * 0.1:  # More than 10% equals signs
            issues.append("Contains excessive encoding artifacts")

        # Check for base64 encoded content (should be removed during cleaning)
        if re.search(r"[A-Za-z0-9+/]{50,}={0,2}", body):
            issues.append("Contains base64 encoded content")

        # Check for email headers and boundaries (should be removed during cleaning)
        if re.search(r"------=_Part_\d+_\d+\.\d+", body):
            issues.append("Contains MIME boundaries")

        if re.search(r"Content-Type:|Content-Transfer-Encoding:", body, re.IGNORECASE):
            issues.append("Contains email headers")

        # Check for excessive HTML entities (should be minimal after cleaning)
        if body.count("&") > len(body) * 0.05:  # More than 5% ampersands
            issues.append("Contains excessive HTML entities")

        # Check for extremely long content
        if len(body) > 50000:  # 50KB limit
            issues.append("Content too long (exceeds 50KB)")

        # Check for suspicious patterns
        if re.search(r"eval\s*\(", body, re.IGNORECASE):
            issues.append("Contains eval() function calls")

        if re.search(r"document\.", body, re.IGNORECASE):
            issues.append("Contains DOM manipulation code")

        is_valid = len(issues) == 0
        return is_valid, issues

    def parse_with_llm_fallback(
        self,
        subject: str,
        sender: str,
        body: str,
        email_date: Optional[str] = None,
    ) -> ParsedEmailData:
        """
        Parse email with LLM fallback for complex cases.

        This method first tries regex-based parsing, then falls back to LLM
        if the email is complex or has low confidence.
        """
        # First, try regex-based parsing (which now includes robust MIME decoding)
        parsed_data = self.parse_email(subject, sender, body, email_date)

        # Check if we should use LLM
        should_use_llm = self._should_use_llm(subject, sender, body, parsed_data)

        if not should_use_llm:
            logger.info(
                f"LLM not needed for email - Subject: {subject}, Sender: {sender}"
            )
            logger.info(
                f"Reason: Regex parsing sufficient (confidence: {parsed_data.confidence_score:.2f}, carrier: {parsed_data.carrier})"
            )
            return parsed_data

        logger.info(f"Using LLM for email - Subject: {subject}, Sender: {sender}")

        # Import LLM parser here to avoid circular imports
        from services.shipments.llm_parser import LLMEmailParser

        # Use our markdown conversion instead of LLM parser's cleaning
        # This ensures consistency between regex and LLM parsing
        cleaned_body = self._convert_to_markdown(body)
        logger.info(
            f"Converted body to markdown for LLM processing (length: {len(cleaned_body)})"
        )

        # Validate the cleaned content
        is_valid, issues = self._validate_email_content_for_llm(cleaned_body)

        if not is_valid:
            logger.error(
                f"Email content validation failed for LLM processing. Issues: {', '.join(issues)}"
            )
            logger.error(f"Subject: {subject}, Sender: {sender}")
            logger.error(f"Cleaned content: {cleaned_body}...")
            # Continue with regex results only
            return parsed_data

        # Content validation passed, proceed with LLM processing
        logger.info("Email content validation passed, proceeding with LLM processing")

        try:
            # Create LLM parser instance
            llm_parser = LLMEmailParser()

            # Determine what we already know
            known_carrier = (
                parsed_data.carrier if parsed_data.carrier != "UNKNOWN" else None
            )
            known_tracking = (
                parsed_data.tracking_number if parsed_data.tracking_number else None
            )
            known_order = parsed_data.order_number if parsed_data.order_number else None

            logger.info(
                f"Known context - Carrier: {known_carrier}, Tracking: {known_tracking}, Order: {known_order}"
            )

            # Determine what fields are missing
            missing_fields = []
            if not parsed_data.status:
                missing_fields.append("shipment status")
            if not parsed_data.estimated_delivery:
                missing_fields.append("estimated delivery date")
            if not parsed_data.vendor_name:
                missing_fields.append("vendor name")
            if not parsed_data.package_description:
                missing_fields.append("package description")
            if not parsed_data.recipient_name:
                missing_fields.append("recipient name")

            logger.info(f"Missing fields to extract: {missing_fields}")

            # Use LLM to fill in missing information
            if known_tracking or known_order:
                # We have some information, use context-aware parsing
                logger.info("Using context-aware LLM parsing")

                # Log the email body being sent to LLM for debugging
                logger.info("=== EMAIL BODY BEING SENT TO LLM ===")
                logger.info(f"Subject: {subject}")
                logger.info(f"Sender: {sender}")
                logger.info(f"Body length: {len(cleaned_body)} characters")
                logger.info(f"Body: \n{cleaned_body}")
                # logger.info(f"Body preview (first 500 chars): {cleaned_body[:500]}...")
                # logger.info(f"Body preview (last 500 chars): ...{cleaned_body[-500:]}")
                logger.info("=== END EMAIL BODY ===")

                llm_info = llm_parser.parse_email_with_context(
                    subject=subject,
                    sender=sender,
                    body=cleaned_body,
                    email_date=email_date,
                    known_carrier=known_carrier,
                    known_tracking_number=known_tracking,
                    known_order_number=known_order,
                    missing_fields=missing_fields,
                )
            else:
                # No tracking number found, use basic parsing
                logger.info("Using basic LLM parsing (no tracking/order context)")
                llm_info = llm_parser.parse_email_basic(
                    subject=subject,
                    sender=sender,
                    body=cleaned_body,
                    email_date=email_date,
                )

            # Log LLM parsing results
            if llm_info:
                extracted_fields = []
                if llm_info.shipment_status:
                    extracted_fields.append(f"status={llm_info.shipment_status}")
                if llm_info.vendor_name:
                    extracted_fields.append(f"vendor={llm_info.vendor_name}")
                if llm_info.recipient_name:
                    extracted_fields.append(f"recipient={llm_info.recipient_name}")
                if llm_info.package_description:
                    extracted_fields.append(
                        f"description={llm_info.package_description}"
                    )
                if llm_info.estimated_delivery:
                    extracted_fields.append(f"delivery={llm_info.estimated_delivery}")

                logger.info(
                    f"LLM parsing successful - extracted: {', '.join(extracted_fields) if extracted_fields else 'no fields'}"
                )
                parsed_data = self._merge_llm_results(parsed_data, llm_info)
            else:
                logger.warning("LLM parsing returned no results")

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            import traceback

            logger.error(f"LLM parsing exception details: {traceback.format_exc()}")
            # Continue with regex results if LLM fails

        return parsed_data

    def _merge_llm_results(
        self, parsed_data: ParsedEmailData, llm_info
    ) -> ParsedEmailData:
        """
        Merge LLM parsing results with regex parsing results.

        Args:
            parsed_data: Results from regex parsing
            llm_info: Results from LLM parsing

        Returns:
            Merged ParsedEmailData
        """
        # Update status - use LLM value if it's different or if we don't have one
        logger.info(
            f"Status - Parsed: {parsed_data.status}, LLM: {llm_info.shipment_status}"
        )
        if llm_info.shipment_status:
            # Handle both enum and string values
            if hasattr(llm_info.shipment_status, "value"):
                llm_status = llm_info.shipment_status.value.replace("_", " ").title()
            else:
                llm_status = str(llm_info.shipment_status).replace("_", " ").title()

            # Update if we don't have a status or if LLM status is different
            if not parsed_data.status or parsed_data.status != llm_status:
                parsed_data.status = llm_status
                logger.info(f"Updated status to: {llm_status}")

        # Update estimated delivery - use LLM value if it's different or if we don't have one
        logger.info(
            f"Estimated Delivery - Parsed: {parsed_data.estimated_delivery}, LLM: {llm_info.estimated_delivery}"
        )
        if llm_info.estimated_delivery:
            llm_date = llm_info.estimated_delivery.strftime("%Y-%m-%d")
            if (
                not parsed_data.estimated_delivery
                or parsed_data.estimated_delivery != llm_date
            ):
                parsed_data.estimated_delivery = llm_date
                logger.info(f"Updated estimated delivery to: {llm_date}")

        # Update vendor name if LLM found one and we didn't
        logger.info(
            f"Vendor Name - Parsed: {parsed_data.vendor_name}, LLM: {llm_info.vendor_name}"
        )
        if not parsed_data.vendor_name and llm_info.vendor_name:
            parsed_data.vendor_name = llm_info.vendor_name
            logger.info(f"Updated vendor name to: {llm_info.vendor_name}")

        # Update package description if LLM found one and we didn't
        logger.info(
            f"Package Description - Parsed: {parsed_data.package_description}, LLM: {llm_info.package_description}"
        )
        if not parsed_data.package_description and llm_info.package_description:
            parsed_data.package_description = llm_info.package_description
            logger.info(
                f"Updated package description to: {llm_info.package_description}"
            )

        # Update recipient name if LLM found one and we didn't
        logger.info(
            f"Recipient Name - Parsed: {parsed_data.recipient_name}, LLM: {llm_info.recipient_name}"
        )
        if not parsed_data.recipient_name and llm_info.recipient_name:
            parsed_data.recipient_name = llm_info.recipient_name
            logger.info(f"Updated recipient name to: {llm_info.recipient_name}")

        # Update tracking number if LLM found one and we didn't
        logger.info(
            f"Tracking Number - Parsed: {parsed_data.tracking_number}, LLM: {llm_info.tracking_number}"
        )
        if not parsed_data.tracking_number and llm_info.tracking_number:
            parsed_data.tracking_number = llm_info.tracking_number
            logger.info(f"Updated tracking number to: {llm_info.tracking_number}")

        # Update order number if LLM found one and we didn't
        logger.info(
            f"Order Number - Parsed: {parsed_data.order_number}, LLM: {llm_info.order_number}"
        )
        if not parsed_data.order_number and llm_info.order_number:
            parsed_data.order_number = llm_info.order_number
            logger.info(f"Updated order number to: {llm_info.order_number}")

        # Update confidence score if LLM provided one
        logger.info(
            f"Confidence Score - Parsed: {parsed_data.confidence_score}, LLM: {llm_info.confidence_score}"
        )
        if llm_info.confidence_score is not None:
            # Blend confidence scores (give more weight to LLM if we have low confidence)
            if parsed_data.confidence_score < 0.3:
                parsed_data.confidence_score = llm_info.confidence_score
                logger.info(f"Updated confidence score to: {llm_info.confidence_score}")
            else:
                # Average the scores
                parsed_data.confidence_score = (
                    parsed_data.confidence_score + llm_info.confidence_score
                ) / 2
                logger.info(
                    f"Blended confidence score to: {parsed_data.confidence_score}"
                )

        return parsed_data

    def _extract_urls_robustly(self, html_content: str) -> List[str]:
        """
        Robustly extract URLs from complex HTML email content.

        Handles:
        - Quoted-printable line breaks (=\\r\\n)
        - HTML tag interruptions (<wbr>, &shy;, etc.)
        - Line wrapping in raw EML or rendered HTML
        - JavaScript obfuscation
        - Visual truncation vs raw data
        - HTML entities and special characters
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning(
                "BeautifulSoup not available, falling back to regex extraction"
            )
            return self._extract_urls_with_regex(html_content)

        urls = []

        # Step 1: Parse HTML with BeautifulSoup to handle tag interruptions
        try:
            # Preprocess HTML to fix common malformed HTML issues
            html_content = self._preprocess_html_content(html_content)
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            logger.warning(f"HTML parsing failed: {e}, falling back to regex")
            return self._extract_urls_with_regex(html_content)

        # Step 2: Extract URLs from href attributes (most reliable)
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            if href and href.startswith(("http://", "https://")):
                # Clean the URL
                cleaned_url = self._clean_extracted_url(href)
                if cleaned_url and cleaned_url not in urls:
                    urls.append(cleaned_url)

        # Step 3: Extract URLs from onclick handlers and JavaScript
        for element in soup.find_all(attrs={"onclick": True}):
            onclick = element.get("onclick", "")
            js_urls = self._extract_urls_from_javascript(onclick)
            for url in js_urls:
                cleaned_url = self._clean_extracted_url(url)
                if cleaned_url and cleaned_url not in urls:
                    urls.append(cleaned_url)

        # Step 4: Extract URLs from text content (fallback for non-linked URLs)
        text_urls = self._extract_urls_from_text_content(html_content)
        for url in text_urls:
            cleaned_url = self._clean_extracted_url(url)
            if cleaned_url and cleaned_url not in urls:
                urls.append(cleaned_url)

        return urls

    def _extract_urls_with_regex(self, content: str) -> List[str]:
        """Fallback regex-based URL extraction with QP handling."""
        urls = []

        # Handle quoted-printable line breaks first
        # Join lines that end with = (soft line breaks)
        content = re.sub(r"=\r?\n", "", content)

        # More robust regex pattern that handles various edge cases
        url_patterns = [
            # Standard URLs
            r'https?://[^\s"\'<>]+',
            # URLs with potential HTML entities
            r'https?://[^\s"\'<>]+(?:&[a-zA-Z0-9]+;)*',
            # URLs that might be broken by HTML tags
            r'https?://[^\s"\'<>]+(?:<[^>]*>[^\s"\'<>]*)*',
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean HTML tags from the URL
                cleaned_match = re.sub(r"<[^>]*>", "", match)
                # Clean HTML entities
                cleaned_match = self._decode_html_entities(cleaned_match)
                # Clean trailing punctuation
                cleaned_match = self._clean_trailing_punctuation(cleaned_match)

                if cleaned_match and self._is_valid_url(cleaned_match):
                    urls.append(cleaned_match)

        return list(set(urls))  # Remove duplicates

    def _extract_urls_from_javascript(self, js_code: str) -> List[str]:
        """Extract URLs from JavaScript code (onclick handlers, etc.)."""
        urls = []

        # Common patterns in JavaScript
        js_patterns = [
            r'window\.open\([\'"]([^\'"]+)[\'"]',
            r'location\.href\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'window\.location\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'url\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'redirect\s*[\'"]([^\'"]+)[\'"]',
        ]

        for pattern in js_patterns:
            matches = re.findall(pattern, js_code, re.IGNORECASE)
            for match in matches:
                if match.startswith(("http://", "https://")):
                    urls.append(match)

        return urls

    def _extract_urls_from_text_content(self, content: str) -> List[str]:
        """Extract URLs from text content, handling QP encoding."""
        urls = []

        # Handle quoted-printable encoding
        content = self._decode_quoted_printable(content)

        # Remove HTML tags for text-based extraction
        content = re.sub(r"<[^>]*>", " ", content)

        # Extract URLs with context awareness
        url_patterns = [
            # Amazon-specific patterns (most important for our use case)
            r'https?://[^\s"\'<>]*amazon\.com[^\s"\'<>]*progress-tracker[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*amazon\.com[^\s"\'<>]*order-details[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*amazon\.com[^\s"\'<>]*gp/css/order-details[^\s"\'<>]*',
            # General tracking URLs
            r'https?://[^\s"\'<>]*track[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*ship[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*deliver[^\s"\'<>]*',
            # Carrier-specific patterns
            r'https?://[^\s"\'<>]*ups\.com[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*fedex\.com[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*usps\.com[^\s"\'<>]*',
            r'https?://[^\s"\'<>]*dhl\.com[^\s"\'<>]*',
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                cleaned_url = self._clean_extracted_url(match)
                if cleaned_url and cleaned_url not in urls:
                    urls.append(cleaned_url)

        return urls

    def _decode_quoted_printable(self, content: str) -> str:
        """Decode quoted-printable encoding, handling soft line breaks and different encodings."""
        try:
            import quopri

            # Join soft line breaks first
            content = re.sub(r"=\r?\n", "", content)

            # Try to decode as bytes first, then handle different encodings
            try:
                # If content contains non-ASCII, encode it first
                if not content.isascii():
                    # Try different encodings
                    for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
                        try:
                            encoded_content = content.encode(encoding, errors="ignore")
                            decoded = quopri.decodestring(encoded_content)
                            return decoded.decode("utf-8", errors="ignore")
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            continue

                # If content is ASCII or encoding attempts failed, try direct decoding
                decoded = quopri.decodestring(content.encode("ascii", errors="ignore"))
                return decoded.decode("utf-8", errors="ignore")

            except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
                # If all decoding attempts fail, just return the content with soft line breaks removed
                return content

        except Exception as e:
            logger.warning(f"QP decoding failed: {e}")
            # Fallback: just join soft line breaks
            return re.sub(r"=\r?\n", "", content)

    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities in text."""
        try:
            import html

            return html.unescape(text)
        except Exception:
            # Fallback for older Python versions

            entity_patterns = {
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&quot;": '"',
                "&#39;": "'",
                "&nbsp;": " ",
            }
            for entity, replacement in entity_patterns.items():
                text = text.replace(entity, replacement)
            return text

    def _clean_trailing_punctuation(self, url: str) -> str:
        """Remove trailing punctuation that might have been added during extraction."""
        # Common trailing characters that shouldn't be part of URLs
        trailing_chars = ".,;:!?)]}'\"`~"
        while url and url[-1] in trailing_chars:
            url = url[:-1]
        return url

    def _clean_extracted_url(self, url: str) -> str:
        """Clean and validate an extracted URL."""
        if not url:
            return ""

        # Remove HTML tags
        url = re.sub(r"<[^>]*>", "", url)

        # Decode HTML entities
        url = self._decode_html_entities(url)

        # Clean trailing punctuation
        url = self._clean_trailing_punctuation(url)

        # Remove whitespace
        url = url.strip()

        # Validate it's a proper URL
        if not self._is_valid_url(url):
            return ""

        return url

    def _is_valid_url(self, url: str) -> bool:
        """Check if a string is a valid URL."""
        if not url or len(url) < 10:
            return False

        # Must start with http:// or https://
        if not url.startswith(("http://", "https://")):
            return False

        # Must contain a domain
        if "." not in url.split("://", 1)[1].split("/", 1)[0]:
            return False

        # Must not contain obvious invalid characters
        invalid_chars = ["<", ">", '"', "'", "\n", "\r", "\t"]
        if any(char in url for char in invalid_chars):
            return False

        return True

    def _detect_carrier_from_sender(self, sender: str) -> Optional[str]:
        """Detect carrier from sender email domain"""
        for carrier, patterns in self.carrier_patterns.items():
            if any(domain in sender for domain in patterns.get("domains", [])):
                return carrier
        return None

    def _detect_carrier_from_tracking_number(
        self, tracking_number: str, body: str = ""
    ) -> Optional[str]:
        """Detect carrier from tracking number format"""
        if not tracking_number:
            return None

        # Remove any non-alphanumeric characters
        clean_number = re.sub(r"[^0-9A-Za-z]", "", tracking_number)

        # Special handling for 26-digit tracking numbers (UPS Mail Innovations vs USPS)
        if len(clean_number) == 26 and clean_number.isdigit():
            # Check if this is UPS Mail Innovations by looking for UPS context in the body
            body_lower = body.lower()
            if "ups.com" in body_lower or "united parcel service" in body_lower:
                return "ups"
            else:
                # Default to USPS for 26-digit numbers without UPS context
                return "usps"

        # Check each carrier's patterns
        for carrier, patterns in self.carrier_patterns.items():
            for pattern in patterns.get("tracking_patterns", []):
                if re.match(pattern, clean_number):
                    return carrier
        return None

    def _has_shipment_keywords(self, text: str) -> bool:
        """Check if text contains shipment-related keywords"""
        shipment_keywords = [
            "shipment",
            "package",
            "order",
            "delivery",
            "tracking",
            "shipped",
            "out for delivery",
            "in transit",
            "arrived",
        ]
        return any(keyword in text for keyword in shipment_keywords)

    def _extract_tracking_numbers(
        self, text: str, detected_carrier: Optional[str]
    ) -> List[str]:
        """Extract tracking numbers from text"""
        found_numbers = set()

        # Check carrier-specific patterns first
        if detected_carrier and detected_carrier in self.carrier_patterns:
            patterns = self.carrier_patterns[detected_carrier].get(
                "tracking_patterns", []
            )
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                # Normalize each found tracking number
                normalized_matches = [
                    normalize_tracking_number(match, detected_carrier)
                    for match in matches
                ]
                found_numbers.update(normalized_matches)

        # Check generic patterns from tracking_patterns
        for pattern in self.tracking_patterns.values():
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Normalize each found tracking number
            normalized_matches = [
                normalize_tracking_number(match, detected_carrier) for match in matches
            ]
            found_numbers.update(normalized_matches)

        return list(found_numbers)

    def _generate_suggested_package_data(
        self, tracking_number: str, carrier: Optional[str], subject: str, body: str
    ) -> Dict:
        """Generate suggested package data for creating a tracking entry"""
        # Ensure tracking number is normalized
        normalized_tracking = normalize_tracking_number(tracking_number, carrier)

        suggested_data = {
            "tracking_number": normalized_tracking,
            "carrier": carrier or "unknown",
            "status": "pending",
        }

        # Try to extract order number from subject or body
        order_patterns = [
            r"order[:\s#]*([A-Z0-9\-]+)",
            r"order[:\s#]*#([A-Z0-9\-]+)",
            r"#([A-Z0-9\-]{10,})",
        ]

        for pattern in order_patterns:
            match = re.search(pattern, subject + " " + body, re.IGNORECASE)
            if match:
                suggested_data["order_number"] = match.group(1)
                break

        # Try to extract shipper name from sender domain or common patterns
        if carrier == "amazon":
            suggested_data["shipper_name"] = "Amazon"
        elif carrier == "ups":
            suggested_data["shipper_name"] = "UPS"
        elif carrier == "fedex":
            suggested_data["shipper_name"] = "FedEx"
        elif carrier == "usps":
            suggested_data["shipper_name"] = "USPS"
        elif carrier == "dhl":
            suggested_data["shipper_name"] = "DHL"

        # Try to extract package description from subject
        if subject:
            # Remove common prefixes and clean up
            clean_subject = re.sub(
                r"^(Your |Order |Package |Shipment |Tracking )",
                "",
                subject,
                flags=re.IGNORECASE,
            )
            clean_subject = re.sub(
                r" has (shipped|been shipped|arrived|been delivered)",
                "",
                clean_subject,
                flags=re.IGNORECASE,
            )
            if clean_subject and len(clean_subject) > 5:
                suggested_data["package_description"] = clean_subject

        return suggested_data
