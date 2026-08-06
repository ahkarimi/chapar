from app.schemas.user import UserRegister, UserUpdate


def test_telegram_registration_accepts_partial_profile():
    user = UserRegister(name="Example", telegram_username="example")
    assert user.email is None
    assert user.phone_number is None
    assert user.is_referred is False


def test_partial_profile_update_accepts_only_changed_fields():
    update = UserUpdate(name="Updated")
    assert update.name == "Updated"
    assert update.email is None
