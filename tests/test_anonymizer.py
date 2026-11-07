
from app.anonymizer.engine import AnonymizationEngine

engine = AnonymizationEngine()


def test_masks_email():
    result, detected = engine.anonymize("Contact ivan@example.com")
    assert result == "Contact i***@example.com"
    assert detected == {"EMAIL": 1}


def test_masks_phone_preserving_last_two_digits():
    result, detected = engine.anonymize("Call +7 (999) 123-45-67")
    assert result == "Call +* (***) ***-**-67"
    assert detected == {"PHONE": 1}


def test_masks_passport():
    result, detected = engine.anonymize("Passport 1234 567890")
    assert result == "Passport **** ******"
    assert detected == {"PASSPORT": 1}


def test_masks_snils():
    result, detected = engine.anonymize("SNILS 123-456-789-00")
    assert result == "SNILS ***-***-***-00"
    assert detected == {"SNILS": 1}


def test_empty_detection():
    result, detected = engine.anonymize("Nothing sensitive here")
    assert result == "Nothing sensitive here"
    assert detected == {}


def test_masks_person():
    result, detected = engine.anonymize("Иван Петров")
    assert result == "И*** П*****"
    assert detected == {"PERSON": 1}


def test_masks_full_name():
    result, detected = engine.anonymize("Иван Сергеевич Петров")
    assert result == "И*** С******** П*****"
    assert detected == {"PERSON": 1}


def test_masks_english_name():
    result, detected = engine.anonymize("John Smith")
    assert result == "J*** S****"
    assert detected == {"PERSON": 1}


def test_does_not_mask_new_year_greeting():
    result, detected = engine.anonymize(
        "Поздравляю с Новым Годом! Иван Петров"
    )
    assert result == "Поздравляю с Новым Годом! И*** П*****"
    assert detected == {"PERSON": 1}


def test_masks_address_with_city():
    result, detected = engine.anonymize(
        "Адрес: г. Москва, ул. Тверская, д. 10"
    )
    assert result == "Адрес: [АДРЕС]"
    assert detected == {"ADDRESS": 1}


def test_masks_address_with_street_and_house():
    result, detected = engine.anonymize(
        "Проживаю по адресу: улица Ленина, дом 25"
    )
    assert result == "Проживаю по адресу: [АДРЕС]"
    assert detected == {"ADDRESS": 1}


def test_masks_address_with_apartment():
    result, detected = engine.anonymize(
        "Мой адрес: ул. Пушкина, д. 5, кв. 12"
    )
    assert result == "Мой адрес: [АДРЕС]"
    assert detected == {"ADDRESS": 1}


def test_masks_date_with_dots():
    result, detected = engine.anonymize(
        "Дата рождения: 15.05.1990"
    )
    assert result == "Дата рождения: [ДАТА]"
    assert detected == {"DATE": 1}


def test_masks_date_with_slashes():
    result, detected = engine.anonymize(
        "Дата рождения: 15/05/1990"
    )
    assert result == "Дата рождения: [ДАТА]"
    assert detected == {"DATE": 1}


def test_masks_date_iso_format():
    result, detected = engine.anonymize(
        "Дата рождения: 1990-05-15"
    )
    assert result == "Дата рождения: [ДАТА]"
    assert detected == {"DATE": 1}

def test_does_not_mask_common_greeting():
    result, detected = engine.anonymize("Доброе утро!")

    assert result == "Доброе утро!"
    assert detected == {}

def test_does_not_mask_birthday_greeting():
    result, detected = engine.anonymize("Поздравляю с Днём Рождения!")

    assert result == "Поздравляю с Днём Рождения!"
    assert detected == {}

def test_does_not_mask_invalid_date():
    result, detected = engine.anonymize(
        "Дата рождения: 31.02.1990"
    )

    assert result == "Дата рождения: 31.02.1990"
    assert detected == {}

def test_masks_valid_leap_year_date():
    result, detected = engine.anonymize(
        "Дата рождения: 29.02.2024"
    )

    assert result == "Дата рождения: [ДАТА]"
    assert detected == {"DATE": 1}

def test_email_is_not_double_masked():
    result, detected = engine.anonymize(
        "Моя почта: ivan.petrov@example.com"
    )

    assert result == "Моя почта: i**********@example.com"
    assert detected == {"EMAIL": 1}

def test_masks_multiple_sensitive_data_types():
    result, detected = engine.anonymize(
        "Паспорт: 4510 123456, СНИЛС: 123-456-789-01, email: ivan@example.com"
    )

    assert "4510 123456" not in result
    assert "123-456-789-01" not in result
    assert "ivan@example.com" not in result

    assert detected == {
        "PASSPORT": 1,
        "SNILS": 1,
        "EMAIL": 1,
    }

def test_custom_empty_rules():
    custom_engine = AnonymizationEngine(rules=[])

    text = "Иван Петров, ivan@example.com, +7 999 123-45-67"

    result, detected = custom_engine.anonymize(text)

    assert result == text
    assert detected == {}

def test_custom_email_only_rule():
    from app.anonymizer.rules import DEFAULT_RULES

    email_rule = next(
        rule for rule in DEFAULT_RULES
        if rule.name == "EMAIL"
    )

    custom_engine = AnonymizationEngine(
        rules=[email_rule]
    )

    text = (
        "Иван Петров, email ivan@example.com, "
        "телефон +7 999 123-45-67"
    )

    result, detected = custom_engine.anonymize(text)

    assert "Иван Петров" in result
    assert "ivan@example.com" not in result
    assert "+7 999 123-45-67" in result
    assert detected == {"EMAIL": 1}

def test_higher_priority_rule_wins():
    import re
    from app.anonymizer.rules import Rule

    rule_low = Rule(
        name="LOW",
        pattern=re.compile(r"Иван Петров"),
        masker=lambda value: "[LOW]",
        priority=10,
    )

    rule_high = Rule(
        name="HIGH",
        pattern=re.compile(r"Иван"),
        masker=lambda value: "[HIGH]",
        priority=100,
    )

    custom_engine = AnonymizationEngine(
        rules=[rule_low, rule_high]
    )

    result, detected = custom_engine.anonymize("Иван Петров")

    assert result == "[HIGH] Петров"
    assert detected == {"HIGH": 1}

def test_anonymizes_large_text():
    text = (
        "Контакты: ivan@example.com, "
        "телефон +7 999 123-45-67. "
    ) * 100

    result, detected = engine.anonymize(text)

    assert "ivan@example.com" not in result
    assert "+7 999 123-45-67" not in result
    assert detected["EMAIL"] == 100
    assert detected["PHONE"] == 100