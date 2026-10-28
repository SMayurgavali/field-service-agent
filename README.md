# Field Service Agent

A Streamlit field-service assistant that uses CrewAI and Gemini to triage machine complaints and check spare-part inventory. Complaint history is stored locally in SQLite.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set your `GEMINI_API_KEY`.
4. Start the mock inventory API in one terminal:

   ```powershell
   uvicorn erp_api:app --host 127.0.0.1 --port 8001
   ```

5. Start the Streamlit app in another terminal:

   ```powershell
   streamlit run app.py
   ```

## Tests

```powershell
python -m unittest discover -s tests
```

The local `.env`, SQLite database, and virtual environment are intentionally excluded from version control.
