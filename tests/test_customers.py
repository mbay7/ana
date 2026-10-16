from src.customers import identify, load_customers, profile_prompt

CUSTOMERS = [
    {
        "id": "1",
        "name": "Sarah",
        "email": "sarah@example.com",
        "past_orders": ["washed linen duvet set"],
        "preferences": ["neutral tones"],
    },
    {
        "id": "2",
        "name": "Omar",
        "email": "omar@example.com",
        "past_orders": ["brass table lamp"],
        "preferences": ["warm lighting"],
    },
]


def test_identify_is_off_by_default():
    # Identity must come from a signed-in session, not from what a shopper types.
    assert identify("hi, this is omar@example.com", CUSTOMERS) is None


def test_identify_refuses_without_session_even_when_enabled():
    # Typing someone's email must never unlock their order history.
    assert identify("hi, this is omar@example.com", CUSTOMERS, enabled=True) is None


def test_identify_by_signed_in_session_id():
    assert identify("where is my order?", CUSTOMERS, enabled=True, session_customer_id="2")["name"] == "Omar"


def test_identify_session_id_ignored_when_disabled_or_unknown():
    assert identify("hi", CUSTOMERS, enabled=False, session_customer_id="2") is None
    assert identify("hi", CUSTOMERS, enabled=True, session_customer_id="999") is None


def test_identify_session_wins_over_typed_email():
    c = identify("I am sarah@example.com", CUSTOMERS, enabled=True, session_customer_id="2")
    assert c["name"] == "Omar"


def test_identify_never_by_name():
    assert identify("I'm Sarah, can I return something?", CUSTOMERS, enabled=True) is None


def test_identify_unknown():
    assert identify("hello there", CUSTOMERS) is None


def test_profile_prompt_personalizes():
    text = profile_prompt(CUSTOMERS[0])
    assert "Sarah" in text
    assert "duvet" in text
    assert "neutral tones" in text


def test_load_customers_missing_file(tmp_path):
    assert load_customers(str(tmp_path / "nope.json")) == []