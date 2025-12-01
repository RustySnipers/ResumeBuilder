"""
PII Detection using spaCy NER and regex patterns.

This module provides enhanced PII detection capabilities including:
- Named Entity Recognition for person/organization detection
- Context-aware name disambiguation
- International PII format support (IBAN, passport)
- Fallback regex patterns for structured PII (email, phone, SSN, addresses)
"""

import spacy
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class PIIDetector:
    """Enhanced PII detector using spaCy NER and regex patterns."""

    def __init__(self):
        """Initialize the PII detector with spaCy model and regex patterns."""
        try:
            self.nlp = spacy.load('en_core_web_lg')
        except OSError:
            logger.warning("spaCy model 'en_core_web_lg' not found. Falling back to regex-only detection.")
            self.nlp = None

        # Regex patterns from Phase 1 (fallback)
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
        ]
        self.ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        self.url_pattern = r'https?://[^\s<>"\')]+|www\.[^\s<>"\')]+'
        self.address_pattern = r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b'

        # International patterns
        self.iban_pattern = r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b'
        self.passport_pattern = r'\b[A-Z]{1,2}\d{6,9}\b'

    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Detect and redact all PII from text using NER + regex.

        Args:
            text: Input text to analyze

        Returns:
            Tuple of (redacted_text, pii_counts)
        """
        if not text:
            return text, {}

        redacted = text
        pii_counts = {
            'person_names': 0,
            'organizations': 0,
            'emails': 0,
            'phones': 0,
            'ssns': 0,
            'urls': 0,
            'addresses': 0,
            'international': 0
        }

        # 1. NER-based detection for names and organizations (if model available)
        if self.nlp:
            try:
                doc = self.nlp(text)

                # Extract person names (filter out company names using heuristics)
                person_entities = [ent for ent in doc.ents if ent.label_ == 'PERSON']
                org_entities = [ent for ent in doc.ents if ent.label_ == 'ORG']

                # Disambiguate: If "John Doe" appears near "Company" or "Inc", it's likely a company
                persons_to_redact = self._filter_persons_from_orgs(person_entities, org_entities)

                for person in persons_to_redact:
                    redacted = redacted.replace(person.text, '<PII_REDACTED_NAME>')
                    pii_counts['person_names'] += 1

                # Optionally redact organizations (decision: keep for context per ARCHITECTURE_NOTES.md)
                # for org in org_entities:
                #     redacted = redacted.replace(org.text, '<PII_REDACTED_ORG>')
                #     pii_counts['organizations'] += 1
            except Exception as e:
                logger.error(f"NER detection failed: {e}. Continuing with regex-only detection.")

        # 2. Regex-based detection (more reliable for structured PII)
        # Emails
        emails = re.findall(self.email_pattern, redacted)
        for email in emails:
            redacted = redacted.replace(email, '<PII_REDACTED_EMAIL>')
            pii_counts['emails'] += 1

        # Phones
        for pattern in self.phone_patterns:
            phones = re.findall(pattern, redacted)
            for phone in phones:
                redacted = redacted.replace(phone, '<PII_REDACTED_PHONE>')
                pii_counts['phones'] += 1

        # SSN
        ssns = re.findall(self.ssn_pattern, redacted)
        for ssn in ssns:
            redacted = redacted.replace(ssn, '<PII_REDACTED_SSN>')
            pii_counts['ssns'] += 1

        # URLs
        urls = re.findall(self.url_pattern, redacted, re.IGNORECASE)
        for url in urls:
            redacted = redacted.replace(url, '<PII_REDACTED_URL>')
            pii_counts['urls'] += 1

        # Addresses
        addresses = re.findall(self.address_pattern, redacted, re.IGNORECASE)
        for addr in addresses:
            redacted = redacted.replace(addr, '<PII_REDACTED_ADDRESS>')
            pii_counts['addresses'] += 1

        # International PII
        ibans = re.findall(self.iban_pattern, redacted)
        for iban in ibans:
            redacted = redacted.replace(iban, '<PII_REDACTED_IBAN>')
            pii_counts['international'] += 1

        passports = re.findall(self.passport_pattern, redacted)
        for passport in passports:
            redacted = redacted.replace(passport, '<PII_REDACTED_PASSPORT>')
            pii_counts['international'] += 1

        return redacted, pii_counts

    def _filter_persons_from_orgs(self, persons: List, orgs: List) -> List:
        """
        Filter out person entities that are likely organization names.

        Heuristics:
        - If person name contains "Inc", "LLC", "Corp", "Company" -> likely org
        - If person name is adjacent to org entity -> likely org

        Args:
            persons: List of person entities from NER
            orgs: List of organization entities from NER

        Returns:
            Filtered list of person entities
        """
        filtered = []
        org_indicators = ['inc', 'llc', 'corp', 'company', 'limited', 'co', 'corporation']

        for person in persons:
            person_text_lower = person.text.lower()

            # Check if contains org indicators
            if any(indicator in person_text_lower for indicator in org_indicators):
                continue

            # Check if adjacent to organization entity (within 10 characters)
            is_adjacent_to_org = False
            for org in orgs:
                if abs(person.start_char - org.end_char) < 10 or abs(org.start_char - person.end_char) < 10:
                    is_adjacent_to_org = True
                    break

            if not is_adjacent_to_org:
                filtered.append(person)

        return filtered
