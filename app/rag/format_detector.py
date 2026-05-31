import re
from typing import List, Dict



# Simple Format Detection
def detect_format(transcript: str) -> str:
    """
    Detect what format the transcript uses
    
    Returns:
        'timestamp_bracket' - [00:00] Alice: text
        'timestamp_inline'  - Alice 00:00 text
        'speaker_label'     - SPEAKER_01: text
        'speaker_letter'    - Speaker A: text
        'plain_text'        - Unknown format
    """
    if not transcript:
        return 'plain_text'
    
    # Check each format (order matters - specific first)
    
    if re.search(r'\[[\d:]+\]\s+\w+:', transcript):  # Otter.ai, Zoom, Google Meet AI notes
        return 'timestamp_bracket'
    
    if re.search(r'[A-Za-z\s]+\s+\d{2}:\d{2}\s+\w+', transcript):  # Fireflies.ai, MeetGeek
        return 'timestamp_inline'
    
    if re.search(r'SPEAKER_\d+:', transcript):  # Whisper, AssemblyAI, Deepgram
        return 'speaker_label'
    
    if re.search(r'Speaker\s+[A-Z]:', transcript):  # Basic diarization, some APIs
        return 'speaker_letter'
    
    return 'plain_text'  # Raw text, meeting notes, fallback



def parse_transcript_turns(transcript: str) -> List[Dict]:
    """
    Parse transcript into list of speaker turns
    
    Returns list of dicts like:
    [
        {'speaker': 'Alice', 'text': 'Hello', 'timestamp': '00:05'},
        {'speaker': 'Bob', 'text': 'Hi there', 'timestamp': '00:08'}
    ]
    """
    format_type = detect_format(transcript)
    
    # Route to appropriate parser
    if format_type == 'timestamp_bracket':
        return parse_bracket_format(transcript)
    
    if format_type == 'timestamp_inline':
        return parse_inline_format(transcript)
    
    if format_type == 'speaker_label':
        return parse_speaker_label_format(transcript)
    
    if format_type == 'speaker_letter':
        return parse_speaker_letter_format(transcript)
    
    # Fallback
    return parse_plain_format(transcript)



# Individual Parsers (one per format)
def parse_bracket_format(transcript: str) -> List[Dict]:
    """
    Parse: [00:00:05] Alice: Hello world
    
    Example input: "[00:00] Alice: Hi\n[00:05] Bob: Hello"
    Output: [
        {'timestamp': '00:00', 'speaker': 'Alice', 'text': 'Hi'},
        {'timestamp': '00:05', 'speaker': 'Bob', 'text': 'Hello'}
    ]
    """
    # Pattern: [timestamp] speaker: text
    pattern = r'\[([\d:]+)\]\s+(\w+):\s*(.*?)(?=\n?\[[\d:]+\]|\Z)'
    
    turns = []
    for match in re.finditer(pattern, transcript, re.DOTALL):
        timestamp = match.group(1)   # "00:00"
        speaker = match.group(2)  # "Alice"
        text = match.group(3).strip()  # "Hi"
        
        turns.append({
            'timestamp': timestamp,
            'speaker': speaker,
            'text': text
        })
    
    return turns


def parse_inline_format(transcript: str) -> List[Dict]:
    """
    Parse: Alice 00:05 Hello world
    
    Example input: "Alice 00:05 Hi Bob 00:08 Hello Alice"
    Output: [
        {'speaker': 'Alice', 'timestamp': '00:05', 'text': 'Hi'},
        {'speaker': 'Bob', 'timestamp': '00:08', 'text': 'Hello Alice'}
    ]
    """
    # Pattern: Name timestamp text (until next Name timestamp)
    pattern = r'([A-Za-z\s]+)\s+(\d{2}:\d{2})\s+(.*?)(?=\s+[A-Za-z\s]+\s+\d{2}:\d{2}|\Z)'
    
    turns = []
    for match in re.finditer(pattern, transcript):
        speaker = match.group(1).strip()  # "Alice"
        timestamp = match.group(2) # "00:05"
        text = match.group(3).strip() # "Hi"
        
        turns.append({
            'speaker': speaker,
            'timestamp': timestamp,
            'text': text
        })
    
    return turns


def parse_speaker_label_format(transcript: str) -> List[Dict]:
    """
    Parse: SPEAKER_01: Hello world
    
    Example input: "SPEAKER_01: Hi\nSPEAKER_02: Hello"
    Output: [
        {'speaker': 'SPEAKER_01', 'text': 'Hi'},
        {'speaker': 'SPEAKER_02', 'text': 'Hello'}
    ]
    """
    pattern = r'(SPEAKER_\d+):\s*(.*?)(?=\nSPEAKER_\d+:|$)'
    
    turns = []
    for match in re.finditer(pattern, transcript, re.DOTALL):
        speaker = match.group(1)  # "SPEAKER_01"
        text = match.group(2).strip()  # "Hi"
        
        turns.append({
            'speaker': speaker,
            'text': text
        })
    
    return turns


def parse_speaker_letter_format(transcript: str) -> List[Dict]:
    """
    Parse: Speaker A: Hello world
    
    Example input: "Speaker A: Hi\nSpeaker B: Hello"
    Output: [
        {'speaker': 'Speaker A', 'text': 'Hi'},
        {'speaker': 'Speaker B', 'text': 'Hello'}
    ]
    """
    pattern = r'(Speaker\s+[A-Z]):\s*(.*?)(?=\nSpeaker\s+[A-Z]:|$)'
    
    turns = []
    for match in re.finditer(pattern, transcript, re.DOTALL):
        speaker = match.group(1)  # "Speaker A"
        text = match.group(2).strip()  # "Hi"
        
        turns.append({
            'speaker': speaker,
            'text': text
        })
    
    return turns


def parse_plain_format(transcript: str) -> List[Dict]:
    """
    Fallback: No clear format, treat as single speaker or split by lines
    
    Example: Plain text with no speaker labels
    Output: [{'speaker': 'Unknown', 'text': 'entire transcript'}]
    """
    # Try to detect if it has "Name:" pattern
    if re.search(r'[A-Z][a-z]+:', transcript):
        # Simple "Name: text" pattern
        pattern = r'([A-Z][a-z]+):\s*(.*?)(?=\n[A-Z][a-z]+:|$)'
        turns = []
        for match in re.finditer(pattern, transcript, re.DOTALL):
            speaker = match.group(1)
            text = match.group(2).strip()
            turns.append({
                'speaker': speaker,
                'text': text
            })
        if turns:
            return turns
    
    # Otherwise treat everything as one speaker
    return [{
        'speaker': 'Unknown',
        'text': transcript.strip()
    }]


# TODO Extention logic for custom user format by API endpoint
# Helper to add new formats (extensible)

# Registry for custom formats
# _custom_parsers = {}

# def register_format(name: str, pattern: str, parser_function):
#     """
#     Add your own transcript format
    
#     Example:
#         def my_parser(text):
#             # Custom parsing logic
#             return [{'speaker': 'X', 'text': 'Y'}]
        
#         register_format('my_app', r'CustomPattern', my_parser)
#     """
#     _custom_parsers[name] = {
#         'pattern': pattern,
#         'parser': parser_function
#     }


# def detect_format_extended(transcript: str) -> str:
#     """Extended detection that includes custom formats"""
#     # Check custom formats first
#     for name, config in _custom_parsers.items():
#         if re.search(config['pattern'], transcript):
#             return name
    
#     # Fall back to built-in detection
#     return detect_format(transcript)


# def parse_transcript_turns_extended(transcript: str) -> List[Dict]:
#     """Extended parsing that includes custom formats"""
#     format_type = detect_format_extended(transcript)
    
#     # Check custom parsers
#     if format_type in _custom_parsers:
#         return _custom_parsers[format_type]['parser'](transcript)
    
#     # Fall back to built-in
#     return parse_transcript_turns(transcript)