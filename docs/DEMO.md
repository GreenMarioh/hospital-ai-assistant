# Demo script (about 10 minutes)

Setup: `make up && make seed` (or `make e2e-up`), open http://localhost:3000. Optional: set `GEMINI_API_KEY` in `.env` before `make up` to see live AI replies; without it the graceful-degradation paths are shown instead (both are worth showing).

1. **Patient onboarding (1 min)** - `/register` as a new patient → lands in the portal.
2. **Emergency safety (1 min)** - Symptom check: type "I have crushing chest pain". Red banner appears instantly, urgency *emergency*, department *Emergency*, no LLM involved (point out: rules run first and cannot be overridden). Start a new check with "mild headache for two days": with an API key you get a guided conversation ending in urgency + department; without one you see the "assistant unavailable, you can still book" state.
3. **FAQ (30 s)** - "What are the visiting hours for the ICU?" → answer with source `visiting-hours.md`.
4. **Booking (2 min)** - Book appointment → Cardiology → Dr. Asha Rao → pick a slot. Then try the booking assistant: "book me a cardiologist next Tuesday morning" → confirmation card → nothing exists until *Confirm*. Show *My appointments* (reschedule/cancel) and the waitlist form.
5. **Doctor (2 min)** - sign out, `doctor1@hospital.example.com`: schedule (week view) shows the new appointment → open chart → **Generate briefing** (flags allergies etc., AI-generated banner) → **Add visit note** with a prescription → visit appears.
6. **Patient sees the outcome (30 s)** - sign in as the patient → *My records* shows the visit, but no AI summaries.
7. **Reception (1 min)** - `staff@hospital.example.com`: register a walk-in, upload a PDF, book via calendar, cancel. Note: no clinical notes visible.
8. **Admin (1.5 min)** - `admin@hospital.example.com`: dashboard KPIs/charts, CSV export, audit log filtered to `patients/visits` (shows the doctor's access), users and departments.
9. **Resilience (optional)** - `docker compose stop worker` / unset the API key and repeat step 2; show `/readyz`, request ids and the JSON logs.
