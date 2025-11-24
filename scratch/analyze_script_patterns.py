#!/usr/bin/env python3
"""
Analyze actual scripts for threading anti-patterns and optimization opportunities
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
import sys

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'lib'))
from parallel import run_parallel

PROJECT_ROOT = Path(__file__).parent.parent


class ScriptAnalysis:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.content = filepath.read_text()
        self.lines = self.content.split('\n')
        self.issues = []
        self.good_patterns = []

    def analyze(self):
        """Run all analysis checks"""
        self.check_sequential_loops()
        self.check_subprocess_usage()
        self.check_parallel_usage()
        self.check_threading_patterns()
        self.check_file_iteration()

    def check_sequential_loops(self):
        """Find loops that could be parallelized"""
        # Pattern: for x in list: subprocess/open/request
        pattern = r'for\s+\w+\s+in\s+([^:]+):\s*\n\s+(subprocess|open|requests?\.)'

        for match in re.finditer(pattern, self.content, re.MULTILINE):
            line_num = self.content[:match.start()].count('\n') + 1
            self.issues.append({
                'type': 'sequential_loop',
                'severity': 'high',
                'line': line_num,
                'code': self.lines[line_num - 1].strip(),
                'recommendation': 'Use parallel.run_parallel() for I/O operations'
            })

    def check_subprocess_usage(self):
        """Check subprocess calls for best practices"""
        # Find all subprocess.run/call/Popen
        pattern = r'subprocess\.(run|call|Popen|check_output)\('

        for match in re.finditer(pattern, self.content):
            line_num = self.content[:match.start()].count('\n') + 1
            line = self.lines[line_num - 1]

            # Check for timeout
            if 'timeout=' not in line:
                self.issues.append({
                    'type': 'subprocess_no_timeout',
                    'severity': 'medium',
                    'line': line_num,
                    'code': line.strip(),
                    'recommendation': 'Add timeout parameter to prevent hangs'
                })

            # Check for shell=True
            if 'shell=True' in line:
                self.issues.append({
                    'type': 'subprocess_shell_true',
                    'severity': 'medium',
                    'line': line_num,
                    'code': line.strip(),
                    'recommendation': 'Use shell=False with list arguments for security'
                })

    def check_parallel_usage(self):
        """Check if script uses parallel library"""
        if 'from parallel import' in self.content or 'import parallel' in self.content:
            self.good_patterns.append({
                'type': 'uses_parallel_lib',
                'description': 'Uses parallel.py library'
            })

        if 'run_parallel' in self.content:
            # Check max_workers value
            pattern = r'run_parallel\([^)]*max_workers=(\d+)'
            matches = re.findall(pattern, self.content)
            for workers in matches:
                workers_int = int(workers)
                if workers_int < 20:
                    self.issues.append({
                        'type': 'low_max_workers',
                        'severity': 'low',
                        'line': 0,
                        'code': f'max_workers={workers}',
                        'recommendation': f'Consider increasing to 50+ for I/O-bound operations (currently {workers})'
                    })
                else:
                    self.good_patterns.append({
                        'type': 'optimal_workers',
                        'description': f'Uses max_workers={workers} (good for I/O)'
                    })

    def check_threading_patterns(self):
        """Check for threading anti-patterns"""
        # Raw threading.Thread usage
        if 'threading.Thread(' in self.content:
            self.issues.append({
                'type': 'raw_threading',
                'severity': 'medium',
                'line': 0,
                'code': 'threading.Thread',
                'recommendation': 'Use ThreadPoolExecutor instead of raw Thread objects'
            })

        # ThreadPoolExecutor (good!)
        if 'ThreadPoolExecutor' in self.content:
            self.good_patterns.append({
                'type': 'uses_threadpool',
                'description': 'Uses ThreadPoolExecutor for parallel execution'
            })

    def check_file_iteration(self):
        """Check for file iteration patterns"""
        # Pattern: for file in Path.glob / os.listdir
        pattern = r'for\s+\w+\s+in\s+(Path\([^)]+\)\.glob|os\.listdir|glob\.glob)'

        matches = list(re.finditer(pattern, self.content))
        if len(matches) > 0:
            # Check if body has I/O operations
            for match in matches:
                line_num = self.content[:match.start()].count('\n') + 1
                # Simple heuristic: if next 10 lines contain open/read/write
                next_lines = '\n'.join(self.lines[line_num:line_num + 10])
                if any(kw in next_lines for kw in ['open(', '.read(', '.write(', 'subprocess']):
                    self.issues.append({
                        'type': 'serial_file_iteration',
                        'severity': 'high',
                        'line': line_num,
                        'code': self.lines[line_num - 1].strip(),
                        'recommendation': 'Use parallel.run_parallel() for file processing'
                    })


def analyze_script(filepath: Path) -> ScriptAnalysis:
    """Analyze a single script"""
    analysis = ScriptAnalysis(filepath)
    analysis.analyze()
    return analysis


def generate_report(analyses: List[ScriptAnalysis]):
    """Generate comprehensive report"""

    print("="*80)
    print("SCRIPT-LEVEL THREADING ANALYSIS")
    print("="*80)

    # Collect statistics
    total_scripts = len(analyses)
    scripts_with_issues = sum(1 for a in analyses if a.issues)
    total_issues = sum(len(a.issues) for a in analyses)
    high_severity = sum(1 for a in analyses for i in a.issues if i['severity'] == 'high')
    medium_severity = sum(1 for a in analyses for i in a.issues if i['severity'] == 'medium')

    scripts_with_parallel = sum(1 for a in analyses if any(p['type'] == 'uses_parallel_lib' for p in a.good_patterns))

    print(f"\nScripts analyzed: {total_scripts}")
    print(f"Scripts with issues: {scripts_with_issues}")
    print(f"Total issues: {total_issues}")
    print(f"  High severity: {high_severity}")
    print(f"  Medium severity: {medium_severity}")
    print(f"\nScripts using parallel.py: {scripts_with_parallel}")

    # High severity issues
    print("\n" + "="*80)
    print("HIGH SEVERITY ISSUES (Immediate optimization opportunities)")
    print("="*80)

    for analysis in analyses:
        high_issues = [i for i in analysis.issues if i['severity'] == 'high']
        if high_issues:
            print(f"\n{analysis.filepath.relative_to(PROJECT_ROOT)}")
            for issue in high_issues:
                print(f"  Line {issue['line']}: {issue['type']}")
                print(f"    Code: {issue['code']}")
                print(f"    Fix: {issue['recommendation']}")

    # Good patterns
    print("\n" + "="*80)
    print("GOOD PATTERNS DETECTED")
    print("="*80)

    scripts_with_good = [a for a in analyses if a.good_patterns]
    for analysis in scripts_with_good:
        print(f"\n{analysis.filepath.relative_to(PROJECT_ROOT)}")
        for pattern in analysis.good_patterns:
            print(f"  ✓ {pattern['description']}")

    # Recommendations
    print("\n" + "="*80)
    print("ACTIONABLE RECOMMENDATIONS")
    print("="*80)

    recommendations = {
        'sequential_loop': [],
        'serial_file_iteration': [],
        'subprocess_no_timeout': [],
        'low_max_workers': []
    }

    for analysis in analyses:
        for issue in analysis.issues:
            if issue['type'] in recommendations:
                recommendations[issue['type']].append({
                    'file': analysis.filepath.relative_to(PROJECT_ROOT),
                    'line': issue['line']
                })

    print("\n1. CONVERT TO PARALLEL EXECUTION")
    print("   Files with sequential loops/file iteration:")
    for issue_type in ['sequential_loop', 'serial_file_iteration']:
        for item in recommendations[issue_type]:
            print(f"   - {item['file']}:{item['line']}")

    print("\n2. ADD TIMEOUT TO SUBPROCESS CALLS")
    print("   Files missing timeout:")
    for item in recommendations['subprocess_no_timeout']:
        print(f"   - {item['file']}:{item['line']}")

    print("\n3. INCREASE MAX_WORKERS")
    print("   Files with low max_workers:")
    for item in recommendations['low_max_workers']:
        print(f"   - {item['file']}:{item['line']}")


def main():
    # Find all Python scripts
    script_dirs = [
        PROJECT_ROOT / 'scripts' / 'ops',
        PROJECT_ROOT / 'scripts' / 'lib',
        PROJECT_ROOT / '.claude' / 'hooks'
    ]

    all_scripts = []
    for directory in script_dirs:
        if directory.exists():
            all_scripts.extend(directory.glob('*.py'))

    print(f"Analyzing {len(all_scripts)} scripts...")

    # Analyze in parallel (dogfooding!)
    results = run_parallel(
        analyze_script,
        all_scripts,
        max_workers=10,
        desc="Analyzing scripts"
    )

    # Extract analyses (run_parallel returns tuples: (item, result, error))
    analyses = [result for item, result, error in results if error is None and result is not None]

    # Generate report
    generate_report(analyses)

    # Save detailed results
    output_file = PROJECT_ROOT / 'scratch' / 'script_analysis_detailed.txt'
    with open(output_file, 'w') as f:
        f.write("DETAILED SCRIPT ANALYSIS\n")
        f.write("="*80 + "\n\n")

        for analysis in analyses:
            if analysis.issues or analysis.good_patterns:
                f.write(f"\n{analysis.filepath.relative_to(PROJECT_ROOT)}\n")
                f.write("-"*80 + "\n")

                if analysis.good_patterns:
                    f.write("\nGood patterns:\n")
                    for pattern in analysis.good_patterns:
                        f.write(f"  ✓ {pattern['description']}\n")

                if analysis.issues:
                    f.write("\nIssues:\n")
                    for issue in analysis.issues:
                        f.write(f"  [{issue['severity'].upper()}] Line {issue['line']}: {issue['type']}\n")
                        f.write(f"    Code: {issue['code']}\n")
                        f.write(f"    Fix: {issue['recommendation']}\n")

    print(f"\nDetailed report saved to: {output_file}")


if __name__ == '__main__':
    main()
