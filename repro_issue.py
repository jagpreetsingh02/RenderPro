import os
import utils
from processor import VideoEngine
import shutil
import time

# Setup
log_file = "repro_log.txt"
def log(msg):
    with open(log_file, "a") as f:
        f.write(msg + "\n")

if __name__ == "__main__":
    utils.ensure_temp_folder()
    original_video = "185947-876963225_small.mp4"
    input_path = os.path.join(utils.TEMP_FOLDER, "test_video.mp4")

    # Simulate upload
    if os.path.exists(original_video):
        shutil.copy(original_video, input_path)
        log(f"Copied {original_video} to {input_path}")
    else:
        log(f"File {original_video} not found!")
        exit(1)

    engine = VideoEngine()

    log("1. Splitting...")
    chunks = engine.split_video(input_path, chunk_length=5)
    log(f"Chunks: {len(chunks)}")

    if not chunks:
        log("Splitting failed.")
        exit(1)

    log("2. Processing Run 1...")
    def update_bar(p):
        pass # log(f"Progress: {p*100:.1f}%")

    start = time.time()
    duration1, processed_files1 = engine.process_parallel(chunks, progress_callback=update_bar)
    log(f"Run 1 done in {duration1:.2f}s. Files: {len(processed_files1)}")

    log("2. Processing Run 2 (Should be instant)...")
    start = time.time()
    duration2, processed_files2 = engine.process_parallel(chunks, progress_callback=update_bar)
    log(f"Run 2 done in {duration2:.2f}s. Files: {len(processed_files2)}")
    
    if duration2 < 1.0:
        log("SUCCESS: Caching works!")
    else:
        log(f"WARNING: Run 2 took {duration2:.2f}s")

    log("3. Merging...")
    final_output_path = os.path.join(utils.TEMP_FOLDER, "final_output.mp4")
    # processed_dir = os.path.join(utils.TEMP_FOLDER, "processed")
    # processed_files = sorted([os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith('.mp4')])

    success = engine.merge_chunks(processed_files2, final_output_path)
    if success:
        log("Merge successful!")
    else:
        log("Merge failed.")
