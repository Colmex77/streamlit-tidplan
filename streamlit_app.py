
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import networkx as nx
import io

# ----- Klassdefinition -----
class Task:
    def __init__(self, name, duration, dependencies=None, resources=None):
        self.name = name
        self.duration = duration
        self.dependencies = dependencies or []
        self.resources = resources or []
        self.early_start = 0
        self.early_finish = 0
        self.late_start = 0
        self.late_finish = 0
        self.slack = 0
        self.is_critical = False

# ----- Funktioner -----
def calculate_schedule(tasks):
    G = nx.DiGraph()
    for task in tasks:
        G.add_node(task.name, task=task)
        for dep in task.dependencies:
            G.add_edge(dep, task.name)

    sorted_tasks = list(nx.topological_sort(G))

    for name in sorted_tasks:
        task = next(t for t in tasks if t.name == name)
        if not task.dependencies:
            task.early_start = 0
        else:
            task.early_start = max(
                next(t for t in tasks if t.name == d).early_finish for d in task.dependencies
            )
        task.early_finish = task.early_start + task.duration

    project_duration = max(t.early_finish for t in tasks)

    for name in reversed(sorted_tasks):
        task = next(t for t in tasks if t.name == name)
        successors = list(G.successors(name))
        if not successors:
            task.late_finish = project_duration
        else:
            task.late_finish = min(
                next(t for t in tasks if t.name == s).late_start for s in successors
            )
        task.late_start = task.late_finish - task.duration
        task.slack = task.late_start - task.early_start
        task.is_critical = task.slack == 0

    return tasks


def render_gantt(tasks):
    fig, ax = plt.subplots(figsize=(10, len(tasks)))
    for i, task in enumerate(tasks):
        color = 'red' if task.is_critical else 'blue'
        ax.barh(task.name, task.duration, left=task.early_start, color=color)
        ax.text(task.early_start + task.duration/2, i, task.name, va='center', ha='center', color='white')
    ax.set_xlabel("Dagar")
    ax.set_ylabel("Uppgifter")
    ax.set_title("Gantt-schema med kritisk linje")
    st.pyplot(fig)


def export_data(tasks):
    data = [
        {
            "Namn": t.name,
            "Start": t.early_start,
            "Slut": t.early_finish,
            "Slack": t.slack,
            "Kritisk": t.is_critical,
            "Resurser": ", ".join(t.resources),
            "Beroenden": ", ".join(t.dependencies)
        }
        for t in tasks
    ]
    df = pd.DataFrame(data)
    
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False)
    st.download_button("📄 Ladda ner som Excel", data=excel_io.getvalue(), file_name="tidplan.xlsx")

    json_io = io.StringIO()
    df.to_json(json_io, orient="records", force_ascii=False, indent=2)
    st.download_button("📃 Ladda ner som JSON", data=json_io.getvalue(), file_name="tidplan.json")


# ----- Streamlit-gränssnitt -----
st.set_page_config(page_title="Tidplanesystem", layout="wide")
st.title("📆 Tidplaneringsverktyg med kritisk linje")

with st.form("task_form"):
    st.subheader("Lägg till en uppgift")
    name = st.text_input("Uppgiftsnamn")
    duration = st.number_input("Varaktighet (dagar)", min_value=1, step=1)
    dependencies = st.text_input("Beroenden (kommaseparerat)").split(",")
    dependencies = [d.strip() for d in dependencies if d.strip()]
    resources = st.text_input("Resurser (kommaseparerat)").split(",")
    resources = [r.strip() for r in resources if r.strip()]
    submitted = st.form_submit_button("Lägg till uppgift")

if 'tasks' not in st.session_state:
    st.session_state.tasks = []

if submitted and name:
    st.session_state.tasks.append(Task(name, duration, dependencies, resources))

if st.session_state.tasks:
    st.subheader("Planerade uppgifter")
    tasks = calculate_schedule(st.session_state.tasks)
    render_gantt(tasks)
    export_data(tasks)
else:
    st.info("Lägg till uppgifter för att generera ett schema.")
