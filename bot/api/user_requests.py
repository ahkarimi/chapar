"""User-account API operations used by the Telegram bot."""


class UserRequestsMixin:
    """Requests for registration, profiles, and verification."""

    async def add_user(self, user_id, name=None, telegram_username=None):
        """Register a new user in the API.

        Args:
            user_id (int): Telegram user ID
            name (str, optional): User's display name
            telegram_username (str, optional): Telegram @username (without @)

        Returns:
            dict: User information or error details
        """
        data = {}
        if name is not None:
            data['name'] = name
        if telegram_username is not None:
            data['telegram_username'] = telegram_username

        result, status_code = await self._request(
            method='POST',
            path='/api/v1/users/register',
            data=data,
            headers={'TelegramUID': str(user_id)}
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        # Return the result directly as it's already been parsed by _request
        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def register(self, user_id, email, phone_number, name, telegram_username, is_referred):
        """Register a new user with details.

        Args:
            user_id (int): Telegram user ID
            email (str): User email
            phone_number (str): User phone number
            name (str): User name
            telegram_username (str): Telegram username
            is_referred (bool): Whether user was referred

        Returns:
            dict: Registration result or error details
        """
        result, status_code = await self._request(
            method='POST',
            path='/api/v1/users/register',
            data={
                'email': email,
                'phone_number': phone_number,
                'name': name,
                'telegram_username': telegram_username,
                'is_referred': is_referred
            },
            headers={'TelegramUID': str(user_id)}
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        if status_code != 200 and status_code != 201:
            return {"error": True, "status": status_code, "message": f"API error: {status_code}"}

        # Return the result directly as it's already been parsed by _request
        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def update(self, user_id, email, phone_number, name, telegram_username, is_referred):
        """Update user information.

        Args:
            user_id (int): Telegram user ID
            email (str): User email
            phone_number (str): User phone number
            name (str): User name
            telegram_username (str): Telegram username
            is_referred (bool): Whether user was referred

        Returns:
            dict: Update result or error details
        """
        result, status_code = await self._request(
            method='PUT',
            path='/api/v1/users/update',
            headers={'TelegramUID': str(user_id)},
            query={
                'email': email,
                'phone_number': phone_number,
                'name': name,
                'telegram_username': telegram_username,
                'is_referred': is_referred
            }
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        if status_code != 200:
            return {"error": True, "status": status_code, "message": f"API error: {status_code}"}

        # Return the result directly as it's already been parsed by _request
        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def me(self, user_id):
        """Get current user information.

        Args:
            user_id (int): Telegram user ID

        Returns:
            dict: User information or None if not found
        """
        result, status_code = await self._request(
            method='GET',
            path='/api/v1/users/me',
            headers={'TelegramUID': str(user_id)}
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        # Result is already a dictionary since _request parses JSON
        if isinstance(result, dict):
            # Look for different error patterns in the response
            if 'detail' in result:
                if 'User not found' in result['detail']:
                    return None
                # Handle other error messages in the detail field
                return {"error": True, "status": status_code, "message": f"API Error: {result['detail']}"}

            # Check for error field that might be present in some responses
            if 'error' in result and result['error'] is True:
                return {"error": True, "status": status_code, "message": result.get('message', 'Unknown API error')}

            return result
        else:
            # Handle unexpected response type
            return {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def get_user_by_username(self, username):
        """Get user information by telegram username (case-insensitive).

        Args:
            username (str): Telegram username (without @)

        Returns:
            dict: User information or error details
        """
        result, status_code = await self._request(
            method='GET',
            path='/api/v1/admin/users/search',
            query={'username': username}
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        if isinstance(result, dict):
            if 'detail' in result:
                return {"error": True, "status": status_code, "message": result['detail']}
            if 'error' in result and result['error'] is True:
                return {"error": True, "status": status_code, "message": result.get('message', 'Unknown API error')}
            return result
        else:
            return {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def get_user_plan_history(self, user_id):
        """Get complete plan history for a user.

        Args:
            user_id (int): User ID

        Returns:
            dict: Plan history information or error details
        """
        result, status_code = await self._request(
            method='GET',
            path=f'/api/v1/admin/plan/history/{user_id}',
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        if isinstance(result, dict):
            if 'detail' in result:
                return {"error": True, "status": status_code, "message": result['detail']}
            if 'error' in result and result['error'] is True:
                return {"error": True, "status": status_code, "message": result.get('message', 'Unknown API error')}
            return result
        else:
            return {"error": True, "status": status_code, "message": "Invalid response from API"}

    async def verify(self, user_id, uid):
        """Verify a user with simplified verification (only checks invitation codes, no balance required).

        Args:
            user_id (int): Telegram user ID
            uid (str): User UID
        Returns:
            dict: Verification result or error details
        """
        query_params = {'uid_code': uid}

        result, status_code = await self._request(
            method='POST',
            path='/api/v1/referrals/verify',
            headers={'TelegramUID': str(user_id)},
            query=query_params
        )

        if result is None:
            return {"error": True, "status": status_code, "message": "Could not connect to API"}

        # Handle error status codes
        if status_code != 200:
            error_message = "Verification failed"
            if status_code == 404:
                error_message = "Invalid UID or invitation code"
            elif status_code == 401 or status_code == 403:
                error_message = "Authentication failed"
            elif status_code == 400:
                # Try to extract the specific error message from the parsed result
                if isinstance(result, dict) and "detail" in result:
                    error_message = result.get("detail", "Invalid request parameters.")
                else:
                    error_message = "Invalid request parameters"

            return {"error": True, "status": status_code, "message": error_message}

        # Result is already a dictionary since _request parses JSON
        if isinstance(result, dict):
            # Check for error indicators in the response content
            if result.get("status") in ["error", "failed"] or result.get("error"):
                return {"error": True, "status": status_code, "message": result.get("message", "Verification failed")}
            return result
        else:
            # Handle case where response is not a proper dictionary
            return {"error": True, "status": status_code, "message": "Invalid response from API"}
