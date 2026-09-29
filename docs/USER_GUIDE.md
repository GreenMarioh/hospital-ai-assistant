# User guide

Demo accounts (created by `make seed`, **local/dev only**): password `DemoPass!12345` for all except admin (`ChangeMe!12345`).
`admin@hospital.example.com`, `staff@hospital.example.com`, `doctor1@hospital.example.com` … `doctor6@…` (Cardiology, General Medicine, Orthopedics, Pediatrics, Dermatology, Neurology), `patient1@example.com` … `patient3@example.com`.

> The AI assistant provides decision support and administrative help only. It never diagnoses or prescribes, and everything clinical-adjacent is marked "AI-generated, requires clinician review". In an emergency, call your local emergency number.

## Patients
1. **Register** at `/register` (name, date of birth, email, password of 12+ characters). You are signed in straight away.
2. **Symptom check** (Symptom check & FAQ): describe what you feel and answer up to two short questions per turn. You get an urgency level (emergency / urgent / routine / self-care), a suggested department and a short reason. If you mention warning signs (chest pain, stroke signs, severe bleeding, trouble breathing, …) a red **emergency banner** appears immediately: call your local emergency number. If the assistant is unavailable you'll be told and can still book directly.
3. **Hospital FAQ**: ask about visiting hours, departments, policies. Answers come only from the hospital's knowledge base.
4. **Book an appointment**: choose a department and doctor, click a free time. Or type to the **booking assistant** ("book me a cardiologist next Tuesday morning"): it proposes a slot and **nothing is booked until you press Confirm**.
5. **My appointments**: reschedule or cancel any upcoming booking. If your preferred day is full, **join the waitlist** on the booking page; you're notified (email/SMS) if a slot opens.
6. **My records**: your profile, visits, prescriptions, documents (download links expire after 5 minutes) and timeline. You can update your contact details with reception.
Reminders are sent 24 hours and 2 hours before each appointment.

## Reception / staff
- **Patients**: search by name, phone or patient ID; register new patients (demographics, emergency contact, allergies, blood group, insurance; the insurance ID is stored encrypted and masked in lists). Open a patient to see demographics and timeline and **upload documents** (PDF/PNG/JPEG up to 10 MB).
- **Calendar & booking**: pick a doctor, use Day/Week views, click an appointment to **cancel** or mark **no-show**; find a patient and click a free slot to **book on their behalf**.
- Staff do not see clinical notes, diagnoses or prescriptions (least privilege).

## Doctors
- **My schedule**: day/week calendar of your appointments; open the chart, mark completed / no-show.
- **Availability & leave**: set weekly working windows and add leave/holiday ranges (existing bookings are not cancelled automatically).
- **My patients**: patients with an appointment or visit with you; a full-text **records search** across your visit notes.
- **Patient chart**: **Pre-visit AI briefing** (overview, flagged items such as allergies and overdue follow-ups, key history, recent visits; regenerate any time; if the AI service is down you get a structured overview from the record), **Add visit note** (complaint, vitals, notes, your diagnosis, prescription, follow-up date), visit history. Edits are versioned; every change is attributable.

## Admin
- **Dashboard**: appointments per day, no-show rate, average booking lead time, department load, AI assistant usage; date range filter; **CSV export**.
- **Users**: create staff/doctor/admin accounts (doctors need a department), activate/deactivate accounts, add departments.
- **Audit logs**: every API access with user, role, action, resource, status and IP; filter by resource, action and dates.
- Data-subject tools (API): patient export and erasure request under `/api/admin/patients/{id}/…` (see `docs/API.md`).
