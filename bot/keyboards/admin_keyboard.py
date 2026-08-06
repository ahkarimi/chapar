from telegram import ReplyKeyboardMarkup

from constants import PLAN_PACKAGES_DAYS

class AdminKeyboard:
    """Admin keyboard layouts."""

    @staticmethod
    def main():
        """Main admin menu keyboard.

        Returns:
            ReplyKeyboardMarkup: Admin main keyboard
        """
        keyboard = [
            [{'text': '• افزودن زمان به کاربر •'}, {'text': '• دریافت اطلاعات کاربر •'}],
            [{'text': '• ارسال پیام همگانی •'}, {'text': '• گزارشات آماری •'}],
            [{'text': '• برگشت •'}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def back():
        """Back button keyboard.

        Returns:
            ReplyKeyboardMarkup: Back keyboard
        """
        keyboard = [
            [{'text': '• برگشت •'}]
        ]

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )

    @staticmethod
    def plan_packages():
        """Plan package selection keyboard.

        Returns:
            ReplyKeyboardMarkup: Plan packages keyboard
        """
        package_buttons = [
            {'text': f'+{days} روز'} for days in PLAN_PACKAGES_DAYS
        ]
        keyboard = [
            package_buttons[index:index + 3]
            for index in range(0, len(package_buttons), 3)
        ]
        keyboard.append([{'text': '• برگشت •'}])

        return ReplyKeyboardMarkup(
            keyboard=[[btn['text'] for btn in row] for row in keyboard],
            resize_keyboard=True
        )
