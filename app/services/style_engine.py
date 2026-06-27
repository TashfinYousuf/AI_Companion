import random

def apply_human_style(text: str, language_mode: str, energy_level: int) -> str:
    """
    LLM-এর র-টেক্সটকে মানুষের মতো ন্যাচারাল করার Post-Processor.
    এখানে কোনো হার্ড-রুল নেই, পুরোটাই Probability (সম্ভাবনা) নির্ভর।
    """
    
    # 1. Probability Distribution for Slang/Breathing
    if language_mode == 'bn':
        styles = [
            ("আরেহ... ", 0.18),
            ("উফফ... ", 0.09),
            ("ধুর! ", 0.05),
            ("এই, ", 0.22),
            ("হুমম... ", 0.10),
            ("", 0.36) # 36% chance of no slang (to avoid repetition)
        ]
    else:
        styles = [
            ("Hmm... ", 0.15),
            ("Oh, ", 0.10),
            ("Well... ", 0.15),
            ("Hey, ", 0.10),
            ("", 0.50)
        ]
    
    words, weights = zip(*styles)
    chosen_prefix = random.choices(words, weights=weights, k=1)[0]
    
    # 2. Imperfection Engine (Rarely add a human stumble)
    imperfection = ""
    if random.random() < 0.05: # 5% chance to hesitate
        imperfection = "না মানে... " if language_mode == 'bn' else "I mean... "

    # 3. Dynamic Pauses (Breathing)
    # Energy কম থাকলে কথা বলার মাঝে পজ (...) বেশি নেবে
    if energy_level < 40 and random.random() < 0.4:
        text = text.replace(", ", "... ", 1)
        
    # Clean up any potential double punctuation caused by LLM
    raw_text = text.lstrip("।.,!?- ")
    
    return f"{chosen_prefix}{imperfection}{raw_text}"