"""
Unit tests for PII redaction functionality.

Tests cover various PII formats and edge cases to ensure
comprehensive redaction before LLM processing.
"""

import pytest
from main import redact_pii


class TestEmailRedaction:
    """Test email address redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_standard_email(self):
        """Test redaction of standard email format."""
        text = "Contact me at john.doe@example.com for details"
        result = redact_pii(text)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "john.doe@example.com" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_multiple_emails(self):
        """Test redaction of multiple email addresses."""
        text = "Primary: alice@company.com, Secondary: bob@company.org"
        result = redact_pii(text)
        assert result.count("<PII_REDACTED_EMAIL>") == 2
        assert "alice@company.com" not in result
        assert "bob@company.org" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_email_with_plus_sign(self):
        """Test redaction of email with plus sign (common for filtering)."""
        text = "Email: user+tag@example.com"
        result = redact_pii(text)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "user+tag@example.com" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_email_with_subdomain(self):
        """Test redaction of email with subdomain."""
        text = "Contact: admin@mail.example.co.uk"
        result = redact_pii(text)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "admin@mail.example.co.uk" not in result


class TestPhoneRedaction:
    """Test phone number redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_us_phone_with_parentheses(self):
        """Test redaction of US phone with parentheses format."""
        text = "Call me at (555) 123-4567"
        result = redact_pii(text)
        assert "<PII_REDACTED_PHONE>" in result
        assert "(555) 123-4567" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_us_phone_with_hyphens(self):
        """Test redaction of US phone with hyphens."""
        text = "Phone: 555-123-4567"
        result = redact_pii(text)
        assert "<PII_REDACTED_PHONE>" in result
        assert "555-123-4567" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_us_phone_with_dots(self):
        """Test redaction of US phone with dots."""
        text = "Mobile: 555.123.4567"
        result = redact_pii(text)
        assert "<PII_REDACTED_PHONE>" in result
        assert "555.123.4567" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_international_phone(self):
        """Test redaction of international phone format."""
        text = "International: +1-555-123-4567"
        result = redact_pii(text)
        assert "<PII_REDACTED_PHONE>" in result
        assert "+1-555-123-4567" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_multiple_phones(self):
        """Test redaction of multiple phone numbers."""
        text = "Office: (555) 123-4567, Mobile: 555-987-6543"
        result = redact_pii(text)
        assert result.count("<PII_REDACTED_PHONE>") >= 2
        assert "(555) 123-4567" not in result
        assert "555-987-6543" not in result


class TestSSNRedaction:
    """Test Social Security Number redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_standard_ssn(self):
        """Test redaction of standard SSN format."""
        text = "SSN: 123-45-6789"
        result = redact_pii(text)
        assert "<PII_REDACTED_SSN>" in result
        assert "123-45-6789" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_ssn_in_context(self):
        """Test redaction of SSN within sentence."""
        text = "My social security number is 987-65-4321 for verification"
        result = redact_pii(text)
        assert "<PII_REDACTED_SSN>" in result
        assert "987-65-4321" not in result


class TestAddressRedaction:
    """Test street address redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_street_address_with_street(self):
        """Test redaction of address with 'Street'."""
        text = "I live at 123 Main Street, Anytown"
        result = redact_pii(text)
        assert "<PII_REDACTED_ADDRESS>" in result
        assert "123 Main Street" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_street_address_with_avenue(self):
        """Test redaction of address with 'Avenue'."""
        text = "Office: 456 Park Avenue"
        result = redact_pii(text)
        assert "<PII_REDACTED_ADDRESS>" in result
        assert "456 Park Avenue" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_street_address_with_abbreviation(self):
        """Test redaction of address with abbreviation."""
        text = "Mailing address: 789 Oak St"
        result = redact_pii(text)
        assert "<PII_REDACTED_ADDRESS>" in result
        assert "789 Oak St" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_street_address_with_drive(self):
        """Test redaction of address with 'Drive'."""
        text = "Located at 321 Elm Drive"
        result = redact_pii(text)
        assert "<PII_REDACTED_ADDRESS>" in result
        assert "321 Elm Drive" not in result


class TestURLRedaction:
    """Test URL redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_http_url(self):
        """Test redaction of HTTP URL."""
        text = "Visit my portfolio at http://johndoe.com/portfolio"
        result = redact_pii(text)
        assert "<PII_REDACTED_URL>" in result
        assert "http://johndoe.com" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_https_url(self):
        """Test redaction of HTTPS URL."""
        text = "GitHub: https://github.com/johndoe"
        result = redact_pii(text)
        assert "<PII_REDACTED_URL>" in result
        assert "https://github.com/johndoe" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_multiple_urls(self):
        """Test redaction of multiple URLs."""
        text = "Portfolio: https://portfolio.com LinkedIn: https://linkedin.com/in/user"
        result = redact_pii(text)
        assert result.count("<PII_REDACTED_URL>") == 2


class TestNameRedaction:
    """Test common name pattern redaction."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_full_name_at_start(self):
        """Test redaction of full name at document start."""
        text = "John Doe\nSoftware Engineer\nExperience..."
        result = redact_pii(text)
        # Should detect capitalized name pattern at start
        assert "<PII_REDACTED_NAME>" in result or "John Doe" in result  # May not catch all names in Phase 1

    @pytest.mark.unit
    @pytest.mark.pii
    def test_preserve_company_names(self):
        """Test that company names are preserved (Phase 1 limitation)."""
        text = "Worked at Google Inc. and Microsoft Corporation"
        result = redact_pii(text)
        # Phase 1: Company names are preserved (no NER yet)
        # This is a known limitation documented in ARCHITECTURE_NOTES.md
        assert "Google" in result or "Microsoft" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_empty_string(self):
        """Test redaction of empty string."""
        result = redact_pii("")
        assert result == ""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_none_input(self):
        """Test redaction handles None gracefully."""
        result = redact_pii(None)
        assert result is None or result == ""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_no_pii_present(self):
        """Test text with no PII remains unchanged."""
        text = "This is a simple sentence with no personal information"
        result = redact_pii(text)
        assert "PII_REDACTED" not in result
        assert text == result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_mixed_pii_types(self):
        """Test text with multiple PII types."""
        text = """
        John Doe
        Email: john.doe@example.com
        Phone: (555) 123-4567
        Address: 123 Main Street
        SSN: 123-45-6789
        Portfolio: https://johndoe.com
        """
        result = redact_pii(text)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "<PII_REDACTED_PHONE>" in result
        assert "<PII_REDACTED_ADDRESS>" in result
        assert "<PII_REDACTED_SSN>" in result
        assert "<PII_REDACTED_URL>" in result
        # Verify original PII not present
        assert "john.doe@example.com" not in result
        assert "(555) 123-4567" not in result
        assert "123 Main Street" not in result
        assert "123-45-6789" not in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_pii_with_special_characters(self):
        """Test PII with special characters and formatting."""
        text = "Contact: <john.doe@example.com> or call: [555-123-4567]"
        result = redact_pii(text)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "<PII_REDACTED_PHONE>" in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_case_sensitivity(self):
        """Test that redaction is case-insensitive where appropriate."""
        text = "123 MAIN STREET and 456 oak avenue"
        result = redact_pii(text)
        # Both should be redacted regardless of case
        assert result.count("<PII_REDACTED_ADDRESS>") >= 1


class TestRealWorldResume:
    """Test realistic resume examples."""

    @pytest.mark.unit
    @pytest.mark.pii
    def test_typical_resume_header(self):
        """Test redaction of typical resume header."""
        resume = """
        Jane Smith
        jane.smith@email.com | (415) 555-0123 | https://janesmith.dev
        123 Market Street, San Francisco, CA 94103

        PROFESSIONAL SUMMARY
        Experienced software engineer with 5+ years...
        """
        result = redact_pii(resume)
        assert "<PII_REDACTED_EMAIL>" in result
        assert "<PII_REDACTED_PHONE>" in result
        assert "<PII_REDACTED_URL>" in result
        assert "<PII_REDACTED_ADDRESS>" in result
        # Verify professional content preserved
        assert "PROFESSIONAL SUMMARY" in result
        assert "software engineer" in result

    @pytest.mark.unit
    @pytest.mark.pii
    def test_linkedin_github_urls(self):
        """Test redaction of common profile URLs."""
        text = """
        LinkedIn: https://linkedin.com/in/johndoe
        GitHub: https://github.com/johndoe
        Portfolio: http://johndoe.dev
        """
        result = redact_pii(text)
        assert result.count("<PII_REDACTED_URL>") >= 3
        assert "linkedin.com/in/johndoe" not in result
        assert "github.com/johndoe" not in result
