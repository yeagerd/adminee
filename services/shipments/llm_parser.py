"""
LLM-based email parser for shipping notifications.

This module provides LLM-powered parsing capabilities for shipping emails
using the Instructor package and structured data models.
"""

import json
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from services.common.llm_manager import get_llm_manager
from services.common.logging_config import get_logger
from services.shipments.llm_models import ShipmentInfo, ShipmentStatus
from services.shipments.settings import get_settings

logger = get_logger(__name__)


class LLMEmailParser:
    """LLM-based parser for shipping notification emails."""

    def __init__(self):
        """Initialize the LLM parser with settings."""
        self.settings = get_settings()
        self.llm_manager = get_llm_manager()

        # Get LLM instance
        self.llm = self.llm_manager.get_llm(
            model=self.settings.llm_model,
            provider=self.settings.llm_provider,
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=1000,
        )

    def clean_email_content(self, content: str) -> str:
        """
        Clean email content by removing email artifacts, encoding issues, and formatting noise.

        Args:
            content: Raw email content (HTML or plain text)

        Returns:
            Clean, readable text content
        """
        if not content:
            return ""

        # Step 1: Extract tracking numbers from URLs before cleaning
        # This preserves tracking numbers that might be lost during HTML-to-markdown conversion
        tracking_numbers_in_urls = []
        if "<" in content and ">" in content:
            # Look for tracking numbers in href attributes
            url_tracking_patterns = [
                r'href\s*=\s*["\'][^"\']*tracknum=([^&"\']+)["\']',  # tracknum parameter
                r'href\s*=\s*["\'][^"\']*tracking=([^&"\']+)["\']',  # tracking parameter
                r'href\s*=\s*["\'][^"\']*track=([^&"\']+)["\']',  # track parameter
                r'href\s*=\s*["\'][^"\']*/([A-Z0-9]{8,20})["\']',  # tracking number in path
            ]

            for pattern in url_tracking_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 8 and not re.search(r"[=&\?]", match):
                        tracking_numbers_in_urls.append(match)

        # Step 2: Remove email headers and boundaries
        # Remove MIME boundaries and headers
        content = re.sub(r"------=_Part_\d+_\d+\.\d+.*?\n", "", content)
        content = re.sub(r"Content-Type:.*?\n", "", content)
        content = re.sub(r"Content-Transfer-Encoding:.*?\n", "", content)
        content = re.sub(r"charset=.*?\n", "", content)

        # Step 3: Decode quoted-printable encoding
        # Replace =XX with actual characters
        content = re.sub(
            r"=([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), content
        )
        # Remove line continuations (= at end of line)
        content = re.sub(r"=\n", "", content)
        # Remove remaining = characters that are likely encoding artifacts
        content = re.sub(r"=\s+", " ", content)  # = followed by whitespace
        content = re.sub(r"\s+=", " ", content)  # whitespace followed by =
        content = re.sub(r"=$", "", content, flags=re.MULTILINE)  # = at end of line

        # Step 4: Remove base64 encoded content
        # Remove base64 encoded images and attachments
        content = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[IMAGE]", content)
        content = re.sub(r"[A-Za-z0-9+/]{50,}={0,2}", "[ENCODED_DATA]", content)

        # Step 5: Remove HTML entities and special characters
        # Remove common HTML entities
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

        # Remove email headers and metadata
        content = re.sub(r"x-[a-zA-Z-]+[^\\n]*", "", content, flags=re.IGNORECASE)
        content = re.sub(
            r"[a-zA-Z-]+-[a-zA-Z-]+[^\\n]*", "", content
        )  # Generic header patterns

        # Step 6: Remove CSS and styling
        # Remove CSS blocks
        content = re.sub(
            r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE
        )
        # Remove inline styles
        content = re.sub(
            r'style\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE
        )
        # Remove CSS classes
        content = re.sub(
            r'class\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE
        )

        # Remove CSS rules and properties (even when not in style tags)
        content = re.sub(r"[a-zA-Z-]+\s*:\s*[^;]+;", "", content)  # CSS properties
        content = re.sub(
            r"@media[^{]*\{[^}]*\}", "", content, flags=re.DOTALL
        )  # Media queries
        content = re.sub(r"@import[^;]+;", "", content)  # Import statements
        content = re.sub(
            r"#[a-zA-Z][a-zA-Z0-9_-]*\s*\{[^}]*\}", "", content, flags=re.DOTALL
        )  # ID selectors
        content = re.sub(
            r"\.[a-zA-Z][a-zA-Z0-9_-]*\s*\{[^}]*\}", "", content, flags=re.DOTALL
        )  # Class selectors
        content = re.sub(
            r"[a-zA-Z][a-zA-Z0-9_-]*\s*\{[^}]*\}", "", content, flags=re.DOTALL
        )  # Element selectors

        # Step 7: Remove email-specific artifacts
        # Remove tracking pixels and analytics
        content = re.sub(
            r'<img[^>]*width\s*=\s*["\']?1["\']?[^>]*>',
            "",
            content,
            flags=re.IGNORECASE,
        )
        # Remove empty divs and spans
        content = re.sub(r"<(div|span)[^>]*>\s*</\1>", "", content, flags=re.IGNORECASE)

        # Step 8: Extract text content if it's HTML
        if "<" in content and ">" in content:
            try:
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(content, "html.parser")

                # Remove script, style, and other non-content elements
                for element in soup(["script", "style", "meta", "link", "head"]):
                    element.decompose()

                # Convert to markdown
                markdown_text = md(str(soup), heading_style="ATX")

                # Clean up the markdown
                markdown_text = re.sub(
                    r"\n\s*\n", "\n\n", markdown_text
                )  # Remove excessive newlines
                markdown_text = re.sub(
                    r"[ \t]+", " ", markdown_text
                )  # Normalize whitespace

                # Clean up messy markdown artifacts
                markdown_text = re.sub(
                    r"\|\s*\|\s*\|", "", markdown_text
                )  # Remove empty table markers
                markdown_text = re.sub(
                    r"---\s*\|", "", markdown_text
                )  # Remove table separators
                markdown_text = re.sub(
                    r"\*\*\*\*", "", markdown_text
                )  # Remove excessive asterisks
                markdown_text = re.sub(
                    r"\]\s*\(\s*\)", "", markdown_text
                )  # Remove empty links
                markdown_text = re.sub(
                    r"@media[^}]*\}", "", markdown_text
                )  # Remove CSS media queries
                markdown_text = re.sub(
                    r'style="[^"]*"', "", markdown_text
                )  # Remove inline styles

                markdown_text = markdown_text.strip()

                content = markdown_text

            except Exception as e:
                logger.warning(f"Failed to convert HTML to markdown: {e}")
                # Fallback: just strip HTML tags
                content = re.sub(r"<[^>]+>", "", content)

        # Step 9: Add back tracking numbers found in URLs if they're not already in the text
        if tracking_numbers_in_urls:
            # Check if any of the tracking numbers are already in the cleaned content
            existing_tracking = []
            for tracking_num in tracking_numbers_in_urls:
                if tracking_num in content:
                    existing_tracking.append(tracking_num)

            # Add missing tracking numbers to the content
            missing_tracking = [
                tn for tn in tracking_numbers_in_urls if tn not in existing_tracking
            ]
            if missing_tracking:
                # Add tracking numbers in a more natural way
                tracking_info = f"\n\nTracking Numbers: {', '.join(missing_tracking)}"
                content += tracking_info

        # Step 10: Final cleanup
        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content)
        # Remove empty lines
        content = re.sub(r"\n\s*\n", "\n", content)
        # Remove leading/trailing whitespace
        content = content.strip()

        # Step 11: Truncate if too long (LLM context limits)
        if len(content) > 8000:
            content = content[:8000] + "\n\n[Content truncated due to length]"

        return content

    def html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML email content to clean markdown.

        Args:
            html_content: Raw HTML content from email

        Returns:
            Clean markdown text
        """
        # Use the new comprehensive cleaning function
        return self.clean_email_content(html_content)

    def extract_tracking_numbers_from_text(self, text: str) -> list[tuple[str, str]]:
        """
        Extract tracking numbers from text using carrier-specific patterns.

        Args:
            text: Clean text content to search

        Returns:
            List of (tracking_number, carrier) tuples
        """
        tracking_patterns = [
            # OnTrac: C + 15 digits
            (r"\b(C\d{15})\b", "ONTRAC"),
            # UPS: 1Z + 16 alphanumeric
            (r"\b(1Z[A-Z0-9]{16})\b", "UPS"),
            # USPS: 20 digits
            (r"\b(\d{20})\b", "USPS"),
            # FedEx: 12 digits
            (r"\b(\d{12})\b", "FEDEX"),
            # Generic fallback (but more restrictive)
            (r"\b([A-Z0-9]{8,20})\b", "UNKNOWN"),
        ]

        found_tracking = []
        for pattern, carrier in tracking_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Additional validation: don't accept strings that look like URL parameters
                if not re.search(r"[=&\?]", match) and len(match) >= 8:
                    found_tracking.append((match, carrier))

        return found_tracking

    def parse_email_basic(
        self, subject: str, sender: str, body: str, email_date: Optional[str] = None
    ) -> Optional[ShipmentInfo]:
        """
        Parse email to determine if it's a shipping-related email and extract basic info.

        This is used when we don't have a tracking number or obvious tracking link.

        Args:
            subject: Email subject line
            sender: Sender email address
            body: Email body (HTML or plain text)
            email_date: Email send date in ISO format for relative date resolution

        Returns:
            ShipmentInfo with extracted data, or None if parsing failed
        """
        try:
            # Clean the email content to remove artifacts and formatting noise
            body_md = self.clean_email_content(body)

            # Create prompt for basic parsing
            email_date_context = ""
            if email_date:
                try:
                    from datetime import datetime

                    # Parse the email date and format it in a human-readable way
                    email_datetime = datetime.fromisoformat(
                        email_date.replace("Z", "+00:00")
                    )
                    formatted_date = email_datetime.strftime(
                        "%A, %B %d, %Y"
                    )  # e.g., "Tuesday, July 15, 2025"
                    email_date_context = f"\nEMAIL DATE: {formatted_date} (use this as reference for relative dates like 'today', 'tomorrow', 'next week', 'Friday', etc.)"
                except Exception:
                    # Fallback to original format if parsing fails
                    email_date_context = f"\nEMAIL DATE: {email_date} (use this as reference for relative dates like 'today', 'tomorrow', 'next week')"

            prompt = f"""
You are an expert at analyzing shipping and order notification emails. 

Please analyze the following email and extract any shipping-related information:

SUBJECT: {subject}
SENDER: {sender}{email_date_context}
BODY:
{body_md}

Extract the following information if present:
- Whether this is an order/shipment update email
- Order number or order ID
- Current shipment status (use one of: confirmed, pending, packing, shipped, in_transit, out_for_delivery, delivered, exception, cancelled, returned)
- Estimated delivery date
- Vendor/retailer name
- Package description
- Recipient name
- Any tracking numbers
- Your confidence in the extracted information

If this is not a shipping-related email, set is_order_update to false.
If you're unsure about any field, leave it as null.
For dates, use YYYY-MM-DD format. When you see relative dates like "today", "tomorrow", "next week", etc., calculate the actual date based on the email date provided.
For confidence score, use a value between 0.0 and 1.0.

IMPORTANT: For shipment status, use the exact values: confirmed, pending, packing, shipped, in_transit, out_for_delivery, delivered, exception, cancelled, or returned.
"""

            # Extract tracking numbers directly from cleaned email content
            tracking_numbers = self.extract_tracking_numbers_from_text(body_md)
            logger.info(f"Found tracking numbers in email content: {tracking_numbers}")

            # Use Instructor to get structured response
            response = self.llm.complete(prompt)

            # Parse the response (Instructor will handle the structured extraction)
            # For now, we'll manually parse the response since we're not using the patch decorator
            parsed_info = self._parse_llm_response(response)

            # If we found tracking numbers in the email content but not in LLM response, use them
            if parsed_info and tracking_numbers and not parsed_info.tracking_number:
                best_tracking = tracking_numbers[0]  # Use the first one found
                parsed_info.tracking_number = best_tracking[0]
                logger.info(
                    f"Using tracking number from email content: {best_tracking[0]} ({best_tracking[1]})"
                )

            return parsed_info

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return None

    def parse_email_with_context(
        self,
        subject: str,
        sender: str,
        body: str,
        email_date: Optional[str] = None,
        known_carrier: Optional[str] = None,
        known_tracking_number: Optional[str] = None,
        known_order_number: Optional[str] = None,
        missing_fields: Optional[list[str]] = None,
    ) -> Optional[ShipmentInfo]:
        """
        Parse email with context about what we already know.

        This is used when we have some information from regex parsing and want
        the LLM to fill in missing details.

        Args:
            subject: Email subject line
            sender: Sender email address
            body: Email body (HTML or plain text)
            email_date: Email send date in ISO format for relative date resolution
            known_carrier: Carrier that was already detected
            known_tracking_number: Tracking number that was already extracted
            known_order_number: Order number that was already extracted
            missing_fields: List of fields we want the LLM to extract

        Returns:
            ShipmentInfo with extracted data, or None if parsing failed
        """
        try:
            # Clean the email content to remove artifacts and formatting noise
            body_md = self.clean_email_content(body)

            # Build context information
            context_parts = []
            if known_carrier:
                context_parts.append(f"Carrier: {known_carrier}")
            if known_tracking_number:
                context_parts.append(f"Tracking Number: {known_tracking_number}")
            if known_order_number:
                context_parts.append(f"Order Number: {known_order_number}")

            context_str = (
                "\n".join(context_parts)
                if context_parts
                else "No information already extracted"
            )

            # Build extraction instructions
            if missing_fields:
                extract_instructions = f"Please extract: {', '.join(missing_fields)}"
            else:
                extract_instructions = "Please extract any missing shipping information"

            # Create prompt for context-aware parsing
            email_date_context = ""
            if email_date:
                try:
                    from datetime import datetime

                    # Parse the email date and format it in a human-readable way
                    email_datetime = datetime.fromisoformat(
                        email_date.replace("Z", "+00:00")
                    )
                    formatted_date = email_datetime.strftime(
                        "%A, %B %d, %Y"
                    )  # e.g., "Tuesday, July 15, 2025"
                    email_date_context = f"\nEMAIL DATE: {formatted_date} (use this as reference for relative dates like 'today', 'tomorrow', 'next week', 'Friday', etc.)"
                except Exception:
                    # Fallback to original format if parsing fails
                    email_date_context = f"\nEMAIL DATE: {email_date} (use this as reference for relative dates like 'today', 'tomorrow', 'next week')"

            prompt = f"""
You are an expert at analyzing shipping and order notification emails.

We have already extracted some information from this email:
{context_str}

Please analyze the following email and extract the missing information:

SUBJECT: {subject}
SENDER: {sender}{email_date_context}
BODY:
{body_md}

{extract_instructions}

Extract the following information if present and not already known:
- Current shipment status (use one of: confirmed, pending, packing, shipped, in_transit, out_for_delivery, delivered, exception, cancelled, returned)
- Estimated delivery date
- Vendor/retailer name
- Package description
- Recipient name
- Any additional tracking numbers
- Your confidence in the extracted information

If you're unsure about any field, leave it as null.
For dates, use YYYY-MM-DD format. When you see relative dates like "today", "tomorrow", "next week", etc., calculate the actual date based on the email date provided.
For confidence score, use a value between 0.0 and 1.0.

IMPORTANT: For shipment status, use the exact values: confirmed, pending, packing, shipped, in_transit, out_for_delivery, delivered, exception, cancelled, or returned.
"""

            # Use Instructor to get structured response
            response = self.llm.complete(prompt)

            # Parse the response
            return self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"LLM parsing with context failed: {e}")
            return None

    def _parse_llm_response(self, response: str) -> Optional[ShipmentInfo]:
        """
        Parse the LLM response into a ShipmentInfo object.

        This is a fallback method when Instructor structured extraction isn't available.

        Args:
            response: Raw LLM response text

        Returns:
            ShipmentInfo object with extracted data
        """
        try:
            # Check if response is None or empty
            if not response or not response.strip():
                logger.warning("LLM response is None or empty")
                return None

            # For now, we'll create a basic ShipmentInfo object
            # In a full implementation, we'd use Instructor's structured extraction
            info = ShipmentInfo()

            # First try to extract JSON from the response
            # Look for JSON blocks with ```json or just { }
            json_patterns = [
                r"```json\s*(\{.*?\})\s*```",  # JSON in code blocks
                r'\{[^{}]*"shipment_status"[^{}]*\}',  # JSON with shipment_status
                r'\{[^{}]*"vendor"[^{}]*\}',  # JSON with vendor
            ]

            json_data = None
            for pattern in json_patterns:
                json_match = re.search(pattern, response, re.DOTALL)
                if json_match:
                    try:

                        json_str = (
                            json_match.group(1)
                            if pattern.startswith("```json")
                            else json_match.group(0)
                        )
                        json_data = json.loads(json_str)
                        logger.info(f"Found JSON data: {json_str[:100]}...")
                        break
                    except json.JSONDecodeError:
                        continue

            # Extract data from JSON - only use non-null, non-numeric values
            if json_data:
                if (
                    "shipment_status" in json_data
                    and json_data["shipment_status"]
                    and json_data["shipment_status"] != "null"
                ):
                    try:
                        info.shipment_status = ShipmentStatus(
                            json_data["shipment_status"]
                        )
                        logger.info(
                            f"Found JSON status: {json_data['shipment_status']}"
                        )
                    except ValueError:
                        logger.warning(
                            f"Unknown JSON status value: {json_data['shipment_status']}"
                        )

                if (
                    "vendor" in json_data
                    and json_data["vendor"]
                    and json_data["vendor"] != "null"
                    and not isinstance(json_data["vendor"], (int, float))
                ):
                    info.vendor_name = json_data["vendor"]
                    logger.info(f"Found JSON vendor: {json_data['vendor']}")

                if (
                    "package_description" in json_data
                    and json_data["package_description"]
                    and json_data["package_description"] != "null"
                ):
                    info.package_description = json_data["package_description"]
                    logger.info(
                        f"Found JSON package description: {json_data['package_description']}"
                    )

                if (
                    "recipient_name" in json_data
                    and json_data["recipient_name"]
                    and json_data["recipient_name"] != "null"
                ):
                    info.recipient_name = json_data["recipient_name"]
                    logger.info(f"Found JSON recipient: {json_data['recipient_name']}")

                if (
                    "estimated_delivery_date" in json_data
                    and json_data["estimated_delivery_date"]
                    and json_data["estimated_delivery_date"] != "null"
                ):
                    try:
                        info.estimated_delivery = datetime.strptime(
                            json_data["estimated_delivery_date"], "%Y-%m-%d"
                        ).date()
                        logger.info(
                            f"Found JSON delivery date: {json_data['estimated_delivery_date']}"
                        )
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid JSON date format: {json_data['estimated_delivery_date']}"
                        )

                # If we found JSON data, return early
                if any(
                    [
                        info.shipment_status,
                        info.vendor_name,
                        info.package_description,
                        info.recipient_name,
                        info.estimated_delivery,
                    ]
                ):
                    return info

            # Extract basic information using regex patterns
            if "is_order_update" in response.lower():
                info.is_order_update = (
                    "true" in response.lower() or "yes" in response.lower()
                )

            # Extract status - look for both structured and natural language responses
            status_patterns = {
                "confirmed": r"confirmed|order.*received|thanks.*for.*order",
                "shipped": r"shipped|shipment.*sent|package.*shipped",
                "delivered": r"delivered|delivery.*complete|successfully.*delivered",
                "in_transit": r"in.*transit|on.*the.*way|on.*its.*way",
                "out_for_delivery": r"out.*for.*delivery|delivery.*today",
                "exception": r"exception|delivery.*exception|failed.*delivery",
                "pending": r"pending|processing|order.*pending",
                "packing": r"packing|being.*packed|preparing.*shipment",
            }

            # First try to find status in a structured format (e.g., "status: shipped")
            structured_status_match = re.search(
                r"status\s*[:=]\s*(\w+)", response, re.IGNORECASE
            )
            if structured_status_match:
                status_value = structured_status_match.group(1).lower()
                # Convert string to ShipmentStatus enum
                try:
                    info.shipment_status = ShipmentStatus(status_value)
                    logger.info(f"Found structured status: {status_value}")
                except ValueError:
                    logger.warning(f"Unknown structured status value: {status_value}")

            # If no structured status found, try pattern matching
            if not info.shipment_status:
                for status, pattern in status_patterns.items():
                    try:
                        if re.search(pattern, response, re.IGNORECASE):
                            # Convert string to ShipmentStatus enum

                            try:
                                info.shipment_status = ShipmentStatus(status)
                                logger.info(f"Found pattern-based status: {status}")
                            except ValueError:
                                # If the status doesn't match any enum value, skip it
                                logger.warning(f"Unknown status value: {status}")
                            break
                    except Exception as e:
                        logger.warning(f"Error in status pattern matching: {e}")
                        continue

            # Extract order number
            order_match = re.search(
                r"order.*number.*?[:#]\s*([A-Z0-9\-]+)", response, re.IGNORECASE
            )
            if order_match:
                info.order_number = order_match.group(1)

            # Extract tracking number with carrier-specific patterns
            tracking_patterns = [
                # OnTrac: C + 15 digits
                (r"tracking.*number.*?[:#]\s*(C\d{15})", "ONTRAC"),
                # UPS: 1Z + 16 alphanumeric
                (r"tracking.*number.*?[:#]\s*(1Z[A-Z0-9]{16})", "UPS"),
                # USPS: 20 digits
                (r"tracking.*number.*?[:#]\s*(\d{20})", "USPS"),
                # FedEx: 12 digits
                (r"tracking.*number.*?[:#]\s*(\d{12})", "FEDEX"),
                # Generic fallback (but more restrictive)
                (r"tracking.*number.*?[:#]\s*([A-Z0-9]{8,20})", "UNKNOWN"),
            ]

            for pattern, carrier in tracking_patterns:
                tracking_match = re.search(pattern, response, re.IGNORECASE)
                if tracking_match:
                    tracking_num = tracking_match.group(1)
                    # Additional validation: don't accept strings that look like URL parameters
                    if (
                        not re.search(r"[=&\?]", tracking_num)
                        and len(tracking_num) >= 8
                    ):
                        info.tracking_number = tracking_num
                        logger.info(f"Found {carrier} tracking number: {tracking_num}")
                        break

            # Extract vendor name - look for both structured and natural language responses
            # First try structured format (e.g., "vendor: The Home Depot")
            structured_vendor_match = re.search(
                r"vendor\s*[:=]\s*([^,\n(]+)", response, re.IGNORECASE
            )
            if structured_vendor_match:
                vendor_name = structured_vendor_match.group(1).strip()
                if vendor_name and vendor_name.lower() not in ["null", "none", "n/a"]:
                    info.vendor_name = vendor_name
                    logger.info(f"Found structured vendor name: {vendor_name}")

            # If no structured vendor found, try pattern matching
            if not info.vendor_name:
                vendor_patterns = [
                    r"vendor/retailer name:\s*([^,\n(]+)",
                    r"vendor/retailer:\s*([^,\n(]+)",
                    r"retailer name:\s*([^,\n(]+)",
                    r"from\s+([A-Z][a-zA-Z\s&]+)\s+(?:order|shipment|email)",
                ]
                for pattern in vendor_patterns:
                    try:
                        vendor_match = re.search(pattern, response, re.IGNORECASE)
                        if vendor_match:
                            vendor_name = vendor_match.group(1).strip()
                            if vendor_name and vendor_name.lower() not in [
                                "null",
                                "none",
                                "n/a",
                            ]:
                                info.vendor_name = vendor_name
                                logger.info(
                                    f"Found pattern-based vendor name: {vendor_name}"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"Error in vendor pattern matching: {e}")
                        continue

            # Extract package description
            structured_desc_match = re.search(
                r"package description\s*[:=]\s*([^,\n(]+)", response, re.IGNORECASE
            )
            if structured_desc_match:
                desc = structured_desc_match.group(1).strip()
                if desc and desc.lower() not in ["null", "none", "n/a"]:
                    info.package_description = desc
                    logger.info(f"Found structured package description: {desc}")

            # Extract recipient name
            structured_recipient_match = re.search(
                r"recipient name\s*[:=]\s*([^,\n(]+)", response, re.IGNORECASE
            )
            if structured_recipient_match:
                recipient = structured_recipient_match.group(1).strip()
                if recipient and recipient.lower() not in ["null", "none", "n/a"]:
                    info.recipient_name = recipient
                    logger.info(f"Found structured recipient name: {recipient}")

            # If no structured recipient found, try pattern matching
            if not info.recipient_name:
                recipient_patterns = [
                    r"recipient name:\s*([^,\n(]+)",
                    r"delivered to:\s*([^,\n(]+)",
                    r"shipping to:\s*([^,\n(]+)",
                    r"dear\s+([A-Z][a-z]+)",
                ]
                for pattern in recipient_patterns:
                    try:
                        recipient_match = re.search(pattern, response, re.IGNORECASE)
                        if recipient_match:
                            recipient = recipient_match.group(1).strip()
                            if recipient and recipient.lower() not in [
                                "null",
                                "none",
                                "n/a",
                            ]:
                                info.recipient_name = recipient
                                logger.info(
                                    f"Found pattern-based recipient name: {recipient}"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"Error in recipient pattern matching: {e}")
                        continue

            # Extract date - look for both structured and natural language responses
            # First try structured format (e.g., "estimated delivery: 2024-11-25")
            structured_date_match = re.search(
                r"estimated.*delivery.*?[:=]\s*(\d{4}-\d{2}-\d{2})",
                response,
                re.IGNORECASE,
            )
            if structured_date_match:

                try:
                    info.estimated_delivery = datetime.strptime(
                        structured_date_match.group(1), "%Y-%m-%d"
                    ).date()
                    logger.info(
                        f"Found structured delivery date: {structured_date_match.group(1)}"
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid structured date format: {structured_date_match.group(1)}"
                    )

            # If no structured date found, try general date pattern
            if not info.estimated_delivery:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", response)
                if date_match:

                    try:
                        info.estimated_delivery = datetime.strptime(
                            date_match.group(1), "%Y-%m-%d"
                        ).date()
                        logger.info(f"Found general date: {date_match.group(1)}")
                    except ValueError:
                        logger.warning(f"Invalid date format: {date_match.group(1)}")

            # Extract confidence score
            confidence_match = re.search(
                r"confidence.*?(\d+\.?\d*)", response, re.IGNORECASE
            )
            if confidence_match:
                try:
                    info.confidence_score = float(confidence_match.group(1))
                except ValueError:
                    pass

            return info

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
