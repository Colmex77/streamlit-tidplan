
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import networkx as nx
import io

# ----- Klassdefinition -----
class Task:
    def __init__(self, name, duration, dependencies=None, resources=None, start_offset=0):
        self.name = name
        self.duration = duration
        self.dependencies = dependencies or []
        self.resources = resources or []
        self.start_offset = start_offset
        self.early_start = 0
        self.early_finish = 0
        self.late_start = 0
        self.late_finish = 0
        self.slack = 0
        self.is_critical = False

# ----- Stil -----
st.set_page_config(page_title="Tidplan", layout="wide")
st.markdown("""<style>
h1 { font-size: 2.5em; margin-bottom: 0.2em; }
h3 { color: #444; }
.logo-img { max-height: 80px; border-radius: 10px; }
.block-container { padding-top: 1rem; }
</style>""", unsafe_allow_html=True)

# ----- Logotyp -----
with st.expander("🎨 Ladda upp logotyp"):
    uploaded_logo = st.file_uploader("Välj en bildfil", type=["png", "jpg", "jpeg"])
    if uploaded_logo:
        st.image(uploaded_logo, width=150)

st.title("📆 Proffsigt Tidplaneringssystem")

# ----- Funktioner -----
def calculate_schedule(tasks):
    G = nx.DiGraph()
    task_names = {t.name for t in tasks}
    for task in tasks:
        G.add_node(task.name, task=task)
        for dep in task.dependencies:
            if dep not in task_names:
                st.error(f"Beroendet '{dep}' finns inte som uppgift.")
                return []
            G.add_edge(dep, task.name)

    try:
        sorted_tasks = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        st.error("Det finns en cirkulär beroendeloop i uppgifterna!")
        return []

    for name in sorted_tasks:
        task = next((t for t in tasks if t.name == name), None)
        if not task:
            st.error(f"Uppgift '{name}' saknas i listan.")
            return []
        if not task.dependencies:
            task.early_start = task.start_offset
        else:
            task.early_start = max(
                next(t for t in tasks if t.name == d).early_finish for d in task.dependencies
            ) + task.start_offset
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
        color = 'red' if task.is_critical else '#4682B4'
        ax.barh(task.name, task.duration, left=task.early_start, color=color, edgecolor='black')
        ax.text(task.early_start + task.duration / 2, i, task.name, va='center', ha='center', color='white')
    ax.set_xlabel("Dagar")
    ax.set_ylabel("Uppgifter")
    ax.set_title("📊 Gantt-schema med kritisk linje")
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

# ----- Formulär -----
with st.expander("➕ Lägg till uppgift"):
    with st.form("task_form"):
        cols = st.columns([3, 1])
        name = cols[0].text_input("Uppgiftsnamn")
        duration = cols[1].number_input("Varaktighet (dagar)", min_value=1, step=1)
        dependencies = st.text_input("Beroenden (kommaseparerat)").split(",")
        dependencies = [d.strip() for d in dependencies if d.strip()]
        resources = st.text_input("Resurser (kommaseparerat)").split(",")
        resources = [r.strip() for r in resources if r.strip()]
        submitted = st.form_submit_button("✅ Lägg till uppgift")

if 'tasks' not in st.session_state:
    st.session_state.tasks = []

if submitted and name:
    st.session_state.tasks.append(Task(name, duration, dependencies, resources))
    st.success(f"Uppgiften '{name}' har lagts till!")

if st.session_state.tasks:
    st.subheader("📋 Planerade uppgifter")

    # Justering
    st.sidebar.header("⚙️ Startförskjutning")
    for task in st.session_state.tasks:
        task.start_offset = st.sidebar.slider(
            f"{task.name}", min_value=0, max_value=10, value=task.start_offset
        )

    tasks = calculate_schedule(st.session_state.tasks)
    if tasks:
        render_gantt(tasks)
        st.markdown("### 📤 Exportera schema")
        export_data(tasks)
else:
    st.info("Lägg till uppgifter för att generera ett schema.")
