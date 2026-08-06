from telegram import ReplyKeyboardMarkup
from localization import button

class UserKeyboard:
    """User keyboard layouts."""

    @staticmethod
    def language_selection():
        return ReplyKeyboardMarkup(
            [["English 🇬🇧", "فارسی 🇮🇷"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    @staticmethod
    def main(is_admin=False, language="fa"):
        """Main menu keyboard.

        Args:
            is_admin (bool): Whether user is admin

        Returns:
            ReplyKeyboardMarkup: Main keyboard
        """
        keyboard = [
            [{'text': button('news', language)}, {'text': button('chart', language)}],
            [{'text': button('chat', language)}, {'text': button('market', language)}],
            [{'text': button('subscription', language)}, {'text': button('profile', language)}],
            [{'text': button('language', language)}],
        ]

        if is_admin:
            keyboard.append([{'text': button('admin', language)}])

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def analyze(language="fa"):
        """Analysis menu keyboard.

        Returns:
            ReplyKeyboardMarkup: Analysis keyboard
        """
        keyboard = [
            # [{'text': '• تحلیل دلار •'}, {'text': '• تحلیل طلا •'}],
            [{'text': button('usd_price', language)}, {'text': button('gold_price', language)}],
            [{'text': button('back', language)}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def back(language="fa"):
        """Back button keyboard.

        Returns:
            ReplyKeyboardMarkup: Back keyboard
        """
        keyboard = [
            [{'text': button('back', language)}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def ai_chat(language="fa"):
        """AI chat keyboard with clear history option.

        Returns:
            ReplyKeyboardMarkup: AI chat keyboard
        """
        keyboard = [
            [{'text': button('clear_chat', language)}],
            [{'text': button('back', language)}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def analysis_type(language="fa"):
        """Analysis type selection keyboard.

        Returns:
            ReplyKeyboardMarkup: Analysis type keyboard
        """
        keyboard = [
            [{'text': button('back', language)}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def education_prize(language="fa"):
        """Education and prize menu keyboard.

        Returns:
            ReplyKeyboardMarkup: Education and prize keyboard
        """
        keyboard = [
            [{'text': button('education', language)}, {'text': button('prize', language)}],
            [{'text': button('back', language)}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )
