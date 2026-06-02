import db_manager


mess_samples = [
    "Summary: Mess food was cold and rice was undercooked during lunch.",
    "Summary: Students reported poor hygiene in the mess dining area.",
    "Summary: Dinner was delayed and many students could not eat on time.",
    "Summary: Mess menu was not followed and food quality was poor.",
    "Summary: Students complained about insects near the mess counter.",
    "Summary: Breakfast was served late, causing students to miss morning classes.",
    "Summary: Drinking water near the mess was not clean.",
    "Summary: Chapatis were hard and not freshly prepared.",
    "Summary: Students reported stomach pain after eating mess food.",
    "Summary: Food quantity was insufficient during dinner.",
    "Summary: Mess staff did not respond properly to student complaints.",
    "Summary: Vegetables served in lunch were stale.",
    "Summary: The mess area was not cleaned after previous meals.",
    "Summary: Students requested better quality control in mess food.",
    "Summary: Milk served during breakfast was spoiled.",
]

hostel_samples = [
    "Summary: Water supply was unavailable in the hostel block.",
    "Summary: Hostel room had leakage from the ceiling.",
    "Summary: Bathroom cleaning was not done for several days.",
    "Summary: Warden was unavailable during an urgent hostel issue.",
    "Summary: Students reported broken lights in the hostel corridor.",
    "Summary: Hostel Wi-Fi was not working for several days.",
    "Summary: Room fan was not functioning despite repeated complaints.",
    "Summary: Students complained about mosquitoes in hostel rooms.",
    "Summary: Lift in the hostel was not working properly.",
    "Summary: Hostel washrooms had blocked drainage.",
    "Summary: Students reported noise disturbance late at night.",
    "Summary: Hostel gate entry issue caused inconvenience to students.",
    "Summary: Room cleaning service was not provided on schedule.",
    "Summary: Students requested repair of broken hostel furniture.",
    "Summary: Power backup was not available during electricity cuts.",
]

academics_samples = [
    "Summary: Assignment upload was not showing correctly on the portal.",
    "Summary: Student requested help with delayed exam form approval.",
    "Summary: Attendance was marked incorrectly for a class.",
    "Summary: Faculty timetable update was not communicated to students.",
    "Summary: Exam result was missing from the academic portal.",
    "Summary: Student requested extension for lab report submission.",
    "Summary: Internal marks were entered incorrectly on the portal.",
    "Summary: Classroom projector was not working during lecture.",
    "Summary: Students complained about sudden schedule change.",
    "Summary: Course material was not uploaded before the exam.",
    "Summary: Student requested correction in subject registration.",
    "Summary: Exam hall ticket was not generated on time.",
    "Summary: Faculty was unavailable for doubt clarification.",
    "Summary: Students requested rescheduling of overlapping exams.",
    "Summary: Practical marks were not updated in the academic system.",
]


for i in range(50):
    db_manager.store_in_db(
        "mess_summarized",
        f"{mess_samples[i % len(mess_samples)]} Case #{i + 1}",
    )

    db_manager.store_in_db(
        "hostel_summarized",
        f"{hostel_samples[i % len(hostel_samples)]} Case #{i + 1}",
    )

    db_manager.store_in_db(
        "academics_summarized",
        f"{academics_samples[i % len(academics_samples)]} Case #{i + 1}",
    )

print("Dummy data added successfully.")