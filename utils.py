import os
import glob

TEMP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")

def ensure_temp_folder():
    """Ensures the temp folder exists."""
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)

def clean_temp_folder():
    """Removes all files in the temp folder."""
    if os.path.exists(TEMP_FOLDER):
        files = glob.glob(os.path.join(TEMP_FOLDER, "*"))
        for f in files:
            try:
                os.remove(f)
            except OSError as e:
                print(f"Error: {f} : {e.strerror}")

def get_video_files():
    """Returns a list of video files in the temp folder."""
    if not os.path.exists(TEMP_FOLDER):
        return []
    # Simple check for common video extensions
    extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(TEMP_FOLDER, ext)))
    return files
