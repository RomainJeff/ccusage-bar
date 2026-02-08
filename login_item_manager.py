"""
login_item_manager.py - Manage macOS login item registration
Uses SMAppService API (macOS 13+) via PyObjC
"""

from Foundation import NSBundle
from ServiceManagement import (
    SMAppService,
    SMAppServiceStatusNotRegistered,
    SMAppServiceStatusEnabled,
    SMAppServiceStatusRequiresApproval,
    SMAppServiceStatusNotFound
)


class LoginItemManager:
    """Manage login item registration for the main app"""

    @staticmethod
    def get_bundle_path():
        """Get the path to the current app bundle

        Returns:
            str or None: Bundle path if available
        """
        bundle = NSBundle.mainBundle()
        if bundle:
            return str(bundle.bundlePath())
        return None

    @staticmethod
    def get_bundle_identifier():
        """Get the app's bundle identifier

        Returns:
            str or None: Bundle identifier if available
        """
        bundle = NSBundle.mainBundle()
        if bundle:
            return str(bundle.bundleIdentifier())
        return None

    @staticmethod
    def is_registered():
        """Check if the app is registered as a login item

        Returns:
            tuple: (is_registered: bool, status_code: int, error: str or None)
        """
        try:
            service = SMAppService.mainAppService()
            status = service.status()

            if status == SMAppServiceStatusEnabled:
                return (True, status, None)
            elif status == SMAppServiceStatusRequiresApproval:
                return (True, status, "User approval required in System Settings")
            elif status == SMAppServiceStatusNotRegistered:
                return (False, status, None)
            else:  # SMAppServiceStatusNotFound
                return (False, status, "Service not found")

        except Exception as e:
            return (False, -1, f"Error checking status: {str(e)}")

    @staticmethod
    def register():
        """Register the app as a login item

        Returns:
            tuple: (success: bool, error: str or None)
        """
        try:
            service = SMAppService.mainAppService()

            # Check if already registered
            if service.status() == SMAppServiceStatusEnabled:
                return (True, None)

            # Register the service
            # In PyObjC, error handling uses the pattern: method_(None) returns (result, error)
            success = service.registerAndReturnError_(None)

            if success[0]:  # First element is the boolean result
                return (True, None)
            else:
                error_obj = success[1]  # Second element is the NSError
                if error_obj:
                    error_msg = str(error_obj.localizedDescription())
                else:
                    error_msg = "Unknown error during registration"
                return (False, error_msg)

        except Exception as e:
            return (False, f"Exception during registration: {str(e)}")

    @staticmethod
    def unregister():
        """Unregister the app from login items

        Returns:
            tuple: (success: bool, error: str or None)
        """
        try:
            service = SMAppService.mainAppService()

            # Check if not registered
            if service.status() == SMAppServiceStatusNotRegistered:
                return (True, None)

            # Unregister the service
            success = service.unregisterAndReturnError_(None)

            if success[0]:
                return (True, None)
            else:
                error_obj = success[1]
                if error_obj:
                    error_msg = str(error_obj.localizedDescription())
                else:
                    error_msg = "Unknown error during unregistration"
                return (False, error_msg)

        except Exception as e:
            return (False, f"Exception during unregistration: {str(e)}")

    @staticmethod
    def toggle():
        """Toggle login item status

        Returns:
            tuple: (new_state: bool, error: str or None)
        """
        is_registered, status, error = LoginItemManager.is_registered()

        if error and status == -1:
            return (False, error)

        if is_registered:
            success, error = LoginItemManager.unregister()
            return (not success, error)  # Return new state: False if unregister succeeded
        else:
            success, error = LoginItemManager.register()
            return (success, error)  # Return new state: True if register succeeded
