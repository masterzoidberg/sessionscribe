#!/usr/bin/env python3
"""
PHI Log Scanner for SessionScribe
Scans logs to ensure no PHI/transcript content is exposed, only metadata.
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set

# PHI patterns to detect
PHI_PATTERNS = [
    # Direct PHI indicators
    r'\b(?:transcript|transcription|speech|utterance|phrase|sentence)\b',
    r'\b(?:said|spoke|mentioned|stated|discussed)\b',
    r'\b(?:patient|client|therapist|doctor|nurse)\s+(?:said|spoke)',
    
    # Audio content indicators  
    r'\b(?:audio_data|pcm_data|wav_data|sound_data)\b',
    r'\b(?:recording|recorded|audio_content)\b',
    
    # Structured text that might be transcripts
    r'"text"\s*:\s*"[^"]{50,}"',  # Long text fields
    r'"content"\s*:\s*"[^"]{50,}"',
    r'"message"\s*:\s*"[^"]{50,}"',
    
    # Personal information
    r'\b(?:\d{3}[-.\s]?\d{2}[-.\s]?\d{4})\b',  # SSN-like
    r'\b(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',  # Phone-like
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
]

# Safe metadata patterns (these are OK)
SAFE_PATTERNS = [
    r'\b(?:session_id|trace_id|request_id)\b',
    r'\b(?:timestamp|duration|latency)\b',
    r'\b(?:chunk_count|frame_count|sample_rate)\b',
    r'\b(?:status|error|warning|info|debug)\b',
    r'\b(?:endpoint|method|service|port)\b',
    r'\b(?:buffer_size|channels|format)\b',
]

class PHIScanner:
    def __init__(self):
        self.phi_regex = re.compile('|'.join(PHI_PATTERNS), re.IGNORECASE)
        self.safe_regex = re.compile('|'.join(SAFE_PATTERNS), re.IGNORECASE)
        self.findings = []
    
    def scan_text(self, text: str, source: str) -> List[Dict]:
        """Scan text for potential PHI content."""
        findings = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check for PHI patterns
            phi_matches = self.phi_regex.findall(line)
            if phi_matches:
                # Check if this is actually safe metadata
                safe_matches = self.safe_regex.findall(line)
                
                # If we found PHI patterns but no safe patterns, flag it
                if len(phi_matches) > len(safe_matches):
                    findings.append({
                        'source': source,
                        'line': line_num,
                        'content': line.strip()[:200],  # Truncate for safety
                        'patterns': phi_matches,
                        'severity': 'HIGH'
                    })
        
        return findings
    
    def scan_json_logs(self, text: str, source: str) -> List[Dict]:
        """Scan JSON-structured logs for PHI content."""
        findings = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            try:
                log_entry = json.loads(line)
                
                # Check specific fields that should never contain PHI
                unsafe_fields = ['message', 'content', 'text', 'data', 'payload']
                
                for field in unsafe_fields:
                    if field in log_entry:
                        value = str(log_entry[field])
                        # Check for long text that might be transcripts
                        if len(value) > 100:
                            findings.append({
                                'source': source,
                                'line': line_num,
                                'content': f"Long {field}: {value[:100]}...",
                                'patterns': [f'long_{field}'],
                                'severity': 'MEDIUM'
                            })
                        
                        # Check for PHI patterns in field values
                        phi_matches = self.phi_regex.findall(value)
                        if phi_matches:
                            findings.append({
                                'source': source,
                                'line': line_num,
                                'content': f"{field}: {value[:100]}...",
                                'patterns': phi_matches,
                                'severity': 'HIGH'
                            })
                
            except json.JSONDecodeError:
                # Not JSON, treat as regular text
                findings.extend(self.scan_text(line, f"{source}:{line_num}"))
        
        return findings
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single log file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Determine if this looks like JSON logs
            if file_path.suffix == '.json' or any(line.strip().startswith('{') for line in content.split('\n')[:10]):
                return self.scan_json_logs(content, str(file_path))
            else:
                return self.scan_text(content, str(file_path))
        
        except Exception as e:
            return [{
                'source': str(file_path),
                'line': 0,
                'content': f"Error reading file: {e}",
                'patterns': ['scan_error'],
                'severity': 'ERROR'
            }]
    
    def scan_directory(self, dir_path: Path) -> List[Dict]:
        """Scan all log files in a directory."""
        findings = []
        
        # Common log file patterns
        log_patterns = ['*.log', '*.txt', '*.json', '*.out']
        
        for pattern in log_patterns:
            for log_file in dir_path.rglob(pattern):
                # Skip very large files (>10MB) for performance
                if log_file.stat().st_size > 10 * 1024 * 1024:
                    findings.append({
                        'source': str(log_file),
                        'line': 0,
                        'content': f"Skipped large file ({log_file.stat().st_size} bytes)",
                        'patterns': ['large_file'],
                        'severity': 'WARNING'
                    })
                    continue
                
                findings.extend(self.scan_file(log_file))
        
        return findings

def main():
    parser = argparse.ArgumentParser(description="Scan SessionScribe logs for PHI content")
    parser.add_argument("paths", nargs="+", help="Paths to log files or directories to scan")
    parser.add_argument("--output", "-o", help="Output file for findings")
    parser.add_argument("--format", choices=['json', 'text'], default='text', help="Output format")
    parser.add_argument("--severity", choices=['HIGH', 'MEDIUM', 'LOW'], default='MEDIUM', 
                       help="Minimum severity to report")
    
    args = parser.parse_args()
    
    scanner = PHIScanner()
    all_findings = []
    
    for path_str in args.paths:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: Path does not exist: {path}", file=sys.stderr)
            continue
        
        if path.is_file():
            findings = scanner.scan_file(path)
        elif path.is_dir():
            findings = scanner.scan_directory(path)
        else:
            print(f"ERROR: Invalid path: {path}", file=sys.stderr)
            continue
        
        all_findings.extend(findings)
    
    # Filter by severity
    severity_levels = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'WARNING': 1, 'ERROR': 3}
    min_severity = severity_levels.get(args.severity, 2)
    
    filtered_findings = [
        f for f in all_findings 
        if severity_levels.get(f['severity'], 1) >= min_severity
    ]
    
    # Output results
    if args.format == 'json':
        output = json.dumps(filtered_findings, indent=2)
    else:
        output_lines = []
        if not filtered_findings:
            output_lines.append("✓ PASS: No PHI content detected in logs")
        else:
            output_lines.append(f"✗ FAIL: Found {len(filtered_findings)} potential PHI exposures")
            output_lines.append("")
            
            for finding in filtered_findings:
                output_lines.append(f"[{finding['severity']}] {finding['source']}:{finding['line']}")
                output_lines.append(f"  Patterns: {', '.join(finding['patterns'])}")
                output_lines.append(f"  Content: {finding['content']}")
                output_lines.append("")
        
        output = '\n'.join(output_lines)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Results written to: {args.output}")
    else:
        print(output)
    
    # Exit code based on findings
    high_severity_count = len([f for f in filtered_findings if f['severity'] == 'HIGH'])
    if high_severity_count > 0:
        sys.exit(1)  # Fail on HIGH severity findings
    elif filtered_findings:
        sys.exit(2)  # Warning on other findings
    else:
        sys.exit(0)  # Success

if __name__ == "__main__":
    main()