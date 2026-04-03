#!/usr/bin/env python3
"""
Quick Summary Script - Shows who talks more in the podcast
"""

from transcript_analyzer import (
    TranscriptAnalyzer,
    find_transcript_files,
    print_transcript_setup_help,
)


def quick_summary():
    """Generate a quick summary of who talks more"""
    analyzer = TranscriptAnalyzer()
    
    # Find all .docx files
    file_paths = find_transcript_files()
    
    if not file_paths:
        print_transcript_setup_help()
        return
    
    print("🎙️  MARK & SCOTT TALK TOO MUCH - ANALYSIS SUMMARY")
    print("=" * 60)
    
    # Quick analysis
    total_words = {'Mark': 0, 'Scott': 0}
    total_time = {'Mark': 0, 'Scott': 0}
    episodes_analyzed = 0
    scott_wins_words = 0
    mark_wins_words = 0
    
    for file_path in file_paths:
        if file_path.exists():
            result = analyzer.analyze_transcript(file_path)
            if result:
                episodes_analyzed += 1
                total_words['Mark'] += result['word_counts']['Mark']
                total_words['Scott'] += result['word_counts']['Scott']
                total_time['Mark'] += result['speaking_time_seconds']['Mark']
                total_time['Scott'] += result['speaking_time_seconds']['Scott']
                
                if result['word_counts']['Scott'] > result['word_counts']['Mark']:
                    scott_wins_words += 1
                else:
                    mark_wins_words += 1
    
    if episodes_analyzed == 0:
        print("No episodes could be analyzed.")
        return
    
    print(f"📊 Episodes analyzed: {episodes_analyzed}")
    print()
    
    # Calculate percentages
    total_all_words = sum(total_words.values())
    total_all_time = sum(total_time.values())
    
    mark_word_pct = (total_words['Mark'] / total_all_words * 100) if total_all_words > 0 else 0
    scott_word_pct = (total_words['Scott'] / total_all_words * 100) if total_all_words > 0 else 0
    
    mark_time_pct = (total_time['Mark'] / total_all_time * 100) if total_all_time > 0 else 0
    scott_time_pct = (total_time['Scott'] / total_all_time * 100) if total_all_time > 0 else 0
    
    print("🗣️  SPEAKING STATS:")
    print(f"   Mark:  {total_words['Mark']:6,} words ({mark_word_pct:4.1f}%) | {analyzer.format_time(total_time['Mark'])} ({mark_time_pct:4.1f}%)")
    print(f"   Scott: {total_words['Scott']:6,} words ({scott_word_pct:4.1f}%) | {analyzer.format_time(total_time['Scott'])} ({scott_time_pct:4.1f}%)")
    print()
    
    # Who talks more overall?
    word_winner = 'Scott' if total_words['Scott'] > total_words['Mark'] else 'Mark'
    word_diff = abs(total_words['Scott'] - total_words['Mark'])
    time_winner = 'Scott' if total_time['Scott'] > total_time['Mark'] else 'Mark'
    time_diff = abs(total_time['Scott'] - total_time['Mark'])
    
    print("🏆 OVERALL WINNER:")
    print(f"   By words: {word_winner} (+{word_diff:,} words)")
    print(f"   By time:  {time_winner} (+{analyzer.format_time(time_diff)})")
    print()
    
    print("📈 EPISODE WINS:")
    print(f"   Scott wins: {scott_wins_words}/{episodes_analyzed} episodes ({scott_wins_words/episodes_analyzed*100:.1f}%)")
    print(f"   Mark wins:  {mark_wins_words}/{episodes_analyzed} episodes ({mark_wins_words/episodes_analyzed*100:.1f}%)")
    print()
    
    if scott_word_pct > mark_word_pct:
        diff_pct = scott_word_pct - mark_word_pct
        print(f"💬 CONCLUSION: Scott talks {diff_pct:.1f}% more than Mark overall!")
    else:
        diff_pct = mark_word_pct - scott_word_pct
        print(f"💬 CONCLUSION: Mark talks {diff_pct:.1f}% more than Scott overall!")
    
    print()
    print("📄 For detailed analysis, run: python3 transcript_analyzer.py")
    print("📋 For CSV export, run: python3 generate_csv_report.py")


if __name__ == '__main__':
    quick_summary()
