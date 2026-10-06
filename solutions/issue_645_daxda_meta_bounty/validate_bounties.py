#!/usr/bin/env python3
"""
DAXDA Bounty Validation Script
===============================
Validates that all generated bounties meet structural and content requirements.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class BountyValidationResult:
    """Result of validating a single bounty."""
    file_path: str
    is_valid: bool
    score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0


@dataclass
class ValidationSummary:
    """Summary of all bounty validations."""
    total_bounties: int
    valid_bounties: int
    invalid_bounties: int
    average_score: float
    results: List[BountyValidationResult] = field(default_factory=list)


class BountyValidator:
    """Validates DAXDA bounty documents against structural and content requirements."""
    
    REQUIRED_SECTIONS = [
        "# [BOUNTY]",
        "## Overview",
        "## 💰 Reward & Payment",
        "## 🎯 Objective",
        "## 📋 Technical Specification",
        "## 📋 Required Deliverables",
        "## ⚖️ Evaluation Criteria",
        "## 🔒 Constraints",
        "## 🎯 Recursive Expansion",
        "## 📝 Submission Format",
        "## ⏰ Timeline",
        "## 🏆 Judging Panel",
        "## 📞 Contact",
        "---",
    ]
    
    REQUIRED_METADATA = [
        "**Status**",
        "**Created**",
        "**Version**",
        "**Tags**",
        "**Platform**",
        "**Difficulty**",
        "**Estimated Effort**",
    ]
    
    TAG_PATTERN = re.compile(r'\[([^\]]+)\]')
    CURRENCY_PATTERN = re.compile(r'\$\d{4,5}')
    DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')
    
    def __init__(self, bounty_dir: str = "docs"):
        self.bounty_dir = Path(bounty_dir)
        self.bounty_files = self._find_bounty_files()
    
    def _find_bounty_files(self) -> List[Path]:
        """Find all bounty markdown files in the directory."""
        bounty_files = []
        for pattern in ["BOUNTY_*.md", "BOUNTY-DAXDA-*.md", "BOUNTY-DAXDA_*.md"]:
            bounty_files.extend(self.bounty_dir.glob(pattern))
        return sorted(bounty_files)
    
    def validate_all(self) -> ValidationSummary:
        """Validate all bounty files and return summary."""
        results = []
        total_score = 0.0
        
        for bounty_file in self.bounty_files:
            result = self.validate_bounty(bounty_file)
            results.append(result)
            total_score += result.score
            
        avg_score = total_score / len(results) if results else 0.0
        valid_count = sum(1 for r in results if r.is_valid)
        
        return ValidationSummary(
            total_bounties=len(results),
            valid_bounties=valid_count,
            invalid_bounties=len(results) - valid_count,
            average_score=round(avg_score, 2),
            results=results
        )
    
    def validate_bounty(self, file_path: Path) -> BountyValidationResult:
        """Validate a single bounty file."""
        result = BountyValidationResult(
            file_path=str(file_path),
            is_valid=True,
            score=0.0
        )
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Failed to read file: {e}")
            return result
        
        # Run all validation checks
        checks = [
            ("File Structure", self._check_file_structure, 0.1),
            ("Required Sections", self._check_required_sections, 0.25),
            ("Metadata Completeness", self._check_metadata, 0.15),
            ("Financial Information", self._check_financial_info, 0.1),
            ("Technical Depth", self._check_technical_depth, 0.15),
            ("Formatting Quality", self._check_formatting, 0.1),
            ("Recursive Fidelity", self._check_recursive_fidelity, 0.1),
            ("Content Length", self._check_content_length, 0.05),
            ("Timeline Information", self._check_timeline, 0.05),
        ]
        
        for check_name, check_func, weight in checks:
            result.checks_total += 1
            passed, errors, warnings = check_func(content, file_path)
            
            if passed:
                result.checks_passed += 1
                result.score += weight
            else:
                result.is_valid = False
                result.errors.extend(errors)
                result.warnings.extend(warnings)
        
        # Clamp score to [0, 1]
        result.score = max(0.0, min(1.0, result.score))
        
        return result
    
    def _check_file_structure(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check basic file structure."""
        errors = []
        warnings = []
        
        # Check file extension
        if not file_path.suffix.lower() == '.md':
            errors.append("File must have .md extension")
            return False, errors, warnings
        
        # Check file size
        if len(content) < 1000:
            errors.append("File too small (< 1000 bytes)")
            return False, errors, warnings
        
        # Check encoding
        try:
            content.encode('utf-8')
        except UnicodeEncodeError:
            errors.append("File contains invalid UTF-8 characters")
            return False, errors, warnings
        
        return True, errors, warnings
    
    def _check_required_sections(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check that all required sections are present."""
        errors = []
        warnings = []
        
        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                errors.append(f"Missing required section: {section}")
        
        if errors:
            return False, errors, warnings
        
        return True, errors, warnings
    
    def _check_metadata(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check that all required metadata is present."""
        errors = []
        warnings = []
        
        for metadata in self.REQUIRED_METADATA:
            if metadata not in content:
                errors.append(f"Missing required metadata: {metadata}")
        
        if errors:
            return False, errors, warnings
        
        # Check for version information
        if "**Version**" in content and "1.0.0" not in content:
            warnings.append("Consider using version 1.0.0 for consistency")
        
        return True, errors, warnings
    
    def _check_financial_info(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check financial information is present and valid."""
        errors = []
        warnings = []
        
        # Check for bounty amount
        if not self.CURRENCY_PATTERN.search(content):
            errors.append("Missing bounty amount in $USD format")
        
        # Check for accepted currencies
        if "Accepted currencies" not in content and "Currencies" not in content:
            warnings.append("Consider specifying accepted currencies")
        
        # Check for payout structure
        if "Payout structure" not in content and "Payment" not in content:
            warnings.append("Consider specifying payout structure")
        
        if errors:
            return False, errors, warnings
        
        return True, errors, warnings
    
    def _check_technical_depth(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check for technical depth and specificity."""
        errors = []
        warnings = []
        
        # Check for architecture diagrams
        if "```" not in content:
            warnings.append("Consider adding code/architecture diagrams")
        
        # Check for performance metrics
        if "Performance" not in content and "Metrics" not in content:
            warnings.append("Consider adding performance metrics table")
        
        # Check for integration requirements
        if "Integration" not in content:
            warnings.append("Consider adding integration requirements")
        
        # Check for component descriptions
        if "Core Components" not in content and "Components" not in content:
            warnings.append("Consider adding core components description")
        
        if errors:
            return False, errors, warnings
        
        return True, errors, warnings
    
    def _check_formatting(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check formatting quality."""
        errors = []
        warnings = []
        
        # Check for consistent heading levels
        lines = content.split('\n')
        heading_levels = []
        for line in lines:
            if line.startswith('#'):
                level = len(line.split()[0])
                heading_levels.append(level)
        
        # Check for heading hierarchy violations
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i-1] + 1:
                warnings.append(f"Heading hierarchy violation: jumping from H{heading_levels[i-1]} to H{heading_levels[i]}")
        
        # Check for markdown tables
        if "| " not in content:
            warnings.append("Consider adding markdown tables for structured data")
        
        # Check for proper list formatting
        if "- " not in content and "* " not in content:
            warnings.append("Consider using bullet points for lists")
        
        return True, errors, warnings
    
    def _check_recursive_fidelity(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check for recursive fidelity elements."""
        errors = []
        warnings = []
        
        # Check for recursive expansion section
        if "## 🎯 Recursive Expansion" not in content:
            errors.append("Missing Recursive Expansion section")
        
        # Check for sub-bounty references
        if "sub-bounties" not in content.lower():
            warnings.append("Consider mentioning sub-bounty opportunities")
        
        if errors:
            return False, errors, warnings
        
        return True, errors, warnings
    
    def _check_content_length(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check content length requirements."""
        errors = []
        warnings = []
        
        lines = content.split('\n')
        line_count = len(lines)
        
        # Minimum line count
        if line_count < 150:
            errors.append(f"Content too short: {line_count} lines (minimum 150)")
            return False, errors, warnings
        
        # Warning for very long files
        if line_count > 500:
            warnings.append(f"Content is quite long: {line_count} lines (consider splitting)")
        
        return True, errors, warnings
    
    def _check_timeline(self, content: str, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Check for timeline information."""
        errors = []
        warnings = []
        
        # Check for timeline section
        if "## ⏰ Timeline" not in content:
            errors.append("Missing Timeline section")
        
        # Check for dates
        if not self.DATE_PATTERN.search(content):
            warnings.append("Consider adding specific dates to timeline")
        
        if errors:
            return False, errors, warnings
        
        return True, errors, warnings


def print_validation_report(summary: ValidationSummary) -> None:
    """Print a formatted validation report."""
    print("\n" + "=" * 80)
    print("DAXDA BOUNTY VALIDATION REPORT")
    print("=" * 80)
    print(f"\nTotal Bounties Validated: {summary.total_bounties}")
    print(f"Valid Bounties: {summary.valid_bounties}")
    print(f"Invalid Bounties: {summary.invalid_bounties}")
    print(f"Average Score: {summary.average_score:.2%}")
    print(f"\nOverall Status: {'✅ PASS' if summary.invalid_bounties == 0 else '❌ FAIL'}")
    
    print("\n" + "-" * 80)
    print("INDIVIDUAL BOUNTY RESULTS")
    print("-" * 80)
    
    for result in summary.results:
        status = "✅ PASS" if result.is_valid else "❌ FAIL"
        print(f"\n{status} {result.file_path}")
        print(f"  Score: {result.score:.2%}")
        print(f"  Checks: {result.checks_passed}/{result.checks_total} passed")
        
        if result.errors:
            print(f"  Errors:")
            for error in result.errors:
                print(f"    - {error}")
        
        if result.warnings:
            print(f"  Warnings:")
            for warning in result.warnings:
                print(f"    - {warning}")
    
    print("\n" + "=" * 80)


def export_json_report(summary: ValidationSummary, output_path: str) -> None:
    """Export validation results as JSON."""
    export_data = {
        "summary": {
            "total_bounties": summary.total_bounties,
            "valid_bounties": summary.valid_bounties,
            "invalid_bounties": summary.invalid_bounties,
            "average_score": summary.average_score,
            "overall_status": "PASS" if summary.invalid_bounties == 0 else "FAIL"
        },
        "results": []
    }
    
    for result in summary.results:
        export_data["results"].append({
            "file_path": result.file_path,
            "is_valid": result.is_valid,
            "score": result.score,
            "checks_passed": result.checks_passed,
            "checks_total": result.checks_total,
            "errors": result.errors,
            "warnings": result.warnings
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\nJSON report exported to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate DAXDA bounty documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_bounties.py docs/
  python validate_bounties.py --output report.json
  python validate_bounties.py --strict
"""
    )
    
    parser.add_argument(
        "directory",
        nargs="?",
        default="docs",
        help="Directory containing bounty files (default: docs)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON report file path"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings as well as errors"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show summary, not individual results"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = BountyValidator(bounty_dir=args.directory)
    summary = validator.validate_all()
    
    # Print report
    if not args.quiet:
        print_validation_report(summary)
    else:
        print(f"Validation Complete: {summary.valid_bounties}/{summary.total_bounties} bounties passed")
    
    # Export JSON if requested
    if args.output:
        export_json_report(summary, args.output)
    
    # Return appropriate exit code
    if args.strict and (summary.invalid_bounties > 0 or any(r.warnings for r in summary.results)):
        return 1
    elif summary.invalid_bounties > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit(main())
