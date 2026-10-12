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


def test_identify_by_email_when_enabled():
    assert identify("hi, this is omar@example.com", CUSTOMERS, enabled=True)["name"] == "Omar"


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