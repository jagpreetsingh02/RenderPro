import subprocess
import os
import glob
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import shutil
import sys
import importlib
import hashlib

# Standalone function for the worker must be at module level for pickle (ProcessPoolExecutor)
def apply_filter_worker(chunk_path):
    """
    Applies a grayscale filter to the video chunk using ffmpeg.
    Uses hash-based caching to avoid re-processing.
    """
    if not os.path.exists(chunk_path):
        return None

    # 1. Calculate MD5 Hash of the chunk
    hasher = hashlib.md5()
    with open(chunk_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    file_hash = hasher.hexdigest()

    # 2. Define Cache Path
    # Using a 'cache' directory in the current working directory (workspace)
    cache_dir = os.path.join(os.getcwd(), "cache")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        pass

    output_filename = f"processed_{file_hash}.mp4"
    output_path = os.path.join(cache_dir, output_filename)

    # 3. Check Cache
    if os.path.exists(output_path):
        print(f"[CACHE HIT] Skipping processing for {os.path.basename(chunk_path)}")
        return output_path

    # Cache Miss - Proceed to Process
    # Lazy import 
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        if shutil.which("ffmpeg"):
            ffmpeg_exe = "ffmpeg"
        else:
            return None

    # ffmpeg -y -i input -vf hue=s=0 output
    cmd = [
        ffmpeg_exe, "-y",
        "-i", chunk_path,
        "-vf", "hue=s=0", # Grayscale
        output_path
    ]
    
    try:
        # Capture output to avoid console spam, check=True raises on error
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error processing {chunk_path}: {e}")
        return None


class VideoEngine:
    def __init__(self):
        pass

    def _get_ffmpeg_exe(self):
        """
        Helper to get ffmpeg executable path safely.
        """
        # 1. Try imageio-ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

        # 2. Try system ffmpeg
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        
        # 3. Fail gracefully
        raise RuntimeError(
            "FFmpeg not found! Please install 'imageio-ffmpeg' via pip:\n"
            "   pip install imageio-ffmpeg\n"
            "Or ensure 'ffmpeg' is in your system PATH."
        )

    def split_video(self, input_path, chunk_length=10):
        """
        Splits the video into chunks using ffmpeg segment muxer.
        Returns a sorted list of chunk filenames.
        """
        ffmpeg_exe = self._get_ffmpeg_exe()
        
        directory = os.path.dirname(input_path)
        filename_no_ext = os.path.splitext(os.path.basename(input_path))[0]
        # Pattern for segment output: inputname_chunk_001.mp4
        output_pattern = os.path.join(directory, f"{filename_no_ext}_chunk_%03d.mp4")
        
        # ffmpeg -y -i input -c copy -f segment -segment_time chunk_length -reset_timestamps 1 output_pattern
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_path,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(chunk_length),
            "-reset_timestamps", "1",
            output_pattern
        ]
        
        print(f"DEBUG: Executing Split Command: {cmd}")
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Find the generated chunks
            # We match the pattern: directory/filename_no_ext_chunk_*.mp4
            search_pattern = os.path.join(directory, f"{filename_no_ext}_chunk_*.mp4")
            chunks = glob.glob(search_pattern)
            return sorted(chunks)
            
        except subprocess.CalledProcessError as e:
            print(f"Error splitting video: {e}")
            return []

    def process_parallel(self, chunks, progress_callback=None):
        """
        Runs apply_filter_worker on all chunks simultaneously.
        Returns tuple: (duration, ordered_output_paths)
        """
        if not chunks:
            return 0.0, []

        start_time = time.time()
        
        # Keep track of futures in order to preserve sequence
        ordered_futures = []
        
        with ProcessPoolExecutor() as executor:
            # Submit all tasks
            for chunk in chunks:
                ordered_futures.append(executor.submit(apply_filter_worker, chunk))
            
            # Monitor completion (for progress bar only)
            total = len(chunks)
            completed_count = 0
            
            # We use as_completed only for the progress reporting side-effect
            for i, future in enumerate(as_completed(ordered_futures)):
                # We don't check result here to avoid blocking order, 
                # but as_completed yields as soon as one is done.
                if progress_callback:
                    progress_callback((i + 1) / total)
            
            # Collect results in original order
            results = []
            for future in ordered_futures:
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Worker failed: {e}")
            
        duration = time.time() - start_time
        return duration, results

    def merge_chunks(self, processed_files, output_path):
        """
        Merges processed video chunks into a single video file.
        Generates a temporary list file for ffmpeg concat demuxer.
        Cleans up intermediate chunk files after successful merge.
        """
        if not processed_files:
            return False

        ffmpeg_exe = self._get_ffmpeg_exe()

        # Sort files to ensure correct order
        # Note: If passing ordered list from process_parallel, this sort is redundant 
        # but harmless if names were sortable. 
        # With hash names, we MUST rely on the list order passed in.
        # processed_files.sort() <--- DISABLED for hash-based naming
        
        # Create list file
        list_file_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
        
        try:
            with open(list_file_path, "w") as f:
                for file_path in processed_files:
                    # ffmpeg requires forward slashes and escaped paths if needed
                    # safe 0 allows absolute paths
                    f.write(f"file '{file_path}'\n")
            
            # ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4
            cmd = [
                ffmpeg_exe, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                output_path
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Cleanup
            os.remove(list_file_path)
            for file_path in processed_files:
                try:
                   os.remove(file_path)
                except OSError as e:
                    print(f"Error removing chunk {file_path}: {e}")
            
            return True
            
        except (IOError, subprocess.CalledProcessError) as e:
            print(f"Error merging chunks: {e}")
            return False
