import os
import sys
import re
from datetime import datetime, timedelta, timezone
import argparse
from dotenv import load_dotenv
from transcript_analyzer import TranscriptAnalyzer

def main():
    """
    Find and analyze all call transcripts from a specific date directory
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze all transcripts for a specific date.')
    parser.add_argument('--date', type=str, help='Date directory to analyze (format: YYYY-MM-DD). Default is today in IST.')
    parser.add_argument('--transcripts-dir', type=str, default='transcripts', help='Base directory containing transcript folders')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Get Google API key from environment
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable not set")
        sys.exit(1)
    
    # Get current prompt from prompt.txt
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            current_prompt = f.read()
    except FileNotFoundError:
        current_prompt = "You are a helpful AI assistant."
        print("Warning: prompt.txt not found, using default prompt")
    
    # Define IST timezone (UTC+5:30)
    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    
    # Determine which date to process
    if args.date:
        target_date = args.date
    else:
        # Default to today's date in IST
        target_date = datetime.now(timezone.utc).astimezone(ist_timezone).strftime("%Y-%m-%d")
    
    print(f"Analyzing all transcripts for date: {target_date}")
    
    # Initialize the analyzer
    analyzer = TranscriptAnalyzer(google_api_key)
    
    # Find and analyze transcripts for the specified date
    analyzed_files = analyze_date_directory(
        analyzer, 
        args.transcripts_dir, 
        target_date, 
        current_prompt
    )
    
    print(f"Analysis completed. Processed {len(analyzed_files)} transcript(s).")
    for file in analyzed_files:
        print(f" - {file}")

def analyze_date_directory(analyzer, transcripts_dir, target_date, current_prompt):
    """Analyze all transcripts in a specific date directory."""
    analyzed_files = []
    
    # Check if transcripts directory exists
    if not os.path.exists(transcripts_dir):
        print(f"Error: Base transcripts directory '{transcripts_dir}' not found")
        return analyzed_files
    
    # Path to the specific date directory
    date_path = os.path.join(transcripts_dir, target_date)
    
    if not os.path.exists(date_path):
        print(f"Error: Date directory '{date_path}' not found")
        return analyzed_files
    
    print(f"Processing directory: {date_path}")
    
    # List transcript files in the date directory
    for filename in os.listdir(date_path):
        if not filename.endswith('.txt') or filename == '.gitkeep':
            continue
        
        filepath = os.path.join(date_path, filename)
        
        try:
            # Check if this file has already been analyzed
            json_path = os.path.join(date_path, "call_analysis.json")
            filename_without_ext = os.path.splitext(filename)[0]
            
            # If analysis exists, check if it already contains this file
            already_analyzed = False
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r') as f:
                    try:
                        analysis_data = json.load(f)
                        if filename_without_ext in analysis_data:
                            already_analyzed = True
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse JSON in {json_path}")
            
            # Skip if already analyzed
            if already_analyzed:
                print(f"Skipping already analyzed file: {filepath}")
                continue
            
            print(f"Analyzing transcript: {filepath}")
            analyzer.analyze_transcript(filepath, current_prompt)
            analyzed_files.append(filepath)
        except Exception as e:
            print(f"Error analyzing {filepath}: {str(e)}")
    
    return analyzed_files

if __name__ == "__main__":
    main()