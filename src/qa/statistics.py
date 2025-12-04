"""Generate statistics and reports about PII de-identification."""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StatisticsGenerator:
    """Generates statistics about the de-identification process."""

    def __init__(self):
        """Initialize statistics generator."""
        logger.info("Initialized StatisticsGenerator")

    def generate_conversation_stats(self, conversation: Dict) -> Dict:
        """
        Generate statistics for a single conversation.

        Args:
            conversation: Conversation dictionary

        Returns:
            Statistics dictionary
        """
        segments = conversation.get('segments', [])
        pii_summary = conversation.get('pii_summary', {})
        redaction_log = conversation.get('redaction_log', {})

        # Calculate total duration (handle None end_time for last segment)
        total_duration = 0
        if segments:
            last_segment = segments[-1]
            if isinstance(last_segment, dict):
                # If it's a dict, use get()
                end_time = last_segment.get('end_time') or last_segment.get('start_time', 0)
            else:
                # If it's a dataclass, use attribute access
                end_time = getattr(last_segment, 'end_time', None) or getattr(last_segment, 'start_time', 0)
            total_duration = end_time

        # Extract speakers (handle both dict and dataclass)
        speakers = []
        for s in segments:
            if isinstance(s, dict):
                speakers.append(s.get('speaker'))
            else:
                speakers.append(getattr(s, 'speaker', None))
        speakers = list(set(filter(None, speakers)))

        return {
            'conversation_id': conversation.get('conversation_id'),
            'total_segments': len(segments),
            'total_duration': total_duration,
            'speakers': speakers,
            'pii_found': pii_summary.get('total_pii_found', 0),
            'pii_by_category': pii_summary.get('categories', {}),
            'total_replacements': redaction_log.get('total_replacements', 0)
        }

    def generate_dataset_stats(self, conversations: List[Dict]) -> Dict:
        """
        Generate statistics for entire dataset.

        Args:
            conversations: List of conversation dictionaries

        Returns:
            Dataset statistics dictionary
        """
        total_pii = 0
        pii_by_category = {}
        total_segments = 0
        total_duration = 0

        for conv in conversations:
            stats = self.generate_conversation_stats(conv)
            total_pii += stats['pii_found']
            total_segments += stats['total_segments']
            total_duration += stats['total_duration']

            # Aggregate category counts
            for category, count in stats['pii_by_category'].items():
                pii_by_category[category] = pii_by_category.get(category, 0) + count

        return {
            'total_conversations': len(conversations),
            'total_segments': total_segments,
            'total_duration': total_duration,
            'total_pii_instances': total_pii,
            'pii_by_category': pii_by_category,
            'avg_pii_per_conversation': total_pii / len(conversations) if conversations else 0
        }

    def generate_qa_report(
        self,
        dataset_stats: Dict,
        verification_results: Dict,
        output_path: Path
    ):
        """
        Generate comprehensive QA report.

        Args:
            dataset_stats: Dataset statistics
            verification_results: Verification results
            output_path: Path to save report
        """
        logger.info(f"Generating QA report: {output_path}")

        report = {
            'generated_at': datetime.now().isoformat(),
            'dataset_summary': dataset_stats,
            'verification': {
                'total_conversations': verification_results['total_conversations'],
                'failed_conversations': len(verification_results['failed_conversations']),
                'pass_rate': verification_results['pass_rate'],
                'pii_remaining': verification_results['total_pii_found']
            },
            'status': 'PASS' if verification_results['passed'] else 'FAIL'
        }

        # Save as JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Also create markdown report
        md_path = output_path.with_suffix('.md')
        self._generate_markdown_report(report, md_path)

        logger.info(f"QA report saved: {output_path}")

    def _generate_markdown_report(self, report: Dict, output_path: Path):
        """
        Generate markdown version of QA report.

        Args:
            report: Report dictionary
            output_path: Path to save markdown report
        """
        md_lines = [
            "# PII De-Identification QA Report",
            "",
            f"**Generated:** {report['generated_at']}",
            f"**Status:** {report['status']}",
            "",
            "---",
            "",
            "## Dataset Summary",
            "",
            f"- **Total Conversations:** {report['dataset_summary']['total_conversations']}",
            f"- **Total Segments:** {report['dataset_summary']['total_segments']}",
            f"- **Total Duration:** {report['dataset_summary']['total_duration']:.2f}s",
            f"- **Total PII Instances Found:** {report['dataset_summary']['total_pii_instances']}",
            f"- **Average PII per Conversation:** {report['dataset_summary']['avg_pii_per_conversation']:.1f}",
            "",
            "### PII by Category",
            ""
        ]

        for category, count in report['dataset_summary']['pii_by_category'].items():
            md_lines.append(f"- **{category.title()}:** {count}")

        md_lines.extend([
            "",
            "---",
            "",
            "## Verification Results",
            "",
            f"- **Pass Rate:** {report['verification']['pass_rate']:.2%}",
            f"- **PII Remaining:** {report['verification']['pii_remaining']}",
            f"- **Failed Conversations:** {report['verification']['failed_conversations']}",
            "",
            "---",
            ""
        ])

        if report['status'] == 'PASS':
            md_lines.extend([
                "## ✅ All Checks Passed",
                "",
                "No PII detected in de-identified transcripts.",
                ""
            ])
        else:
            md_lines.extend([
                "## ⚠️ Verification Failed",
                "",
                f"Found {report['verification']['pii_remaining']} PII instances remaining.",
                "Review failed conversations for details.",
                ""
            ])

        with open(output_path, 'w') as f:
            f.write('\n'.join(md_lines))

        logger.info(f"Markdown report saved: {output_path}")


def main():
    """Test the statistics generator."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    print("\n=== Statistics Generator Ready ===")
    print("Can generate:")
    print("  - Conversation-level statistics")
    print("  - Dataset-level statistics")
    print("  - QA reports (JSON and Markdown)")


if __name__ == "__main__":
    main()
