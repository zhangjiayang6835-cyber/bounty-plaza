2. Code Patch / Fix

**File:** `dwarf_trace/co_linetable_codec.py`

```python
# ... existing imports ...

def encode_linetable(code_obj, exception_handlers=None):
    """
    Encode the line table for a code object, ensuring strict PEP 626/657 compliance.
    
    Args:
        code_obj: The code object to encode.
        exception_handlers: Optional list of exception handler ranges for alignment.
    
    Returns:
        bytes: The encoded line table.
    """
    # Initialize state
    last_instr = 0
    last_line = code_obj.co_firstlineno
    last_col = 0  # PEP 626: Column offsets are relative to the start of the line
    
    # Get the line table from the code object
    line_table = code_obj.co_linetable
    if not line_table:
        return b''
    
    # If exception handlers are provided, we must ensure alignment
    # This is a critical invariant for PEP 657 compliance
    if exception_handlers:
        # Sort handlers by start offset to process in order
        sorted_handlers = sorted(exception_handlers, key=lambda h: h.start)
        handler_idx = 0
        next_handler_start = sorted_handlers[0].start if sorted_handlers else float('inf')
    
    encoded = bytearray()
    
    for entry in line_table:
        instr_offset = entry.instr_offset
        line = entry.line
        col = entry.column
        
        # Calculate deltas
        instr_delta = instr_offset - last_instr
        line_delta = line - last_line
        col_delta = col - last_col
        
        # PEP 626 Invariant: If line changes, column resets to 0
        # But we must preserve the exact delta for the current line's start
        if line_delta != 0: