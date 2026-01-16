import random
import re
from collections import Counter
from django.conf import settings

# ----------------- Static Data (Source of Truth) -----------------

# Copied from views.py
EMOTION_IMAGES = [
    {"id": 1, "file": "detection_app/emotions/happy1.jpg", "emotion": "Happy"},
    {"id": 2, "file": "detection_app/emotions/sad1.jpg", "emotion": "Sad"},
    {"id": 3, "file": "detection_app/emotions/angry1.jpg", "emotion": "Angry"},
    {"id": 4, "file": "detection_app/emotions/surprised1.jpg", "emotion": "Surprised"},
    {"id": 5, "file": "detection_app/emotions/fear1.jpg", "emotion": "Fear"},
]

EMOTION_LABELS = ["Happy", "Sad", "Angry", "Surprised", "Fear"]

WORD_MEMORY_LIST = [
    "mango",
    "train",
    "temple",
    "window",
    "river",
    "doctor",
    "flower",
    "bucket",
    "market",
    "chair",
]

# ----------------- Emotion Memory Test -----------------

def get_emotion_config():
    """
    Returns the configuration for the emotion test.
    Shuffles images and returns IDs and URLs.
    Does NOT return the correct emotion (server-side truth).
    """
    # Create a copy and shuffle
    images = [img.copy() for img in EMOTION_IMAGES]
    random.shuffle(images)
    
    # Transform for client consumption (hide answer)
    client_images = []
    for img in images:
        # Build absolute URL if needed, or relative path
        # Assuming static or media handling. The view sends 'file' which is a static path.
        # We'll just send the file path string for now, or build a full URL if request context is available.
        # Keeping it simple as strings.
        client_images.append({
            "id": img["id"],
            "url": f"/static/{img['file']}" # Approximating static URL construction
        })
        
    return {
        "images": client_images,
        "labels": EMOTION_LABELS
    }

def score_emotion_test(answers):
    """
    answers: list of dicts { "image_id": int, "selected_label": str }
    """
    # Create map of id -> correct_emotion
    truth_map = {img["id"]: img["emotion"] for img in EMOTION_IMAGES}
    
    correct_count = 0
    total = len(answers)
    results = []
    
    for ans in answers:
        img_id = ans.get("image_id")
        user_val = (ans.get("selected_label") or "").strip().lower()
        
        correct_val = truth_map.get(img_id)
        if not correct_val:
            # Invalid ID, skip or mark wrong
            results.append({"image_id": img_id, "correct": False, "error": "Invalid ID"})
            continue
            
        is_correct = (user_val == correct_val.lower())
        if is_correct:
            correct_count += 1
            
        results.append({
            "image_id": img_id,
            "correct": is_correct,
            "correct_label": correct_val # Giving back truth is okay primarily for review/feedback
        })
        
    score_percent = round((correct_count / len(EMOTION_IMAGES)) * 100, 1) if len(EMOTION_IMAGES) > 0 else 0.0
    
    return {
        "total_questions": len(EMOTION_IMAGES),
        "answered_count": total,
        "correct_count": correct_count,
        "score_percent": score_percent,
        "results": results
    }

# ----------------- Word Memory Test -----------------

def get_word_config():
    return {
        "words": WORD_MEMORY_LIST
    }

def score_word_test(recalled_text):
    """
    Logic copied from word_memory_recall view.
    """
    target_set = {w.strip().lower() for w in WORD_MEMORY_LIST}
    
    if recalled_text:
        tmp = recalled_text.replace("\n", ",")
        pieces = [p.strip() for p in tmp.split(",") if p.strip()]
    else:
        pieces = []

    recalled_clean = []
    for p in pieces:
        for tok in p.split():
            tok = tok.strip().lower()
            if tok:
                recalled_clean.append(tok)

    # deduplicate while preserving order
    seen = set()
    recalled_unique = []
    for w in recalled_clean:
        if w not in seen:
            seen.add(w)
            recalled_unique.append(w)

    correct_hits = [w for w in recalled_unique if w in target_set]
    incorrect_hits = [w for w in recalled_unique if w not in target_set]

    total_target = len(target_set)
    correct_count = len(correct_hits)
    score_percent = round((correct_count / total_target) * 100, 1) if total_target > 0 else 0.0

    # Normalize to 0–10 MemoryScore
    memory_score = round((score_percent / 100) * 10.0, 1)
    
    # Interpretation
    if score_percent >= 70:
        level = "Good Memory"
        interpretation = (
            "The patient recalled most of the words, suggesting preserved immediate verbal memory. "
            "This is generally reassuring, especially when combined with other normal test results."
        )
    elif score_percent >= 40:
        level = "Borderline Memory"
        interpretation = (
            "The patient recalled some of the words but missed several. This may indicate mild memory "
            "weakness or inattention and should be monitored over time."
        )
    else:
        level = "Low Memory (High-Risk)"
        interpretation = (
            "The patient recalled few or none of the words. This can be a marker of verbal memory "
            "impairment and warrants a more detailed cognitive assessment by a specialist."
        )

    return {
        "correct_hits": correct_hits,
        "incorrect_hits": incorrect_hits,
        "score_percent": score_percent,
        "memory_score": memory_score,
        "level": level,
        "interpretation": interpretation
    }

# ----------------- Category Fluency Test -----------------

def score_fluency(raw_text, category="fruits"):
    """
    Logic copied from category_fluency view.
    """
    if raw_text:
        tmp = raw_text.replace("\n", ",")
        pieces = [p.strip().lower() for p in tmp.split(",") if p.strip()]
    else:
        pieces = []

    # Split any multi-word chunks too:
    words_flat = []
    for p in pieces:
        for tok in p.split():
            tok = tok.strip().lower()
            if tok:
                words_flat.append(tok)

    # Deduplicate
    unique_words = []
    seen = set()
    for w in words_flat:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)

    unique_count = len(unique_words)

    # Normalize: e.g. 0–15 items -> 0–10 score (cap)
    max_items = 15
    fluency_score = round(min(unique_count, max_items) / max_items * 10.0, 1)
    
    if fluency_score >= 7.0:
        level = "Good Semantic Fluency"
        interpretation = (
            "The patient produced an adequate number of items in the given category, suggesting preserved "
            "semantic memory and word retrieval."
        )
    elif fluency_score >= 4.0:
        level = "Borderline Semantic Fluency"
        interpretation = (
            "The patient produced some items but fewer than expected. This may indicate mild semantic or "
            "executive difficulties and should be monitored over time."
        )
    else:
        level = "Low Semantic Fluency (High-Risk)"
        interpretation = (
            "The patient produced very few distinct items. This can be an early marker of semantic memory "
            "impairment and warrants further cognitive evaluation."
        )

    return {
        "unique_words": unique_words,
        "unique_count": unique_count,
        "fluency_score": fluency_score,
        "level": level,
        "interpretation": interpretation
    }

# ----------------- Speech Coherence Test -----------------

def score_speech_coherence(text):
    """
    Logic copied from speech_coherence_test view.
    """
    if not text:
        return {
            "error": "No text provided",
            "total_score": 0.0
        }

    lower = text.lower()

    # 1) EXPECTED MORNING STEPS (India context)
    steps = [
        ("wake", "woke", "get up", "got up", "waking"),
        ("brush", "teeth", "toothbrush", "toothpaste", "mouthwash"),
        ("bath", "bathe", "bathing", "shower", "wash", "freshen up"),
        ("breakfast", "tea", "coffee", "milk", "eat", "eating"),
        ("work", "office", "school", "college", "study", "classes"),
    ]

    step_hits = []
    step_positions = []

    for synonyms in steps:
        found = False
        pos_min = None
        for kw in synonyms:
            p = lower.find(kw)
            if p != -1:
                found = True
                pos_min = p if pos_min is None else min(pos_min, p)
        step_hits.append(found)
        step_positions.append(pos_min)

    steps_covered = sum(step_hits)

    # ---- Step Coverage Score (0–6) ----
    if len(steps) > 0:
        step_coverage_score = (steps_covered / len(steps)) * 6.0
    else:
        step_coverage_score = 0.0

    # ---- Order Score (0–2) ----
    mentioned_positions = [p for p in step_positions if p is not None]

    inversions = 0
    for i in range(len(mentioned_positions)):
        for j in range(i + 1, len(mentioned_positions)):
            if mentioned_positions[i] > mentioned_positions[j]:
                inversions += 1

    if len(mentioned_positions) <= 1:
        order_score = 1.0  # neutral
    elif inversions == 0:
        order_score = 2.0  # perfect
    elif inversions <= 2:
        order_score = 1.0  # mild
    else:
        order_score = 0.0  # disordered

    # ---- Repetition Score (0–1) ----
    words = re.findall(r"\b\w+\b", lower)
    stopwords = {
        "the", "and", "to", "a", "i", "of", "in", "on", "for", "is", "it", "was", "then",
        "so", "that", "this", "at", "my", "me", "we", "you", "they"
    }
    filtered_words = [w for w in words if w not in stopwords]
    counts = Counter(filtered_words)
    repeated_tokens = [w for w, c in counts.items() if c >= 3]

    if len(repeated_tokens) == 0:
        repetition_score = 1.0
    elif len(repeated_tokens) == 1:
        repetition_score = 0.5
    else:
        repetition_score = 0.0

    # ---- Fragmentation Score (0–1) ----
    raw_sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    if not sentences:
        fragmentation_score = 0.0
    else:
        short_sentences = [s for s in sentences if len(s.split()) <= 3]
        ratio = len(short_sentences) / len(sentences)

        if ratio <= 0.25:
            fragmentation_score = 1.0
        elif ratio <= 0.5:
            fragmentation_score = 0.5
        else:
            fragmentation_score = 0.0

    # ---- Final Score (0–10) ----
    total_score = step_coverage_score + order_score + repetition_score + fragmentation_score
    total_score = round(total_score, 1)

    if total_score >= 8:
        level = "Good Coherence"
        interpretation = (
            "The description is well-structured with good coverage of morning activities, "
            "mostly correct order, and minimal repetition. This suggests preserved speech "
            "coherence and planning ability."
        )
    elif total_score >= 5:
        level = "Borderline Coherence"
        interpretation = (
            "The description shows some gaps, mild disorganization, or repetition. "
            "This may indicate early changes in planning or narrative ability and "
            "should be monitored over time."
        )
    else:
        level = "Low Coherence (High-Risk)"
        interpretation = (
            "The description is poorly organized, with missing key steps, disordered sequence, "
            "or heavy repetition. This may be a marker of cognitive decline and warrants "
            "detailed assessment by a specialist."
        )

    return {
        "total_score": total_score,
        "level": level,
        "interpretation": interpretation,
        "breakdown": {
            "step_coverage": step_coverage_score,
            "order_score": order_score,
            "repetition_score": repetition_score,
            "fragmentation_score": fragmentation_score
        }
    }

# ----------------- AERI Summary -----------------

def get_aeri_summary(speech_score, memory_score, fluency_score):
    """
    Combines 3 scores into 0-100 index.
    """
    # Each component is 0–10; weight 3,4,3 to get 0–100
    aeri = round(
        (float(speech_score) * 3.0) +
        (float(memory_score) * 4.0) +
        (float(fluency_score) * 3.0),
        1
    )

    if aeri >= 80:
        level = "Low Alzheimer’s Risk (based on screening tests)"
        interpretation = (
            "Across speech coherence, memory recall, and category fluency, performance falls within the "
            "expected range. This is reassuring, especially if there are no concerning symptoms in daily life."
        )
    elif aeri >= 50:
        level = "Mild Cognitive Concern"
        interpretation = (
            "Some of the screening scores are borderline. This does not confirm dementia, but suggests that "
            "cognitive status should be monitored with repeat testing and clinical follow-up."
        )
    else:
        level = "High Cognitive Risk – Recommend Specialist Referral"
        interpretation = (
            "The combined screening results indicate significant weaknesses in memory, language, or speech "
            "coherence. This is not a formal diagnosis, but a strong signal that detailed evaluation by a "
            "neurologist or psychiatrist is recommended."
        )
        
    return {
        "aeri_score": aeri,
        "level": level,
        "interpretation": interpretation
    }
