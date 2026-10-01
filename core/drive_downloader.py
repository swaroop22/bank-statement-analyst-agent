"""
Google Drive integration and file downloader module.
Safely handles Google Drive folder links, direct file links, and local statement files.
Detects restricted permissions and provides clear guidance to user.
"""

import os
import re
import urllib.parse
from typing import List, Tuple, Optional
import gdown


class GoogleDriveDownloader:
    """Downloader and accessor for Google Drive folders and files."""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    @staticmethod
    def extract_folder_id(url: str) -> Optional[str]:
        """Extract Google Drive folder ID from various URL formats."""
        patterns = [
            r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)",
            r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_file_id(url: str) -> Optional[str]:
        """Extract Google Drive file ID from URL."""
        patterns = [
            r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
            r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def fetch_from_url(self, url: str) -> Tuple[List[str], Optional[str]]:
        """
        Attempts to fetch statements from a Google Drive URL.
        Returns:
            Tuple[List[str], Optional[str]]: (List of downloaded file paths, Error/Permission message if any)
        """
        url = url.strip()
        folder_id = self.extract_folder_id(url)
        file_id = self.extract_file_id(url)

        if not folder_id and not file_id:
            return [], f"Invalid Google Drive URL provided: '{url}'. Expected format: https://drive.google.com/drive/folders/<FOLDER_ID>"

        # Try downloading folder
        if folder_id:
            target_folder = os.path.join(self.download_dir, f"drive_folder_{folder_id}")
            os.makedirs(target_folder, exist_ok=True)
            try:
                downloaded_files = gdown.download_folder(
                    id=folder_id,
                    output=target_folder,
                    quiet=False,
                    use_cookies=False,
                    remaining_ok=True
                )
                if downloaded_files:
                    valid_files = [
                        f for f in downloaded_files
                        if os.path.isfile(f) and f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls', '.txt', '.png', '.jpg', '.jpeg'))
                    ]
                    if valid_files:
                        return valid_files, None
                    return [], f"Folder was accessed but contained no supported statement files (PDF, CSV, XLS/XLSX, Images)."
                
                # Check if directory already has files downloaded
                existing = [
                    os.path.join(target_folder, f) for f in os.listdir(target_folder)
                    if os.path.isfile(os.path.join(target_folder, f)) and f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls'))
                ]
                if existing:
                    return existing, None

            except Exception as e:
                err_msg = str(e)
                if "Cannot retrieve the folder information" in err_msg or "permission" in err_msg.lower() or "401" in err_msg or "403" in err_msg:
                    return [], (
                        f"🔒 Access Restricted: The Google Drive folder ({folder_id}) requires view permissions.\n"
                        f"Please update the folder permissions in Google Drive:\n"
                        f"1. Open folder in Google Drive.\n"
                        f"2. Click 'Share' -> 'General access'.\n"
                        f"3. Change from 'Restricted' to 'Anyone with the link' (Role: Viewer).\n"
                        f"4. Alternatively, you can drop statement files directly into the web dashboard or project folder."
                    )
                return [], f"Failed to download from Google Drive folder: {err_msg}"

        # Try downloading single file
        if file_id:
            try:
                dest = os.path.join(self.download_dir, f"statement_{file_id}")
                out_path = gdown.download(id=file_id, output=dest, quiet=False)
                if out_path and os.path.exists(out_path):
                    return [out_path], None
            except Exception as e:
                return [], f"Failed to download Google Drive file {file_id}: {str(e)}"

        return [], "Google Drive folder is empty or not publicly shared."
