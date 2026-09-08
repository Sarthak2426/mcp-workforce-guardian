"""
Generates workers.json (600 workers) and daily_plan.json.

Skill level, efficiency, rejection rate, and employment status are drawn
from fixed distributions. The random seed is fixed, so re-running produces
the same dataset and test cases can reference specific worker_ids.

    python generate_workers.py
"""

import json
import random

random.seed(42)

NUM_WORKERS = 600
NUM_LINES = 15
CELLS_PER_LINE = ["Cell 1", "Cell 2", "Cell 3"]

FIRST_NAMES_M = [
    "Suresh", "Anil", "Rakesh", "Deepak", "Manoj", "Ramesh", "Vikas", "Sanjay",
    "Rajesh", "Ashok", "Naveen", "Pankaj", "Vinod", "Sunil", "Ravi", "Amit",
    "Rahul", "Vijay", "Arun", "Dinesh", "Mahesh", "Yogesh", "Prakash", "Sandeep",
    "Ajay", "Vishal", "Gaurav", "Nitin", "Sachin", "Rohit",
]
FIRST_NAMES_F = [
    "Meena", "Sunita", "Kavita", "Geeta", "Pooja", "Anita", "Rekha", "Priya",
    "Neha", "Kiran", "Shobha", "Usha", "Radha", "Lata", "Manju", "Seema",
    "Nisha", "Rani", "Kamla", "Savita", "Poonam", "Renu", "Asha", "Sarita",
    "Deepa", "Jyoti", "Sudha", "Vandana", "Shanti", "Kalpana",
]
LAST_NAMES = [
    "Yadav", "Kumar", "Verma", "Devi", "Singh", "Sharma", "Kumari", "Tiwari",
    "Patel", "Chauhan", "Joshi", "Gupta", "Mishra", "Pandey", "Rathi", "Bansal",
    "Agarwal", "Chaudhary", "Malik", "Rana", "Solanki", "Thakur", "Rawat",
    "Bhatt", "Nair", "Reddy", "Iyer", "Naidu", "Das", "Bose",
]

SKILL_LEVELS = ["Beginner", "Intermediate", "Expert"]
SKILL_WEIGHTS = [0.25, 0.50, 0.25]

# experts are more efficient and reject fewer parts
EFFICIENCY_RANGE = {
    "Beginner": (55, 68),
    "Intermediate": (68, 82),
    "Expert": (82, 96),
}
REJECTION_RATE_RANGE = {
    "Beginner": (0.04, 0.09),
    "Intermediate": (0.02, 0.05),
    "Expert": (0.01, 0.03),
}

NOTE_POOL = [
    "", "", "", "", "", "",  # most workers have no note
    "Trains new hires",
    "Consistently top performer",
    "New hire, still onboarding",
    "Flagged for a refresher safety training",
]


def make_line_cell_pairs():
    pairs = []
    for line_num in range(1, NUM_LINES + 1):
        for cell in CELLS_PER_LINE:
            pairs.append((f"Line {line_num}", cell))
    return pairs


def make_worker(worker_id: str, line_cell_pairs: list) -> dict:
    gender = random.choice(["Male", "Female"])
    first = random.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    skill = random.choices(SKILL_LEVELS, weights=SKILL_WEIGHTS)[0]

    roll = random.random()
    if roll < 0.03:
        status = "terminated"
    elif roll < 0.08:
        status = "on_leave"
    else:
        status = "active"

    if status == "terminated":
        line, cell = None, None
        present_today = False
    else:
        line, cell = random.choice(line_cell_pairs)
        present_today = False if status == "on_leave" else random.random() > 0.05

    eff_lo, eff_hi = EFFICIENCY_RANGE[skill]
    efficiency = round(random.uniform(eff_lo, eff_hi), 1)
    avg_hourly_output = round(efficiency * random.uniform(0.48, 0.56))

    shifts_worked = random.randint(120, 800)
    total_parts_made = avg_hourly_output * shifts_worked
    rej_lo, rej_hi = REJECTION_RATE_RANGE[skill]
    rejected_parts = round(total_parts_made * random.uniform(rej_lo, rej_hi))

    notes = random.choice(NOTE_POOL)
    if status == "on_leave":
        notes = "On approved personal leave this week"
    elif status == "terminated":
        notes = "Terminated for repeated quality issues; kept in records for audit history"

    return {
        "worker_id": worker_id,
        "worker_name": f"{first} {last}",
        "worker_gender": gender,
        "age": random.randint(19, 56),
        "skill_level": skill,
        "current_line": line,
        "current_cell": cell,
        "efficiency": efficiency,
        "total_parts_made": total_parts_made,
        "rejected_parts": rejected_parts,
        "avg_hourly_output": avg_hourly_output,
        "employment_status": status,
        "present_today": present_today,
        "notes": notes,
    }


def main():
    line_cell_pairs = make_line_cell_pairs()

    workers = [
        make_worker(f"W{1001 + i}", line_cell_pairs)
        for i in range(NUM_WORKERS)
    ]

    daily_plan = {
        "date": "2026-09-02",
        "lines": [
            {
                "line": f"Line {line_num}",
                "cells": [
                    {"cell": cell, "required_workers": random.randint(10, 18)}
                    for cell in CELLS_PER_LINE
                ],
            }
            for line_num in range(1, NUM_LINES + 1)
        ],
    }

    with open("workers.json", "w") as f:
        json.dump(workers, f, indent=2)

    with open("daily_plan.json", "w") as f:
        json.dump(daily_plan, f, indent=2)

    print(f"wrote {len(workers)} workers to workers.json")
    print(f"wrote {NUM_LINES * len(CELLS_PER_LINE)} cells to daily_plan.json")

    # quick sanity summary
    from collections import Counter
    status_counts = Counter(w["employment_status"] for w in workers)
    print(f"status breakdown: {dict(status_counts)}")


if __name__ == "__main__":
    main()
