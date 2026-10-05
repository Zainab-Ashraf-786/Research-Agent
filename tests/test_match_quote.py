import pytest
from agent.match_quote import is_quote_valid

def test_exact_quote_passes():
    source = "Mistral Large is offered at $2.00 per million input tokens."
    quote = "Mistral Large is offered at $2.00 per million input tokens."
    assert is_quote_valid(quote, source) is True

def test_typographical_variations_pass():
    # Smart quotes, comma inside numbers, dashes, and whitespace differences
    source = 'The company reported “record net income” of $1,000,000—a 15% increase year-over-year.'
    quote = 'The company reported "record net income" of $1000000 - a 15% increase year-over-year.'
    assert is_quote_valid(quote, source) is True

def test_number_mismatch_fails():
    # $25/month vs $20/month
    source = "The pro subscription tier is priced at $20/month."
    quote = "The pro subscription tier is priced at $25/month."
    assert is_quote_valid(quote, source) is False

def test_number_mismatch_orders_of_magnitude():
    # $250 vs $25
    source = "The enterprise seat costs $250 per seat."
    quote = "The enterprise seat costs $25 per seat."
    assert is_quote_valid(quote, source) is False

def test_number_appearing_elsewhere_on_page_fails():
    # "25" is present in footer/header, but the local sentence says "$20"
    source = "Copyright 2025 Acme Inc. All rights reserved. The pro plan is $20 per month. Contact support at 25 High Street."
    quote = "The pro plan is $25 per month."
    assert is_quote_valid(quote, source) is False

def test_dropped_negation_fails():
    # Dropping "not" inverts truth
    source = "The investigational drug was not approved by the committee."
    quote = "The investigational drug was approved by the committee."
    assert is_quote_valid(quote, source) is False

def test_added_negation_fails():
    # Adding "not" inverts truth
    source = "The investigational drug was approved by the committee."
    quote = "The investigational drug was not approved by the committee."
    assert is_quote_valid(quote, source) is False

def test_negation_contractions():
    # didn't vs did not
    source = "The system didn't suffer any downtime during Q3."
    quote = "The system didn't suffer any downtime during Q3."
    assert is_quote_valid(quote, source) is True

    # dropped didn't
    quote_corrupted = "The system suffered any downtime during Q3."
    assert is_quote_valid(quote_corrupted, source) is False

def test_fabricated_quote_fails():
    source = "Stripe announced a new payments gateway for European fintechs."
    quote = "Stripe announced a multi-billion dollar acquisition of PayPal."
    assert is_quote_valid(quote, source) is False

def test_empty_or_oversized_quote_safe():
    source = "Short text."
    quote = "This quote is vastly longer than the source text and cannot possibly be contained within it."
    assert is_quote_valid(quote, source) is False
    assert is_quote_valid("", source) is False
    assert is_quote_valid(quote, "") is False
