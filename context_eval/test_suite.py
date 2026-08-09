"""
Wanderpath Travel Agency - Long-Context Test Transcripts
========================================================
Defines 3 realistic, tool-heavy test transcripts where crucial early details
(e.g., shellfish allergy, passport expiration date) are buried under noisy tool outputs.
"""

def get_long_context_test_cases():
    return [
        {
            "id": "TC_1_Allergy_Bury",
            "target_fact": "shellfish allergy",
            "messages": [
                {"role": "system", "content": "You are a Wanderpath Travel assistant."},
                {"role": "user", "content": "Hi, I'm planning a trip for Marcus Vance. Note that he developed a severe shellfish allergy recently."},
                {"role": "assistant", "content": "Understood. Noted Marcus Vance's severe shellfish allergy."},
                # Buried under 10 heavy tool outputs
                {"role": "observation", "content": "FETCH_FLIGHTS_RESULT: " + "Flight WP-101 JFK->LHR base_price=$850.00 " * 20},
                {"role": "observation", "content": "FETCH_HOTELS_RESULT: " + "The Ritz London price_per_night=$650.00 " * 20},
                {"role": "user", "content": "Can you check hotel availability in London?"},
                {"role": "observation", "content": "AVAILABILITY_MATRIX_RESULT: " + "Room 101 available, Room 102 available " * 20},
                {"role": "user", "content": "What dining restrictions should we keep in mind for his hotel bookings?"}
            ]
        },
        {
            "id": "TC_2_Expired_Passport",
            "target_fact": "expired",
            "messages": [
                {"role": "system", "content": "=== ACTIVE PLAN SCRATCHPAD ===\nPRIMARY GOAL: Sophia Chen Tokyo Tour"},
                {"role": "user", "content": "Sophia Chen's passport number is US123456789, expiration date is 2024-05-15 (expired)."},
                {"role": "assistant", "content": "Flagged expired passport for Sophia Chen."},
                {"role": "observation", "content": "VISA_CHECK_POLICY_RESULT: " + "Schengen visa requirements and passport validity rules " * 25},
                {"role": "observation", "content": "FLIGHT_MATRIX_RESULT: " + "WP-202 PacificFly SFO->HND price=$1250.00 " * 25},
                {"role": "user", "content": "Can we finalize her flight ticket issuance now?"}
            ]
        },
        {
            "id": "TC_3_Seat_Preference_Change",
            "target_fact": "aisle seat",
            "messages": [
                {"role": "system", "content": "You are a travel assistant."},
                {"role": "user", "content": "Liam Neeson originally wanted a window seat, but due to a leg injury he now strictly requires an aisle seat."},
                {"role": "assistant", "content": "Updated seating preference to aisle seat."},
                {"role": "observation", "content": "SEAT_MAP_RESULT: " + "Row 12 Window, Row 12 Aisle, Row 13 Window, Row 13 Aisle " * 30},
                {"role": "user", "content": "Which seat category should I reserve for him?"}
            ]
        }
    ]