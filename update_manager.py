"""
Update manager for ccusage-bar.

Handles checking for updates via GitHub API and installing updates
by cloning to a temporary directory, building, and installing.
"""

import subprocess
import os
import time
import tempfile
import shutil
import urllib.request
import urllib.error
import json
import ssl

# GitHub repository URL
# Note: Hardcoded for now. Could be made configurable via preferences later.
REPO_URL = "https://github.com/RomainJeff/ccusage-bar.git"
GITHUB_API_URL = "https://api.github.com/repos/RomainJeff/ccusage-bar/commits/main"


class UpdateManager:
    @staticmethod
    def get_current_version():
        """Read version from bundle Info.plist

        Returns: version string like "1.0.0" or None
        """
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.infoDictionary()
                return info.get("CFBundleVersion", None)
        except:
            pass
        return None

    @staticmethod
    def check_for_updates():
        """Check if update available via GitHub API.

        Does NOT require local git repo - uses GitHub API.

        Returns: (has_update: bool, description: str, error: str|None)

        Example: (True, "Add user preferences for week start", None)
        """
        try:
            # Install HTTPS handler explicitly (needed for some Python environments)
            # This ensures urllib can handle HTTPS URLs
            https_handler = urllib.request.HTTPSHandler()
            opener = urllib.request.build_opener(https_handler)
            urllib.request.install_opener(opener)

            # Fetch latest commit from GitHub API
            request = urllib.request.Request(
                GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json"}
            )

            # Create SSL context (needed for some Python environments)
            context = ssl.create_default_context()

            with urllib.request.urlopen(request, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())

            # Extract commit info
            remote_commit = data["sha"][:7]
            remote_message = data["commit"]["message"].split("\n")[0][:50]

            # For now, we always report update available since we don't track
            # which commit the current version was built from
            # TODO: Store build commit hash in Info.plist during build

            return (True, remote_message, None)

        except urllib.error.URLError as e:
            return (False, None, f"Network error: {e.reason}")
        except Exception as e:
            return (False, None, f"{type(e).__name__}: {str(e)}")

    @staticmethod
    def install_update(progress_callback=None):
        """Install update by cloning to temp directory.

        Flow:
        1. Clone repo to /tmp/ccusage-bar-update-XXXX
        2. Build app in temp directory
        3. Copy to /Applications/
        4. Clean up temp directory
        5. Quit app (user relaunches manually)

        Args:
            progress_callback: Optional function(str) for progress updates

        Returns: (success: bool, error: str|None)
        """
        temp_dir = None

        try:
            # Step 1: Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="ccusage-bar-update-")

            # Step 2: Clone repository
            if progress_callback:
                progress_callback("downloading…")

            result = subprocess.run(
                ["git", "clone", "--depth=1", REPO_URL, temp_dir],
                capture_output=True,
                timeout=60,
                text=True
            )

            if result.returncode != 0:
                return (False, f"Clone failed: {result.stderr[:100]}")

            # Step 3: Build app
            if progress_callback:
                progress_callback("building…")

            build_script = os.path.join(temp_dir, "build.sh")

            # Make build.sh executable
            os.chmod(build_script, 0o755)

            result = subprocess.run(
                [build_script],
                capture_output=True,
                timeout=180,
                cwd=temp_dir,
                text=True
            )

            if result.returncode != 0:
                return (False, f"Build failed: {result.stderr[:100]}")

            # Step 4: Quit current app
            if progress_callback:
                progress_callback("installing…")

            subprocess.run(
                ["osascript", "-e", 'quit app "ccusage-bar"'],
                timeout=5
            )
            time.sleep(2)

            # Step 5: Copy to /Applications
            app_path = os.path.join(temp_dir, "dist", "ccusage-bar.app")

            if not os.path.exists(app_path):
                return (False, "Built app not found in dist/")

            # Remove old app if exists
            dest_path = "/Applications/ccusage-bar.app"
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)

            # Copy new app
            shutil.copytree(app_path, dest_path)

            return (True, None)

        except subprocess.TimeoutExpired:
            return (False, "Update timed out")
        except Exception as e:
            return (False, str(e))

        finally:
            # Step 6: Clean up temp directory (always runs)
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass  # Best effort cleanup
