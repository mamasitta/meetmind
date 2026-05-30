from typing import List, Dict
from app.rag.format_detector import parse_transcript_turns

# Settings 
CHUNK_SIZE = 1000      # Each chunk max characters
CHUNK_OVERLAP = 200    # Overlap between chunks (preserves context)


def chunk_transcript(transcript: str) -> List[str]:
    """
    Main function - split transcript into chunks
    
    Example:
        Input: "Alice: Hi\nBob: Hello" (500 chars)
        Output: ["Alice: Hi\nBob: Hello"] (if under 1000 chars)
        
        Input: "Bob: [2000 chars of talking]"
        Output: ["Bob: [first 1000 chars]", "Bob: [last 1000 chars with overlap]"]
        
        Input: "" (empty)
        Output: []  # ← Must return empty list!
    """
    # Handle empty or whitespace-only transcripts FIRST
    if not transcript or not transcript.strip():
        return []
    
    turns = parse_transcript_turns(transcript)
    
    # If still no turns after parsing, return empty list
    if not turns:
        return []
    
    # Check if we have timestamps
    has_timestamps = any('timestamp' in turn for turn in turns)
    
    # Build smart chunks
    return build_smart_chunks(turns, has_timestamps)

def build_smart_chunks(turns: List[Dict], include_timestamp: bool = True) -> List[str]:
    """
    Build chunks while keeping speakers together
    
    CRITICAL: Never splits in the middle of a speaker's turn!
    
    Example turn: {'speaker': 'Alice', 'text': 'Hello', 'timestamp': '00:05'}
    Becomes: "[00:05] Alice: Hello"
    """
    chunks = []
    current_chunk = []      # List of COMPLETE turns in current chunk
    current_size = 0        # Total characters in current chunk
    
    for turn in turns:
        # Format the turn as readable text (preserves speaker identity)
        if include_timestamp and 'timestamp' in turn:
            turn_text = f"[{turn['timestamp']}] {turn['speaker']}: {turn['text']}"
        else:
            turn_text = f"{turn['speaker']}: {turn['text']}"
        
        turn_size = len(turn_text)
        
        # CASE 1: Single speaker turn is TOO LONG (rare, but handle it)
        if turn_size > CHUNK_SIZE:
            # Save current chunk first (it contains complete turns)
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split the long turn by SENTENCES (not by character count!)
            # This way we preserve meaning within the same speaker
            sub_chunks = split_long_turn_by_sentences(turn_text, turn['speaker'])
            chunks.extend(sub_chunks)
            continue
        
        # CASE 2: Adding this turn would exceed chunk size
        if current_size + turn_size > CHUNK_SIZE:
            # Save current chunk (contains complete turns from multiple speakers)
            chunks.append("\n".join(current_chunk))
            
            # Create overlap from previous chunk's LAST COMPLETE SENTENCE
            overlap = get_smart_overlap(current_chunk, CHUNK_OVERLAP)
            
            # Start new chunk with overlap + current turn
            if overlap:
                current_chunk = [overlap, turn_text]
                current_size = len(overlap) + turn_size
            else:
                current_chunk = [turn_text]
                current_size = turn_size
        else:
            # CASE 3: Normal case - add COMPLETE speaker turn to current chunk
            current_chunk.append(turn_text)
            current_size += turn_size
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks if chunks else []


def split_long_turn_by_sentences(turn_text: str, speaker: str) -> List[str]:
    """
    Split a very long speaker turn by SENTENCE boundaries, not character count
    
    This preserves meaning within the same speaker's monologue.
    
    Example: Bob talks for 2500 chars about quarterly results
    Returns: 
        Chunk 1: "Bob: Q3 revenue was up 20%. Costs decreased by 5%."
        Chunk 2: "Bob: Net profit increased to $1.2M. We expect Q4 to be even better."
    
    Notice: Each chunk starts with "Bob:" so we know who's talking!
    """
    import re
    
    # Extract prefix (speaker name + optional timestamp)
    prefix_match = re.match(r'(\[[\d:]+\]\s+\w+:|[\w\s]+:\s*)', turn_text)
    prefix = prefix_match.group(1) if prefix_match else f"{speaker}: "
    
    # Get just the spoken text (without the prefix)
    content = turn_text[len(prefix):]
    
    # Split into sentences by . ! ? (preserves grammatical units)
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    chunks = []
    current = prefix
    
    for sentence in sentences:
        # If adding this complete sentence fits, add it
        if len(current) + len(sentence) <= CHUNK_SIZE:
            current += sentence + " "
        else:
            # Save current chunk (contains complete sentences)
            if current.strip():
                chunks.append(current.strip())
            
            # Start new chunk with overlap from last sentence
            # This ensures continuity of thought
            overlap = get_sentence_overlap(current, CHUNK_OVERLAP)
            current = prefix + overlap + sentence + " "
    
    # Add last chunk
    if current.strip():
        chunks.append(current.strip())
    
    return chunks


def get_smart_overlap(chunk: List[str], overlap_chars: int) -> str:
    """
    Get overlap that preserves COMPLETE SPEAKER TURNS or SENTENCES
    
    Example: Previous chunk ends with:
        "Alice: We need to cut costs.\nBob: I agree, by 20%."
    
    Returns (if within 200 chars): "Bob: I agree, by 20%."
    
    This way the new chunk starts with a complete thought!
    """
    # Join all turns in chunk
    full_chunk = "\n".join(chunk)
    
    # If chunk is smaller than overlap, return whole thing
    if len(full_chunk) <= overlap_chars:
        return full_chunk
    
    # Try to find last COMPLETE speaker turn
    turns_in_chunk = full_chunk.split("\n")
    
    overlap_parts = []
    current_size = 0
    
    # Start from the end and collect complete turns
    for turn in reversed(turns_in_chunk):
        turn_with_newline = turn + "\n"
        if current_size + len(turn_with_newline) <= overlap_chars:
            overlap_parts.insert(0, turn)
            current_size += len(turn_with_newline)
        else:
            # If we can't fit a full turn, try to get last sentence
            if not overlap_parts:
                return get_last_sentence(turn, overlap_chars)
            break
    
    return "\n".join(overlap_parts)


def get_last_sentence(text: str, max_chars: int) -> str:
    """
    Extract last complete sentence from text for overlap
    """
    import re
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Start from end and build overlap
    overlap = ""
    for sentence in reversed(sentences):
        if len(sentence) + len(overlap) <= max_chars:
            overlap = sentence + (" " if overlap else "") + overlap
        else:
            break
    
    return overlap.strip()


def get_sentence_overlap(text: str, max_chars: int) -> str:
    """
    Get last complete sentence(s) from text for overlap
    
    Example: text ends with "... the project deadline is Friday. We should focus on Q3."
    Returns: "We should focus on Q3."
    """
    import re
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    overlap = ""
    for sentence in reversed(sentences):
        if len(sentence) + len(overlap) <= max_chars:
            overlap = sentence + (" " if overlap else "") + overlap
        else:
            break
    
    return overlap.strip()


def get_overlap(chunk: List[str], overlap_chars: int) -> str:
    """
    Original simple overlap function (fallback)
    """
    full_chunk = "\n".join(chunk)
    
    if len(full_chunk) <= overlap_chars:
        return full_chunk
    
    overlap = full_chunk[-overlap_chars:]
    
    # Try to start at a sentence or line break
    for boundary in ['\n', '. ', '? ', '! ']:
        last_boundary = overlap.rfind(boundary)
        if last_boundary > overlap_chars // 2:
            overlap = overlap[last_boundary + len(boundary):]
            break
    
    return overlap.strip()