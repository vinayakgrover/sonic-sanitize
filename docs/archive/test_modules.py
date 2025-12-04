#!/usr/bin/env python3
"""Quick test script to verify all modules are working."""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")

    try:
        from src.ingestion.downloader import HuggingFaceDownloader
        from src.ingestion.organizer import DataOrganizer
        print("  ✓ Ingestion modules")
    except ImportError as e:
        print(f"  ✗ Ingestion modules: {e}")
        return False

    try:
        from src.parsing.transcript_parser import TranscriptParser
        print("  ✓ Parsing modules")
    except ImportError as e:
        print(f"  ✗ Parsing modules: {e}")
        return False

    try:
        from src.deid.config_loader import ConfigLoader
        from src.deid.pii_detector import PIIDetector
        from src.deid.text_redactor import TextRedactor
        print("  ✓ De-identification modules")
    except ImportError as e:
        print(f"  ✗ De-identification modules: {e}")
        return False

    try:
        from src.audio.forced_aligner import ForcedAligner
        from src.audio.audio_modifier import AudioModifier
        print("  ✓ Audio modules")
    except ImportError as e:
        print(f"  ✗ Audio modules: {e}")
        return False

    try:
        from src.qa.verifier import PIIVerifier
        from src.qa.statistics import StatisticsGenerator
        from src.qa.spot_checker import SpotChecker
        print("  ✓ QA modules")
    except ImportError as e:
        print(f"  ✗ QA modules: {e}")
        return False

    try:
        from src.curation.packager import DatasetPackager
        from src.curation.metadata_generator import MetadataGenerator
        print("  ✓ Curation modules")
    except ImportError as e:
        print(f"  ✗ Curation modules: {e}")
        return False

    try:
        from src.main import PIIDeIdentificationPipeline
        print("  ✓ Main pipeline")
    except ImportError as e:
        print(f"  ✗ Main pipeline: {e}")
        return False

    return True


def test_config():
    """Test that config.yaml exists and can be loaded."""
    print("\nTesting configuration...")

    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"  ✗ config.yaml not found")
        return False

    try:
        from src.deid.config_loader import ConfigLoader
        loader = ConfigLoader(config_path)
        categories = loader.get_all_categories()
        print(f"  ✓ Loaded config with {len(categories)} PII categories")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load config: {e}")
        return False


def test_pii_detection():
    """Test PII detection with sample text."""
    print("\nTesting PII detection...")

    try:
        from src.deid.pii_detector import PIIDetector

        detector = PIIDetector()
        test_text = "I'm from Dallas, Texas and visited Houston on Friday in January."

        matches = detector.detect_in_text(test_text)

        if len(matches) > 0:
            print(f"  ✓ Detected {len(matches)} PII instances:")
            for match in matches:
                print(f"      {match.value} ({match.category}) -> {match.tag}")
            return True
        else:
            print(f"  ✗ No PII detected in test text")
            return False

    except Exception as e:
        print(f"  ✗ PII detection failed: {e}")
        return False


def test_transcript_parsing():
    """Test transcript parsing."""
    print("\nTesting transcript parsing...")

    try:
        from src.parsing.transcript_parser import TranscriptParser

        parser = TranscriptParser()
        test_content = """
        [0.000] <Speaker_1> Hello, I'm from Dallas, Texas.
        [3.500] <Speaker_2> Nice to meet you!
        """

        segments = parser.parse_content(test_content)

        if len(segments) == 2:
            print(f"  ✓ Parsed {len(segments)} segments")
            print(f"      Segment 1: {segments[0].speaker} at {segments[0].start_time}s")
            print(f"      Segment 2: {segments[1].speaker} at {segments[1].start_time}s")
            return True
        else:
            print(f"  ✗ Expected 2 segments, got {len(segments)}")
            return False

    except Exception as e:
        print(f"  ✗ Transcript parsing failed: {e}")
        return False


def test_text_redaction():
    """Test text redaction."""
    print("\nTesting text redaction...")

    try:
        from src.deid.pii_detector import PIIDetector
        from src.deid.text_redactor import TextRedactor

        detector = PIIDetector()
        redactor = TextRedactor()

        test_text = "I'm from Dallas, Texas."
        matches = detector.detect_in_text(test_text)
        redacted, _ = redactor.redact_text(test_text, matches)

        if "[CITY]" in redacted and "[STATE]" in redacted:
            print(f"  ✓ Redaction successful")
            print(f"      Original: {test_text}")
            print(f"      Redacted: {redacted}")
            return True
        else:
            print(f"  ✗ Redaction failed")
            print(f"      Original: {test_text}")
            print(f"      Redacted: {redacted}")
            return False

    except Exception as e:
        print(f"  ✗ Text redaction failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("PII DE-IDENTIFICATION PIPELINE - MODULE TESTS")
    print("=" * 80)

    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("PII Detection", test_pii_detection),
        ("Transcript Parsing", test_transcript_parsing),
        ("Text Redaction", test_text_redaction),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed! Ready to run pipeline.")
    else:
        print("✗ Some tests failed. Check requirements.txt and dependencies.")

    print("=" * 80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
