from keyboards import UserKeyboard
from handlers.news_workflow import news_completion_message
from localization import button, is_button, text


def _labels(markup):
    return [item.text for row in markup.keyboard for item in row]


def test_main_keyboard_uses_selected_language():
    english = _labels(UserKeyboard.main(language="en"))
    persian = _labels(UserKeyboard.main(language="fa"))

    assert "📊 Chart analysis" in english
    assert "📊 تحلیل چارت" in persian
    assert "🌐 Language" in english
    assert "🌐 زبان" in persian


def test_button_matching_accepts_both_languages():
    assert is_button("• Back •", "back")
    assert is_button("• برگشت •", "back")
    assert button("news", "en") == "📰 News analysis (free)"


def test_text_falls_back_to_persian():
    assert text("en", "Hello", "سلام") == "Hello"
    assert text(None, "Hello", "سلام") == "سلام"


def test_news_completion_message_uses_selected_language():
    english = news_completion_message("en", "@Chapar_channel")
    persian = news_completion_message("fa", "@Chapar_channel")

    assert "AI-generated" in english
    assert "Analysis results and user feedback" in english
    assert "این تحلیل هوش مصنوعی است" in persian
