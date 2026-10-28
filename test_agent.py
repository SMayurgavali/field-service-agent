from dotenv import load_dotenv
from crewai import Task, Crew, Process
from agents import create_triage_agent, create_inventory_agent

load_dotenv()

triage_agent = create_triage_agent()
inventory_agent = create_inventory_agent()

#sample machine complaint
complaint =(
    "The machine is overheating and the cooling fan"
    "appears not to be running."
)

#Task 1: Diagnose the complaint
diagnosis_task = Task(
    description="""
    Analyze this machine complaint: {complaint}

    Identify:
    1. Reported symptoms
    2. Possible causes
    3. Uncertainty in the diagnosis
    4. One primary spare part

    Use the exact part name from this inventory catalog:
    - Cooling Fan
    - Pressure Sensor
    - Hydraulic Pump
    - Oil Filter
    - Temperature Sensor

    End your report with one line in this format:
    PRIMARY_SPARE_PART: <exact catalog part name>

    Replace the placeholder with the actual selected part name.
    Do not invent inventory information.
    """,
    expected_output=(
        "A diagnosis report with symptoms, possible causes,"
        "uncertainty, and a primary spare part name."
    ),
    agent=triage_agent,
)

#Task 2 ; verify the part in wwarehouse inventory
inventory_task =Task(
    description=(
        "Read the diagnosis from the previous task."
        "Identify the primary spare part recommend by the"
        "triage agent,Use the check warehouse inventory tool"
        "with the exact part name to verify availability.\n\n"
        "report the verified status, part ID, stock quantity,"
        "and aisle location. If the tool says part_not_found,"
        "report that clearly. Never invent inventory details."
    ),

    expected_output =(
        "An inventory report containing the verified part name,"
        "status, part ID, stock quamtity, and warehouse location"
    ),
    agent=inventory_agent,
    context=[diagnosis_task],
)

crew = Crew(
    agents=[triage_agent, inventory_agent],
    tasks=[diagnosis_task, inventory_task],
    process=Process.sequential,
    verbose = True,
)

if __name__ == "__main__":
    crew.kickoff(inputs={"complaint": complaint})

print("\n--- DIAGNOSIS REPORT ---\n")
print(diagnosis_task.output.raw)

print("\n--- INVENTORY REPORT ---\n")
print(inventory_task.output.raw)