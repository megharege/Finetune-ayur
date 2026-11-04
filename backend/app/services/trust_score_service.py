def calculate_bayesian_rating(sum_ratings: float, total_reviews: int, C: float = 5.0, m: float = 3.5) -> float:
    """
    Bayesian rating = (C * m + sum of ratings) / (C + n)
    Ensures that a doctor with 2 five-star reviews cannot outrank a doctor with 200 reviews averaging 4.8.
    """
    if total_reviews <= 0:
        return m
    bayesian = (C * m + sum_ratings) / (C + total_reviews)
    return round(bayesian, 2)

def calculate_trust_score(
    bayesian_rating: float,
    is_verified: bool,
    experience_years: int,
    completion_rate: float,
    avg_response_time_hours: float,
    profile_completeness: float,
    is_kaggle_seed: bool = False
) -> dict:
    """
    Trust score = 40% rating + 20% verification + 15% experience + 10% completion rate + 10% response time + 5% profile
    Seeded doctors are never marked Verified from the dataset alone.
    Scale: 0 to 100.
    """
    # 1. Rating component (40%): normalized from 1.0 - 5.0 scale to 0 - 100
    rating_score = max(0.0, min(100.0, (bayesian_rating / 5.0) * 100.0))
    rating_weighted = rating_score * 0.40
    
    # 2. Verification component (20%):
    # If verified: 100. If unverified/seed: 0. If pending with document: 25.
    if is_verified and not (is_kaggle_seed and not is_verified):
        verification_score = 100.0
    else:
        verification_score = 10.0 # Unverified seed
    verification_weighted = verification_score * 0.20
    
    # 3. Experience component (15%):
    # Benchmark: 20 years = 100 points
    exp_score = max(0.0, min(100.0, (experience_years / 20.0) * 100.0))
    exp_weighted = exp_score * 0.15
    
    # 4. Completion rate component (10%):
    completion_score = max(0.0, min(100.0, completion_rate))
    completion_weighted = completion_score * 0.10
    
    # 5. Response time component (10%):
    # Under 1 hour = 100, 2h = 90, 4h = 80, 12h = 60, 24h = 40, >48h = 20
    if avg_response_time_hours <= 1.0:
        response_score = 100.0
    elif avg_response_time_hours <= 2.0:
        response_score = 90.0
    elif avg_response_time_hours <= 4.0:
        response_score = 80.0
    elif avg_response_time_hours <= 12.0:
        response_score = 60.0
    elif avg_response_time_hours <= 24.0:
        response_score = 40.0
    else:
        response_score = 20.0
    response_weighted = response_score * 0.10
    
    # 6. Profile completeness component (5%):
    profile_score = max(0.0, min(100.0, profile_completeness))
    profile_weighted = profile_score * 0.05
    
    total_trust_score = round(
        rating_weighted +
        verification_weighted +
        exp_weighted +
        completion_weighted +
        response_weighted +
        profile_weighted,
        1
    )
    
    return {
        "trust_score": total_trust_score,
        "breakdown": {
            "bayesian_rating": {
                "value": bayesian_rating,
                "score_out_of_100": round(rating_score, 1),
                "weight": "40%",
                "contribution": round(rating_weighted, 1)
            },
            "verification": {
                "is_verified": is_verified,
                "score_out_of_100": round(verification_score, 1),
                "weight": "20%",
                "contribution": round(verification_weighted, 1),
                "note": "Seeded doctors require state council license verification" if is_kaggle_seed and not is_verified else "Verified against official register"
            },
            "experience": {
                "years": experience_years,
                "score_out_of_100": round(exp_score, 1),
                "weight": "15%",
                "contribution": round(exp_weighted, 1)
            },
            "completion_rate": {
                "rate": f"{completion_rate}%",
                "score_out_of_100": round(completion_score, 1),
                "weight": "10%",
                "contribution": round(completion_weighted, 1)
            },
            "response_time": {
                "hours": f"{avg_response_time_hours} hrs",
                "score_out_of_100": round(response_score, 1),
                "weight": "10%",
                "contribution": round(response_weighted, 1)
            },
            "profile_completeness": {
                "rate": f"{profile_completeness}%",
                "score_out_of_100": round(profile_score, 1),
                "weight": "5%",
                "contribution": round(profile_weighted, 1)
            }
        }
    }
