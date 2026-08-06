# Services/toobitservice.py
from app.config import settings
import time
import hmac
import hashlib
import httpx
import logging

logger = logging.getLogger(__name__)

class ToobitService:
    def __init__(self):
        self.api_key = settings.TOOBIT_API_KEY
        self.secret_key = settings.TOOBIT_SECRET_KEY
        self.base_url = "https://api.toobit.com"
        self.allowed_invitation_codes = {
            code.strip().lower()
            for code in settings.TOOBIT_ALLOWED_INVITATION_CODES.split(",")
            if code.strip()
        }

    def build_query_string(self, params: dict, order: list) -> str:
        """
        Build a query string from parameters in the specified order,
        including only keys with non-None values.
        """
        parts = []
        for key in order:
            if key in params and params[key] is not None:
                parts.append(f"{key}={params[key]}")
        return "&".join(parts)

    def generate_signature(self, params: dict, order: list) -> str:
        """
        Generate an HMAC SHA256 signature using parameters in the specified order.
        """
        query_string = self.build_query_string(params, order)
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def _send_get_request(self, endpoint: str, params: dict, sign_order: list) -> dict:
        """
        Generic helper function to prepare and send a GET request.
        It adds a timestamp, generates the signature, builds the final URL,
        and handles error checking.
        """
        url = f"{self.base_url}{endpoint}"
        # Set current timestamp
        params["timestamp"] = int(time.time() * 1000)
        # Generate signature (ensure 'timestamp' is part of sign_order)
        signature = self.generate_signature(params, sign_order)
        params["signature"] = signature
        final_order = sign_order + ["signature"]
        query_string = self.build_query_string(params, final_order)
        full_url = f"{url}?{query_string}"
        headers = {"X-BB-APIKEY": self.api_key}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(full_url, headers=headers)
                response.raise_for_status()
                try:
                    result = response.json()
                except Exception:
                    raise Exception("Failed to parse JSON response: " + response.text)
                if not isinstance(result, dict):
                    raise Exception("Unexpected response format: " + str(result))
                if result.get("code") != 200:
                    raise Exception(f"API Error {result.get('code')}: {result.get('msg')}")
                return result
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"An error occurred: {str(e)}")

    async def get_invitation_relation(self, uid: int = None, startTime: int = None, endTime: int = None,
                                      pageIndex: int = 1, pageSize: int = 100, recvWindow: int = 5000) -> dict:
        """
        Query Invited Users (Endpoint: /api/v1/agent/inviteUserList)
        Retrieves information about invited users with optional filters and pagination.
        """
        endpoint = "/api/v1/agent/inviteUserList"
        params = {
            "uid": uid,
            "startTime": startTime,
            "endTime": endTime,
            "pageIndex": pageIndex,
            "pageSize": pageSize,
            "recvWindow": recvWindow
        }
        if uid is not None:
            sign_order = ["uid", "startTime", "endTime", "pageIndex", "pageSize", "recvWindow", "timestamp"]
        else:
            sign_order = ["startTime", "endTime", "pageIndex", "pageSize", "recvWindow", "timestamp"]
        return await self._send_get_request(endpoint, params, sign_order)

    async def check_invitation_relation(self, uid: int, invitation_code: str) -> bool:
        """
        Check if the specified uid has an invitation with the given invitationCode.
        Returns True if found, otherwise False.
        """
        try:
            result = await self.get_invitation_relation()
            data = result.get("data", {})
            user_list = data.get("list", [])

            # Normalize invitation code for comparison (case-insensitive)
            invitation_code_lower = invitation_code.lower().strip()

            for user in user_list:
                user_invitation_code = str(user.get("invitationCode", "")).lower().strip()
                # Compare UID (as string for consistency) and invitationCode
                if str(user.get("uid")) == str(uid) and user_invitation_code == invitation_code_lower:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking invitation relation for UID {uid}: {e}")
            return False

    async def verify_user_with_invite_code(self, uid: int) -> dict:
        """
        Simplified verification that only checks if user registered with any of our allowed invitation codes.
        No balance checking required.

        Args:
            uid: Toobit user ID

        Returns:
            dict: {"verified": bool, "invitation_code": str or None, "error": str or None}
        """
        try:
            # First, try to get the specific user by UID
            result = await self.get_invitation_relation(uid=uid)
            data = result.get("data", {})
            user_list = data.get("list", [])

            # Look for the user in the invited users list
            for user in user_list:
                if str(user.get("uid")) == str(uid):
                    user_invitation_code = str(user.get("invitationCode", "")).lower().strip()

                    # Check if the invitation code is one of our allowed codes
                    if user_invitation_code in self.allowed_invitation_codes:
                        return {
                            "verified": True,
                            "invitation_code": user.get("invitationCode"),
                            "error": None
                        }
                    else:
                        return {
                            "verified": False,
                            "invitation_code": user.get("invitationCode"),
                            "error": f"User registered with invitation code '{user.get('invitationCode')}' which is not allowed"
                        }

            # User not found in invited users list
            return {
                "verified": False,
                "invitation_code": None,
                "error": "UID not found in invited users list"
            }

        except Exception as e:
            logger.error(f"Error verifying user with UID {uid}: {e}")
            return {
                "verified": False,
                "invitation_code": None,
                "error": f"API error: {str(e)}"
            }

    async def get_balance_volume(self, uid: int, invitation_code: str) -> str:
        """
        Retrieve the 'balanceVolume' for the specified uid and check if the invitation code matches.
        Returns the balanceVolume as a string if the invitation code matches, otherwise returns -1.
        """
        result = await self.get_invitation_relation(uid)
        data = result.get("data", {})
        user_list = data.get("list", [])
        for user in user_list:
            if str(user.get("uid")) == str(uid):
                if user.get("invitationCode") == invitation_code:
                    return float(user.get("balanceVolume", "-1"))
                else:
                    return -1  # Invitation code does not match
        return -1

    async def check_balance_volume(self, uid: int, invitation_code: str, threshold: float) -> bool:
        """
        DEPRECATED: Use verify_user_with_invite_code instead.
        Check if the balance volume for the specified uid is greater than the given threshold
        and if the invitation code matches.
        Returns True if the balance volume is greater than the threshold, otherwise False.
        """
        try:
            balance_volume = await self.get_balance_volume(uid, invitation_code)
            return balance_volume >= threshold
        except Exception as e:
            logger.error(f"Error checking balance volume for UID {uid}: {e}")
            return False
