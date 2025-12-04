"""
PII De-Identification Pipeline - Results Explorer

Interactive Streamlit app to explore processed conversations from the PII de-identification pipeline.

## Installation
```bash
pip install streamlit
```

## Usage
```bash
streamlit run streamlit_app.py
```

## What This Shows
- De-identified transcripts with PII replaced by tags (e.g., [CITY], [STATE])
- Original raw transcripts for comparison (if available)
- De-identified audio files with PII segments muted
- QA verification results and statistics
- Per-conversation PII summaries

## Note on Audio Redaction
Current implementation uses **segment-level muting** (mutes entire segments containing PII).
Word-level precision via Montreal Forced Aligner (MFA) is planned for v2.0.

## Audio Playback
FLAC files are converted to WAV in-memory for browser compatibility.
"""

import streamlit as st
import json
import re
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import soundfile as sf
import pandas as pd


# Configuration
OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")
TRANSCRIPTS_DEID_DIR = OUTPUT_DIR / "transcripts_deid" / "train"
AUDIO_DEID_DIR = OUTPUT_DIR / "audio" / "train"
TRANSCRIPTS_RAW_DIR = DATA_DIR / "raw" / "transcripts"
QA_REPORT_PATH = OUTPUT_DIR / "qa" / "qa_report.json"


# Utility Functions
def strip_markup_tags(text: str) -> str:
    """Remove audio markup tags like <cough>, <lipsmack>, etc."""
    # Pattern matches tags like <int>, <cough>, <lipsmack>, <hesitation>, etc.
    clean_text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text


def highlight_pii_tags(text: str) -> str:
    """Highlight PII tags with colored HTML spans."""
    # Define colors for different PII categories
    tag_colors = {
        '[CITY]': '#FF6B6B',      # Red
        '[STATE]': '#4ECDC4',     # Teal
        '[DAY]': '#FFE66D',       # Yellow
        '[MONTH]': '#95E1D3',     # Mint
        '[COLOR]': '#F38181',     # Pink
    }

    highlighted = text
    for tag, color in tag_colors.items():
        # Use HTML with background color for highlighting
        highlighted = highlighted.replace(
            tag,
            f'<span style="background-color: {color}; padding: 2px 6px; border-radius: 3px; font-weight: bold; color: #2C3E50;">{tag}</span>'
        )

    return highlighted


def convert_flac_to_wav_bytes(flac_path: Path) -> Optional[bytes]:
    """Convert FLAC file to WAV bytes for st.audio compatibility."""
    try:
        # Read FLAC file
        audio_data, sample_rate = sf.read(str(flac_path))

        # Write to WAV in memory
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format='WAV')
        wav_buffer.seek(0)

        return wav_buffer.read()
    except Exception as e:
        st.error(f"Audio conversion error: {e}")
        return None


@st.cache_data
def load_qa_report() -> Optional[Dict]:
    """Load QA report with overall statistics."""
    try:
        if QA_REPORT_PATH.exists():
            with open(QA_REPORT_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Failed to load QA report: {e}")
    return None


@st.cache_data
def list_conversations() -> List[str]:
    """List all available de-identified conversations."""
    try:
        if TRANSCRIPTS_DEID_DIR.exists():
            json_files = sorted(TRANSCRIPTS_DEID_DIR.glob("*.json"))
            return [f.stem for f in json_files]
    except Exception as e:
        st.error(f"Failed to list conversations: {e}")
    return []


@st.cache_data
def load_deid_transcript(conv_id: str) -> Optional[Dict]:
    """Load de-identified transcript JSON."""
    try:
        transcript_path = TRANSCRIPTS_DEID_DIR / f"{conv_id}.json"
        if transcript_path.exists():
            with open(transcript_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Failed to load de-identified transcript: {e}")
    return None


@st.cache_data
def load_raw_transcript(conv_id: str) -> Optional[str]:
    """Load raw transcript text (best-effort)."""
    try:
        raw_path = TRANSCRIPTS_RAW_DIR / f"{conv_id}.txt"
        if raw_path.exists():
            with open(raw_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        # Silently fail - raw transcripts are optional
        pass
    return None


def get_audio_path(conv_id: str) -> Optional[Path]:
    """Get path to de-identified audio file."""
    audio_path = AUDIO_DEID_DIR / f"{conv_id}.flac"
    return audio_path if audio_path.exists() else None


def display_summary_metrics(qa_report: Optional[Dict]):
    """Display high-level QA metrics."""
    st.markdown("### 📊 Dataset Summary")

    if qa_report:
        dataset_summary = qa_report.get('dataset_summary', {})
        verification = qa_report.get('verification', {})
        status = qa_report.get('status', 'UNKNOWN')

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Conversations",
                dataset_summary.get('total_conversations', 0)
            )

        with col2:
            st.metric(
                "PII Removed",
                dataset_summary.get('total_pii_instances', 0)
            )

        with col3:
            pass_rate = verification.get('pass_rate', 0) * 100
            st.metric(
                "QA Pass Rate",
                f"{pass_rate:.1f}%"
            )

        with col4:
            status_color = "🟢" if status == "PASS" else "🔴"
            st.metric(
                "Status",
                f"{status_color} {status}"
            )

        # PII categories breakdown
        if dataset_summary.get('pii_by_category'):
            st.markdown("**PII Categories Found:**")
            categories = dataset_summary['pii_by_category']
            category_str = ", ".join([f"{cat.title()}: {count}" for cat, count in categories.items()])
            st.caption(category_str)
    else:
        st.warning("QA report not found. Run the pipeline first.")


def display_transcript_comparison(conv_id: str, deid_data: Dict):
    """Display de-identified and raw transcripts side-by-side."""
    st.markdown("### 📝 Transcript Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### De-Identified Transcript")
        st.caption("PII replaced with category tags • Audio markup removed for clarity")

        segments = deid_data.get('segments', [])
        if segments:
            # Prepare data for table
            table_data = []
            for seg in segments:
                speaker = seg.get('speaker', 'Unknown')
                text = seg.get('text', '')
                start_time = seg.get('start_time', 0)

                # Strip markup and highlight PII tags
                clean_text = strip_markup_tags(text)
                highlighted_text = highlight_pii_tags(clean_text)

                table_data.append({
                    "Time": f"{start_time:.2f}s",
                    "Speaker": speaker.replace("Speaker_", "S"),
                    "Text": highlighted_text
                })

            # Display as DataFrame with HTML rendering for highlights
            df = pd.DataFrame(table_data)

            # Use st.markdown with HTML to render the table with highlighting
            st.markdown(
                df.to_html(escape=False, index=False),
                unsafe_allow_html=True
            )
        else:
            st.info("No segments found in transcript")

    with col2:
        st.markdown("#### Raw Transcript")
        st.caption("Original with timestamps and markup")

        raw_text = load_raw_transcript(conv_id)
        if raw_text:
            # Show first N lines with expand option
            lines = raw_text.strip().split('\n')
            preview_lines = 15

            if len(lines) <= preview_lines:
                # Short transcript - show all
                st.text(raw_text)
            else:
                # Long transcript - show preview with expander
                preview = '\n'.join(lines[:preview_lines])
                st.text(preview)

                with st.expander(f"📄 Show all {len(lines)} lines"):
                    st.text(raw_text)
        else:
            st.info("Raw transcript not available")


def display_audio_player(conv_id: str):
    """Display audio player for de-identified audio."""
    st.markdown("### 🔊 De-Identified Audio")

    audio_path = get_audio_path(conv_id)

    if audio_path:
        st.caption("🔇 PII segments muted • Converted from FLAC to WAV for playback")

        # Convert FLAC to WAV for better browser compatibility
        wav_bytes = convert_flac_to_wav_bytes(audio_path)

        if wav_bytes:
            st.audio(wav_bytes, format='audio/wav')
        else:
            st.error("Failed to convert audio for playback")
    else:
        st.warning("Audio file not found")


def display_pii_summary(deid_data: Dict):
    """Display PII summary for this conversation."""
    st.markdown("### 🔍 PII Detection Summary")

    pii_summary = deid_data.get('pii_summary', {})
    redaction_log = deid_data.get('redaction_log', {})

    if pii_summary or redaction_log:
        col1, col2 = st.columns(2)

        with col1:
            total_pii = pii_summary.get('total_pii_found', 0)
            st.metric("PII Instances Found", total_pii)

        with col2:
            total_replacements = redaction_log.get('total_replacements', 0)
            st.metric("Replacements Made", total_replacements)

        # Categories breakdown
        categories = pii_summary.get('categories', {})
        if categories:
            st.markdown("**By Category:**")
            category_data = [
                {"Category": cat.title(), "Count": count}
                for cat, count in categories.items()
            ]
            st.dataframe(category_data, hide_index=True, use_container_width=True)

        # Detailed redaction log
        if redaction_log.get('by_segment'):
            with st.expander("View Detailed Redaction Log"):
                by_segment = redaction_log['by_segment']

                for seg_idx, replacements in by_segment.items():
                    st.markdown(f"**Segment {seg_idx}:**")
                    for repl in replacements:
                        st.caption(
                            f"  • `{repl.get('original')}` → "
                            f"`{repl.get('tag')}` ({repl.get('category')})"
                        )
    else:
        st.info("No PII detected in this conversation")


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="PII De-ID Explorer",
        page_icon="🔒",
        layout="wide"
    )

    # Custom CSS for better table styling
    st.markdown("""
        <style>
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        table thead tr {
            background-color: #2C3E50;
            color: white;
            text-align: left;
        }

        table th, table td {
            padding: 12px 15px;
            border: 1px solid #ddd;
        }

        table tbody tr {
            border-bottom: 1px solid #dddddd;
        }

        table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }

        table tbody tr:hover {
            background-color: #f1f1f1;
        }

        /* Ensure text column wraps properly */
        table td:nth-child(3) {
            max-width: 500px;
            word-wrap: break-word;
        }

        /* Better spacing */
        .block-container {
            padding-top: 2rem;
        }

        /* PII tag legend */
        .pii-legend {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 10px 0;
            font-size: 0.85rem;
        }

        .pii-legend-item {
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("🔒 PII De-Identification Pipeline - Results Explorer")
    st.markdown(
        "Explore processed conversations with de-identified transcripts and muted audio. "
        "See [README.md](README.md) for pipeline details."
    )

    # Banner about audio approach
    st.info(
        "ℹ️ **Audio Redaction:** Currently using segment-level muting (mutes entire segments containing PII). "
        "Word-level precision via Montreal Forced Aligner (MFA) is planned for v2.0. See TODO.md for roadmap."
    )

    # PII tag legend
    st.markdown("""
        <div class="pii-legend">
            <span>🏷️ <b>PII Tags:</b></span>
            <span class="pii-legend-item" style="background-color: #FF6B6B; color: #2C3E50;">[CITY]</span>
            <span class="pii-legend-item" style="background-color: #4ECDC4; color: #2C3E50;">[STATE]</span>
            <span class="pii-legend-item" style="background-color: #FFE66D; color: #2C3E50;">[DAY]</span>
            <span class="pii-legend-item" style="background-color: #95E1D3; color: #2C3E50;">[MONTH]</span>
            <span class="pii-legend-item" style="background-color: #F38181; color: #2C3E50;">[COLOR]</span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Load data
    qa_report = load_qa_report()
    conversations = list_conversations()

    if not conversations:
        st.error(
            "No processed conversations found. Please run the pipeline first:\n\n"
            "```bash\n"
            "python -m src.main --limit 3\n"
            "```"
        )
        st.stop()

    # Sidebar
    with st.sidebar:
        st.header("🗂️ Conversations")
        st.caption(f"{len(conversations)} conversations processed")

        selected_conv = st.selectbox(
            "Select Conversation",
            conversations,
            format_func=lambda x: x.replace("_", " ")
        )

        st.divider()

        st.markdown("### 📖 Quick Guide")
        st.caption(
            "- **Green text**: PII was found and redacted\n"
            "- **Tags**: [CITY], [STATE], [DAY], [MONTH], [COLOR]\n"
            "- **Audio**: Muted segments where PII was spoken"
        )

        st.divider()

        st.markdown("### 🔗 Links")
        st.markdown("- [README](README.md)")
        st.markdown("- [System Design](SYSTEM_DESIGN.md)")
        st.markdown("- [Roadmap](TODO.md)")

    # Main content
    # 1. Summary metrics
    with st.container():
        display_summary_metrics(qa_report)

    st.divider()

    # 2. Selected conversation details
    if selected_conv:
        st.header(f"📄 Conversation: {selected_conv.replace('_', ' ')}")

        deid_data = load_deid_transcript(selected_conv)

        if deid_data:
            # Transcript comparison
            with st.container():
                display_transcript_comparison(selected_conv, deid_data)

            st.divider()

            # Audio player
            with st.container():
                display_audio_player(selected_conv)

            st.divider()

            # PII summary
            with st.container():
                display_pii_summary(deid_data)
        else:
            st.error(f"Failed to load transcript for {selected_conv}")

    # Footer
    st.divider()
    st.caption(
        "Generated by PII De-Identification Pipeline v1.0 | "
        "Segment-level audio muting with word-level MFA planned for v2.0"
    )


if __name__ == "__main__":
    main()
