"""Intent-detector routing: a real question must never be swallowed by a small-talk branch.

Each case is (message, first detector expected to fire in chat.ask order, or None
when the message should fall through to recommend/retrieve).
"""
import pytest

from src.generate import (
    is_buy_intent, is_chitchat, is_farewell, is_greeting, is_routine_intent,
    is_thanks, is_vague_product_request,
)

ORDER = [
    is_greeting, is_thanks, is_farewell, is_vague_product_request,
    is_chitchat, is_buy_intent, is_routine_intent,
]


def route(text):
    return next((f.__name__ for f in ORDER if f(text)), None)


CASES = [
    # bare small talk still routes to small talk
    ("hi", "is_greeting"),
    ("Hello!", "is_greeting"),
    ("hey there", "is_greeting"),
    ("مرحبا", "is_greeting"),
    ("how are you?", "is_greeting"),
    ("what can you do", "is_greeting"),
    ("thanks!", "is_thanks"),
    ("thank you so much", "is_thanks"),
    ("شكرا", "is_thanks"),
    ("bye", "is_farewell"),
    ("show me products", "is_vague_product_request"),
    ("what do you sell?", "is_vague_product_request"),
    ("browse", "is_vague_product_request"),
    ("what are your products", "is_vague_product_request"),
    ("cool", "is_chitchat"),
    ("buy it", "is_buy_intent"),
    ("build my routine", "is_routine_intent"),
    # real questions that start with a small-talk word must fall through
    ("Hi, I'm Sarah. Can I return the duvet I bought?", None),
    ("hey, can I return my lamp?", None),
    ("what are your return policies", None),
    ("who are you shipping with", None),
    ("find me a lamp for my bedroom", None),
    ("what do you have for dry skin", None),
    ("show me products for oily skin", None),
    ("tell me more about the brass lamp", None),
    ("what else goes with the throw", None),
    ("browse lamps", None),
    ("thanks, but does it come in blue?", None),
    ("steps to return an item", None),
    ("what order number do I need", None),
    ("add it to my routine?", "is_routine_intent"),
    # routine words win over a greeting word at the start
    ("morning routine for oily skin?", "is_routine_intent"),
    ("evening skincare routine please", "is_routine_intent"),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_route(text, expected):
    assert route(text) == expected
