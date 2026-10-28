from datetime import datetime
import pandas as pd
import re
import streamlit as st
from crewai import Crew, Task, Process
from inventory_tool import check_warehouse_inventory
from database import init_db, save_complaint, get_recent_complaints
import time
from retry_utils import run_with_retries

from agents import (
    create_triage_agent,
    create_inventory_agent,
)

st.set_page_config(
    page_title="Field Service AI",
    page_icon="🛠️",
    layout="wide",
)
init_db()

if "complaint_history" not in st.session_state:
    st.session_state["complaint_history"] = []

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .hero {
        padding: 1.5rem;
        border-radius: 16px;
        background: linear-gradient(120deg, #10243A, #204D68);
        color: white;
        margin-bottom: 1.5rem;
    }
    .hero h1 {
        color: white;
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def extract_field(text, label):
    """Extract a field from the inventory report."""
    pattern = (
        rf"{re.escape(label)}\s*\**\s*:\s*\**\s*([^\n*]+)"
    )
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(1).strip().strip("`")

    return "Not reported"


def run_crew_with_retries(crew, max_attempts=3):
    """Retry the workflow for temporary API/server errors."""

    retryable_errors = (
        "503",
        "429",
        "500",
        "502",
        "504",
        "unavailable",
        "resource_exhausted",
        "timed out",
        "timeout",
    )

    for attempt in range(1, max_attempts + 1):
        try:
            return crew.kickoff()

        except Exception as exc:
            error_text = str(exc).lower()

            is_retryable = any(
                error.lower() in error_text
                for error in retryable_errors
            )

            if not is_retryable or attempt == max_attempts:
                raise

            wait_seconds = attempt * 2

            st.warning(
                f"Temporary API error. Retrying "
                f"({attempt + 1}/{max_attempts}) "
                f"in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Workflow failed after retries.")


def run_field_service_workflow(complaint):
    """Run the triage agent followed by the inventory agent."""

    triage_agent = create_triage_agent()
    inventory_agent = create_inventory_agent()

    diagnosis_task = Task(
        description=f"""
        Analyze this machine complaint:

        {complaint}

        Identify:
        1. Reported symptoms
        2. Possible causes
        3. Uncertainty in the diagnosis
        4. Recommended next diagnostic checks
        5. One primary spare part

        Choose the part that best matches the symptoms.
        Do not claim that a component is definitely defective
        without supporting evidence.

        Use the exact name from this catalog:
        - Cooling Fan
        - Pressure Sensor
        - Hydraulic Pump
        - Oil Filter
        - Temperature Sensor

        End your report with:
        PRIMARY_SPARE_PART: <exact catalog part name>

        Replace the placeholder with the selected part name.
        """,
        expected_output=(
            "A field triage report with symptoms, possible causes, "
            "uncertainty, and one primary spare part. The report "
            "must end with PRIMARY_SPARE_PART and the exact part name."
        ),
        agent=triage_agent,
    )

    inventory_task = Task(
        description="""
        Read the diagnosis from the previous task.

        Identify the primary spare part recommended by the
        triage agent. Use the Check Warehouse Inventory tool
        with the exact catalog part name.

        Report the verified:
        - Part name
        - Availability status
        - Part ID
        - Stock quantity
        - Warehouse aisle location

        If the part is not found, report that clearly.
        Never invent quantities, IDs, or locations.
        """,
        expected_output=(
            "An inventory verification report containing the actual "
            "tool result, part ID, stock quantity, and aisle location."
        ),
        agent=inventory_agent,
        context=[diagnosis_task],
    )

    crew = Crew(
        agents=[triage_agent, inventory_agent],
        tasks=[diagnosis_task, inventory_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        run_with_retries(
        crew.kickoff,
        on_retry=lambda next_attempt, max_attempts,
            wait_seconds, error: st.warning(
                f"Temporary API error. Retrying "
                f"({next_attempt}/{max_attempts}) "
                f"in {wait_seconds} seconds..."
            ),
    )

        diagnosis = diagnosis_task.output.raw
        inventory = inventory_task.output.raw

    except Exception:
        # Keep the diagnosis if Task 1 already completed.
        task_output = getattr(diagnosis_task, "output", None)
        diagnosis = getattr(task_output, "raw", None)

        if not diagnosis:
            # Diagnosis itself did not complete.
            raise

        # Extract the exact spare-part name from the diagnosis.
        match = re.search(
            r"PRIMARY_SPARE_PART\s*:\s*([^\n\r]+)",
            diagnosis,
            re.IGNORECASE,
        )

        if not match:
            raise

        part_name = match.group(1).strip().strip("`* ")

        # Fallback: query the existing inventory function directly.
        stock_result = check_warehouse_inventory(part_name)

        inventory = f"""
        ### Inventory Verification Report

        - **Verified Part Name:** {stock_result.get('part_name', part_name)}
        - **Status:** {stock_result.get('status', 'unknown').replace('_', ' ').title()}
        - **Part ID:** {stock_result.get('part_id', 'Not reported')}
        - **Stock Quantity:** {stock_result.get('stock_count', 'Not reported')}
        - **Warehouse Location:** {stock_result.get('aisle_location', 'Not reported')}
        """

    return {
        "diagnosis": diagnosis,
        "inventory": inventory,
    }


# Sidebar
with st.sidebar:
    st.title("🛠️ Field Service AI")
    st.caption("Autonomous diagnosis and inventory verification")

    st.divider()

    st.markdown("### Workflow")
    st.markdown(
        """
        1. Enter a machine complaint.
        2. Triage Agent analyzes it.
        3. Inventory Agent checks warehouse stock.
        4. Review the final reports.
        """
    )

    st.divider()
    st.caption("Powered by CrewAI, Gemini and Streamlit")


# Header
st.markdown(
    """
    <div class="hero">
        <h1>Field Service Intelligence Dashboard</h1>
        <p>
            Diagnose machine complaints, identify spare parts,
            and verify warehouse inventory.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("New Service Complaint")

with st.form("complaint_form"):
    complaint = st.text_area(
        "Describe the machine problem",
        value=(
            "The machine is overheating and the cooling fan "
            "appears not to be running."
        ),
        height=120,
        placeholder="Enter the symptoms observed by the technician...",
    )

    submitted = st.form_submit_button(
        "🔍 Analyze Complaint",
        type="primary",
        width="stretch",
    )

if submitted:
    if not complaint.strip():
        st.warning("Please enter a machine complaint.")
    else:
        st.session_state.pop("workflow_error", None)
        st.session_state.pop("workflow_result", None)

        try:
            with st.spinner(
                "AI agents are diagnosing the complaint "
                "and checking warehouse stock..."
            ):
                result = run_field_service_workflow(complaint)

            st.session_state["workflow_result"] = result
            st.session_state["submitted_complaint"] = complaint

            diagnosis = result.get("diagnosis", "")
            inventory = result.get("inventory", "")

            recommended_part = extract_field(
                diagnosis, "PRIMARY_SPARE_PART"
            )

            part_name = extract_field(inventory, "Part Name")

            availability = extract_field(
                inventory, "Availability Status"
            )

            if availability == "Not reported":
                availability = extract_field(inventory, "Status")

            part_id = extract_field(inventory, "Part ID")
            stock = extract_field(inventory, "Stock Quantity")

            location = extract_field(
                inventory, "Warehouse Aisle Location"
            )

            if location == "Not reported":
                location = extract_field(
                    inventory, "Warehouse Location"
                )

            if recommended_part == "Not reported":
                recommended_part = part_name

            save_complaint(
                complaint=complaint.strip(),
                diagnosis=diagnosis,
                inventory=inventory,
                recommended_part=recommended_part,
                availability=availability,
                part_id=part_id,
                stock_quantity=stock,
                warehouse_location=location,
            )

            st.divider()
            st.subheader("🕘 Recent Complaint History")

            history = get_recent_complaints(limit=50)

            if history:
                history_df = pd.DataFrame(history)

                history_df = history_df.rename(columns={
                    "created_at": "Time",
                    "complaint": "Complaint",
                    "recommended_part": "Recommended Part",
                    "availability": "Availability",
                    "part_id": "Part ID",
                    "stock_quantity": "Stock Quantity",
                    "warehouse_location": "Warehouse Location",
                    "diagnosis_report": "Diagnosis Report",
                    "inventory_report": "Inventory Report",
                })

                display_columns = [
                    "Time",
                    "Complaint",
                    "Recommended Part",
                    "Availability",
                    "Part ID",
                    "Stock Quantity",
                    "Warehouse Location",
                ]

                st.dataframe(
                    history_df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "⬇️ Download Complaint History",
                    data=history_df.to_csv(index=False).encode("utf-8"),
                    file_name="complaint_history.csv",
                    mime="text/csv",
                    key="download_complaint_history",
                )

            else:
                st.info(
                    "No complaint history yet. "
                    "Analyze a complaint to save your first record."
                )

        except Exception as exc:
            st.session_state["workflow_error"] = (
                f"{type(exc).__name__}: {exc}"
            )


if st.session_state.get("workflow_error"):
    st.error("The workflow could not be completed.")
    st.code(st.session_state["workflow_error"])
    st.info(
        "Check the terminal for the full error. "
        "A temporary Gemini API error may require another attempt."
    )


result = st.session_state.get("workflow_result")

if result:
    diagnosis = result["diagnosis"]
    inventory = result["inventory"]

    primary_part = extract_field(
        diagnosis, "PRIMARY_SPARE_PART"
    )
    part_name = extract_field(inventory, "Part Name")

    status = extract_field(inventory, "Availability Status")
    if status == "Not reported":
        status = extract_field(inventory, "Status")

    part_id = extract_field(inventory, "Part ID")
    stock = extract_field(inventory, "Stock Quantity")

    aisle = extract_field(inventory, "Warehouse Aisle Location")
    if aisle == "Not reported":
        aisle = extract_field(inventory, "Warehouse Location")

    st.divider()
    st.subheader("Service Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Recommended Part", primary_part)
    col2.metric("Part ID", part_id)
    col3.metric("Stock Quantity", stock)
    col4.metric("Warehouse Location", aisle)

    if status.lower() == "available":
        st.success(
            f"{part_name} is available in the warehouse."
        )
    elif status.lower() == "out_of_stock":
        st.warning(
            f"{part_name} is currently out of stock."
        )
    elif status.lower() == "not reported":
        st.info(
            "Review the inventory report below for the verified status."
        )
    else:
        st.info(f"Inventory status: {status}")

    tab1, tab2, tab3 = st.tabs(
        ["📊 Overview", "🧠 Diagnosis Report", "📦 Inventory Report"]
    )

    with tab1:
        st.markdown("### Complaint")
        st.write(st.session_state["submitted_complaint"])

        st.markdown("### Recommended Spare Part")
        st.write(primary_part)

        st.markdown("### Inventory Verification")
        st.write(inventory)

    with tab2:
        st.markdown(diagnosis)

    with tab3:
        st.markdown(inventory)

    combined_report = (
        "# Field Service Report\n\n"
        f"## Complaint\n{st.session_state['submitted_complaint']}\n\n"
        f"## Diagnosis\n{diagnosis}\n\n"
        f"## Inventory Verification\n{inventory}\n"
    )

    st.download_button(
        "⬇️ Download Full Report",
        data=combined_report,
        file_name="field_service_report.md",
        mime="text/markdown",
        width="stretch",
    )

else:
    if not st.session_state.get("workflow_error"):
        st.info(
            "Enter a complaint and click Analyze Complaint "
            "to generate the diagnosis and inventory reports."
        )

st.divider()

st.subheader("🕘 Recent Complaint History")

history = st.session_state.get("complaint_history", [])

if history:
    history_df = pd.DataFrame(history[::-1])

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Complaint History",
        data=pd.DataFrame(history).to_csv(index=False).encode("utf-8"),
        file_name="complaint_history.csv",
        mime="text/csv",
        key="download_complaint_history",
    )
else:
    st.info(
        "No completed complaints yet. "
        "Analyze a complaint to create your first history record."
    )
