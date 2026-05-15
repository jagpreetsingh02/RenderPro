import streamlit as st
import os
import utils
from processor import VideoEngine

# Page Config
st.set_page_config(
    page_title="RenderPro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar ---
st.sidebar.title("⚙️ System Architecture")
st.sidebar.info(
    """
    **MapReduce-style Video Processing**
    
    1. **Split (Map)**: 
       The video is segmented into small chunks using FFmpeg.
       
    2. **Process (Parallel Workers)**: 
       Each chunk is processed independently in parallel using Python's `ProcessPoolExecutor`.
       
    3. **Merge (Reduce)**: 
       Processed chunks are stitched back together to form the final output.
    """
)

st.sidebar.divider()
st.sidebar.subheader("Utilities")
if st.sidebar.button("🗑️ Clear Cache", type="secondary"):
    utils.clean_temp_folder()
    st.sidebar.success("Temp folder cleared!")
    # Re-ensure temp folder exists after cleaning
    utils.ensure_temp_folder()

# --- Main App ---
st.title("🚀 RenderPro")
st.markdown("### High-Performance Parallel Video Processing Node")

# Ensure temp folder exists
utils.ensure_temp_folder()

# Upload Section
uploaded_file = st.file_uploader("📂 Upload Video (MP4/AVI/MOV)", type=['mp4', 'avi', 'mov', 'mkv'])

if uploaded_file:
    # Save uploaded file
    input_path = os.path.join(utils.TEMP_FOLDER, uploaded_file.name)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Action Section
    st.divider()
    col_action, col_status = st.columns([1, 3])
    
    with col_action:
        start_btn = st.button("▶️ Start Distributed Render", type="primary", use_container_width=True)

    if start_btn:
        final_output_path = os.path.join(utils.TEMP_FOLDER, f"final_{uploaded_file.name}")
        
        # Progress UI
        progress_container = st.container()
        with progress_container:
            split_bar = st.progress(0, text="⏳ Initializing Splitter...")
            process_bar = st.progress(0, text="⏳ Waiting for Chunks...")
            merge_status = st.empty()

        engine = VideoEngine()

        try:
            # 1. Splitting
            chunks = engine.split_video(input_path, chunk_length=5)
            split_bar.progress(100, text=f"✅ Splitting Complete ({len(chunks)} Segments)")
            
            if not chunks:
                st.error("Operation Failed: Could not split video. Check FFmpeg installation.")
            else:
                # 2. Processing
                def update_bar(progress):
                    percentage = int(progress * 100)
                    process_bar.progress(progress, text=f"⚙️ Processing Chunks via ProcessPoolExecutor... {percentage}%")
                
                duration, processed_files = engine.process_parallel(chunks, progress_callback=update_bar)
                process_bar.progress(100, text="✅ Parallel Processing Complete!")
                
                # 3. Merging
                merge_status.info("🔗 Merging chunks...")
                
                if not processed_files:
                     st.error("Error: Processing returned no files.")
                else:
                    if engine.merge_chunks(processed_files, final_output_path):
                        merge_status.success("✅ Merge Complete!")
                        
                        st.divider()
                        st.subheader("📊 Performance Metrics")
                        
                        # Metrics Layout
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Processing Time", f"{duration:.2f}s", delta="Parallel Execution")
                        m2.metric("Chunk Count", len(chunks), "Segments")
                        if len(chunks) > 0:
                            m3.metric("Avg Time / Chunk", f"{duration/len(chunks):.2f}s", "Thread Speed")
                        
                        st.divider()
                        st.subheader("🎬 Results Comparison")
                        
                        # Video Comparison
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption("Original Input")
                            st.video(input_path)
                        with c2:
                            st.caption("Processed Output (Grayscale)")
                            st.video(final_output_path)
                            
                    else:
                        st.error("Merge Failed.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.exception(e)

# Debugging / Footer
st.divider()
with st.expander("🛠️ Debug: Temp Directory Content"):
    files = utils.get_video_files()
    st.write(files if files else "No files in /temp")
