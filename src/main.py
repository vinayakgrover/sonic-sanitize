"""Main pipeline orchestrator for PII de-identification."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .ingestion.downloader import HuggingFaceDownloader
from .ingestion.organizer import DataOrganizer
from .parsing.transcript_parser import TranscriptParser
from .deid.pii_detector import PIIDetector
from .deid.text_redactor import TextRedactor
from .audio.forced_aligner import ForcedAligner
from .audio.audio_modifier import AudioModifier
from .qa.verifier import PIIVerifier
from .qa.statistics import StatisticsGenerator
from .qa.spot_checker import SpotChecker
from .curation.packager import DatasetPackager
from .curation.metadata_generator import MetadataGenerator
from .utils.logger import setup_logger, get_logger
from .utils.progress import create_progress_bar

# Setup logging
log_file = Path("output/logs/pipeline.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
setup_logger("src", log_file=log_file, level=20)
logger = get_logger(__name__)


class PIIDeIdentificationPipeline:
    """Main pipeline for de-identifying conversational audio dataset."""

    def __init__(
        self,
        config_path: Path = Path("config.yaml"),
        output_dir: Path = Path("output"),
        limit_conversations: Optional[int] = None
    ):
        """
        Initialize pipeline.

        Args:
            config_path: Path to config.yaml
            output_dir: Directory for outputs
            limit_conversations: Limit number of conversations (for testing)
        """
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.limit = limit_conversations

        # Load MFA configuration
        mfa_config = self._load_mfa_config(config_path)

        # Initialize components
        logger.info("Initializing pipeline components")
        self.downloader = HuggingFaceDownloader()
        self.organizer = DataOrganizer()
        self.parser = TranscriptParser()
        self.detector = PIIDetector(config_path)
        self.redactor = TextRedactor()

        # Initialize forced aligner with MFA config
        self.aligner = ForcedAligner(use_mfa=True, mfa_config=mfa_config)

        self.audio_modifier = AudioModifier()
        self.verifier = PIIVerifier(config_path)
        self.stats_generator = StatisticsGenerator()
        self.spot_checker = SpotChecker()
        self.packager = DatasetPackager(output_dir)
        self.metadata_generator = MetadataGenerator()

        # Log which alignment method will be used
        if self.aligner.mfa_aligner:
            logger.info("✓ Using MFA for word-level audio alignment")
        else:
            logger.info("→ Using segment-level audio muting (MFA not available)")

        logger.info("Pipeline initialized")

    def _load_mfa_config(self, config_path: Path) -> dict:
        """
        Load MFA configuration from config.yaml or environment variables.

        Args:
            config_path: Path to config.yaml

        Returns:
            Dictionary with MFA configuration
        """
        import yaml
        import os

        mfa_config = {
            'acoustic_model': 'english_us_arpa',
            'dictionary': 'english_us_arpa',
            'temp_dir': None,
            'cleanup': True
        }

        # Try to load from config.yaml
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                    # Look for MFA section
                    if 'mfa' in config:
                        mfa_section = config['mfa']
                        mfa_config['acoustic_model'] = mfa_section.get('acoustic_model', mfa_config['acoustic_model'])
                        mfa_config['dictionary'] = mfa_section.get('dictionary', mfa_config['dictionary'])
                        mfa_config['temp_dir'] = mfa_section.get('temp_dir')
                        mfa_config['cleanup'] = mfa_section.get('cleanup', True)

                        logger.info(f"Loaded MFA config: model={mfa_config['acoustic_model']}, "
                                  f"dict={mfa_config['dictionary']}")
            except Exception as e:
                logger.warning(f"Failed to load MFA config from {config_path}: {e}")

        # Override with environment variables if present
        if 'MFA_ACOUSTIC_MODEL' in os.environ:
            mfa_config['acoustic_model'] = os.environ['MFA_ACOUSTIC_MODEL']
            logger.info(f"Using MFA acoustic model from env: {mfa_config['acoustic_model']}")

        if 'MFA_DICTIONARY' in os.environ:
            mfa_config['dictionary'] = os.environ['MFA_DICTIONARY']
            logger.info(f"Using MFA dictionary from env: {mfa_config['dictionary']}")

        return mfa_config

    def run(self):
        """Execute the complete pipeline."""
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("PII DE-IDENTIFICATION PIPELINE STARTED")
        logger.info("=" * 80)

        try:
            # Stage 1: Ingest data
            logger.info("\n[STAGE 1/7] Data Ingestion")
            downloaded_files = self.downloader.download_dataset(limit=self.limit)
            organized_files = self.organizer.organize_files(downloaded_files)
            conversation_pairs = self.organizer.get_conversation_pairs()
            logger.info(f"✓ Ingested {len(conversation_pairs)} conversation pairs")

            # Stage 2: Parse transcripts
            logger.info("\n[STAGE 2/7] Transcript Parsing")
            parsed_conversations = []
            for audio_path, transcript_path in create_progress_bar(
                conversation_pairs, desc="Parsing transcripts", unit="files"
            ):
                conv_id = audio_path.stem
                segments = self.parser.parse_file(transcript_path)
                parsed_conversations.append({
                    'conversation_id': conv_id,
                    'audio_path': audio_path,
                    'transcript_path': transcript_path,
                    'segments': segments
                })
            logger.info(f"✓ Parsed {len(parsed_conversations)} transcripts")

            # Stage 3: Detect PII
            logger.info("\n[STAGE 3/7] PII Detection")
            for conv in create_progress_bar(
                parsed_conversations, desc="Detecting PII", unit="conversations"
            ):
                pii_matches = self.detector.detect_in_segments(conv['segments'])
                conv['pii_matches'] = pii_matches

                # Calculate summary
                all_matches = []
                for matches in pii_matches.values():
                    all_matches.extend(matches)
                summary = self.detector.get_pii_summary(all_matches)
                conv['pii_summary'] = {
                    'total_pii_found': len(all_matches),
                    'categories': summary
                }
            logger.info(f"✓ Detected PII in {len(parsed_conversations)} conversations")

            # Stage 4: De-identify transcripts
            logger.info("\n[STAGE 4/7] Transcript De-Identification")
            for conv in create_progress_bar(
                parsed_conversations, desc="De-identifying transcripts", unit="conversations"
            ):
                deid_segments, redaction_log = self.redactor.redact_segments(
                    conv['segments'], conv['pii_matches']
                )
                conv['deid_segments'] = deid_segments
                conv['redaction_log'] = redaction_log
            logger.info(f"✓ De-identified {len(parsed_conversations)} transcripts")

            # Stage 5: De-identify audio
            logger.info("\n[STAGE 5/7] Audio De-Identification")
            deid_audio_files = {}

            for conv in create_progress_bar(
                parsed_conversations, desc="De-identifying audio", unit="conversations"
            ):
                try:
                    # Check if this conversation has PII
                    if not conv['pii_matches']:
                        # No PII, just copy audio as-is
                        output_audio_path = Path("data/processed/audio") / f"{conv['conversation_id']}.flac"
                        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(conv['audio_path'], output_audio_path)
                        deid_audio_files[conv['conversation_id']] = output_audio_path
                        logger.debug(f"No PII in {conv['conversation_id']}, copied audio as-is")
                        continue

                    # Try word-level alignment first
                    pii_timings = []
                    try:
                        word_timings = self.aligner.align_audio_with_transcript(
                            conv['audio_path'],
                            conv['segments'],
                            conversation_id=conv['conversation_id']
                        )

                        if word_timings:  # Word-level alignment succeeded
                            all_pii_matches = []
                            for matches in conv['pii_matches'].values():
                                all_pii_matches.extend(matches)

                            pii_timings = self.aligner.match_pii_to_words(
                                all_pii_matches, word_timings
                            )
                            logger.debug(f"Using word-level alignment for {conv['conversation_id']}")
                        else:
                            raise ValueError("Word-level alignment returned empty")

                    except Exception as align_error:
                        # Fallback to segment-level muting
                        logger.warning(f"Word-level alignment failed for {conv['conversation_id']}, "
                                     f"falling back to segment-level muting: {align_error}")

                        # Mute entire segments that contain PII
                        for segment_idx, pii_matches in conv['pii_matches'].items():
                            if pii_matches:  # This segment has PII
                                segment = conv['segments'][segment_idx]
                                pii_timings.append({
                                    'start_time': segment.start_time,
                                    'end_time': segment.end_time or segment.start_time + 5.0,  # Default 5s if no end_time
                                    'text': f"[SEGMENT {segment_idx}]"
                                })
                        logger.info(f"Using segment-level muting for {conv['conversation_id']}: "
                                  f"{len(pii_timings)} segments to mute")

                    # Mute PII in audio (either word-level or segment-level)
                    if pii_timings:
                        output_audio_path = Path("data/processed/audio") / f"{conv['conversation_id']}.flac"
                        self.audio_modifier.process_audio_file(
                            conv['audio_path'],
                            output_audio_path,
                            pii_timings
                        )
                        deid_audio_files[conv['conversation_id']] = output_audio_path
                    else:
                        logger.warning(f"No PII timings generated for {conv['conversation_id']}, skipping audio")

                except Exception as e:
                    logger.error(f"Failed to process audio for {conv['conversation_id']}: {e}")
                    # Continue with other conversations

            logger.info(f"✓ De-identified {len(deid_audio_files)} audio files")

            # Stage 6: QA & Verification
            logger.info("\n[STAGE 6/7] Quality Assurance")

            # Verify de-identified transcripts
            deid_conversations = []
            for conv in parsed_conversations:
                deid_conv = {
                    'conversation_id': conv['conversation_id'],
                    'segments': [seg.to_dict() for seg in conv['deid_segments']],
                    'pii_summary': conv['pii_summary'],
                    'redaction_log': conv['redaction_log']
                }
                deid_conversations.append(deid_conv)

            verification_results = self.verifier.verify_dataset(deid_conversations)
            logger.info(f"✓ Verification: {verification_results['pass_rate']:.2%} pass rate")

            # Generate statistics
            dataset_stats = self.stats_generator.generate_dataset_stats(deid_conversations)
            dataset_stats['generated_at'] = datetime.now().isoformat()
            logger.info(f"✓ Generated statistics")

            # Generate QA report
            qa_report_path = self.output_dir / "qa" / "qa_report.json"
            self.stats_generator.generate_qa_report(
                dataset_stats, verification_results, qa_report_path
            )

            # Generate spot-check samples
            samples = self.spot_checker.generate_samples(deid_conversations, num_samples=10)
            samples_path = self.output_dir / "qa" / "spot_check_samples.jsonl"
            self.spot_checker.save_samples(samples, samples_path)

            logger.info(f"✓ QA complete")

            # Stage 7: Package dataset
            logger.info("\n[STAGE 7/7] Dataset Packaging")

            # Package conversations
            self.packager.package_dataset(deid_conversations, deid_audio_files)

            # Generate metadata
            metadata_path = self.output_dir / "metadata" / "conversations.parquet"
            self.metadata_generator.generate_conversations_metadata(
                deid_conversations, metadata_path
            )

            manifest_path = self.output_dir / "metadata" / "dataset_manifest.json"
            self.metadata_generator.generate_dataset_manifest(
                dataset_stats, verification_results, manifest_path
            )

            # Create README
            self.packager.create_readme(dataset_stats)

            logger.info(f"✓ Dataset packaged")

            # Final summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Duration: {duration:.1f}s")
            logger.info(f"Conversations processed: {len(deid_conversations)}")
            logger.info(f"PII instances removed: {dataset_stats['total_pii_instances']}")
            logger.info(f"Verification pass rate: {verification_results['pass_rate']:.2%}")
            logger.info(f"Output directory: {self.output_dir}")
            logger.info("=" * 80)

            return {
                'success': True,
                'conversations_processed': len(deid_conversations),
                'pii_removed': dataset_stats['total_pii_instances'],
                'pass_rate': verification_results['pass_rate'],
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="PII De-Identification Pipeline for Conversational Audio"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of conversations to process (for testing)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )

    args = parser.parse_args()

    # Print banner
    print("\n" + "=" * 80)
    print("PII DE-IDENTIFICATION PIPELINE")
    print("=" * 80)
    if args.limit:
        print(f"Mode: Testing (limit={args.limit} conversations)")
    else:
        print("Mode: Full dataset processing")
    print("=" * 80 + "\n")

    # Run pipeline
    pipeline = PIIDeIdentificationPipeline(
        config_path=Path(args.config),
        limit_conversations=args.limit
    )

    result = pipeline.run()

    # Print summary
    if result['success']:
        print("\n✓ Pipeline completed successfully!")
        print(f"  Processed: {result['conversations_processed']} conversations")
        print(f"  PII removed: {result['pii_removed']} instances")
        print(f"  Pass rate: {result['pass_rate']:.2%}")
        print(f"  Duration: {result['duration_seconds']:.1f}s")
        print(f"\nOutputs in: output/")
    else:
        print(f"\n✗ Pipeline failed: {result['error']}")
        print("Check output/logs/pipeline.log for details")


if __name__ == "__main__":
    main()
