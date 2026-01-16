
def assess_epilepsy_risk(data):
    """
    Evaluates epilepsy risk based on questionnaire answers.
    Logic extracted from detection_app.views.epilepsy_home
    """
    # Helper to convert yes/no (boolean here) to weighted score
    def val(key, weight):
        return weight if data.get(key, False) else 0

    score = 0
    # You can tune these weights as you like
    score += val("q1", 3)  # history of seizure-like episodes
    score += val("q2", 3)  # jerking movements / witnessed seizures
    score += val("q3", 2)  # family history
    score += val("q4", 1)  # events after lack of sleep
    score += val("q5", 3)  # loss of awareness / confusion
    score += val("q6", 2)  # tongue biting / incontinence
    score += val("q7", 2)  # discomfort with flashing lights
    score += val("q8", 2)  # currently on anti-seizure meds

    risk_level = ""
    advice = ""

    # Basic interpretation
    if score <= 4:
        risk_level = "Low Epilepsy Risk (Based on Questionnaire)"
        advice = (
            "Current responses do not strongly suggest epilepsy. "
            "However, if the person experiences new or repeated episodes of fainting, jerking movements, "
            "or loss of awareness, they should still consult a doctor."
        )
    elif score <= 10:
        risk_level = "Moderate Epilepsy Risk"
        advice = (
            "There are some warning signs that may be consistent with seizure activity. "
            "It is advisable to consult a physician or neurologist for further evaluation, "
            "especially if episodes are increasing or affecting daily life."
        )
    else:
        risk_level = "High Epilepsy Risk – Recommend Specialist Referral"
        advice = (
            "The pattern of symptoms strongly suggests possible epileptic seizures. "
            "The person should be referred to a neurologist or epilepsy clinic for detailed assessment. "
            "Caregivers should be educated about seizure first-aid and safety precautions."
        )

    return {
        "score": score,
        "risk_level": risk_level,
        "advice": advice
    }
