import streamlit as st
import sqlite3
import pandas as pd

import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go


# ----------------------------
# Connect to DB
# ----------------------------
conn = sqlite3.connect("cell_count_db.db")


st.title("Teiko Interactive Dashboard")

# ----------------------------
# Dropdowns
# ----------------------------
cols = st.columns(6)

projects = pd.read_sql("SELECT DISTINCT project_name FROM projects", conn)["project_name"].tolist()
selected_projects = cols[0].multiselect(
    "Project",
    options=projects,
    default=[]    # all selected by default
)

conditions = ["All"] + pd.read_sql("SELECT DISTINCT condition FROM subjects", conn)["condition"].tolist()
selected_condition = cols[1].selectbox("Condition", conditions)

treatments = ["All"] + pd.read_sql("SELECT DISTINCT treatment FROM subjects", conn)["treatment"].tolist()
selected_treatment = cols[2].selectbox("Treatment", treatments)

responses_raw = pd.read_sql("SELECT DISTINCT response FROM subjects", conn)["response"].tolist()
responses = ["All"] + ["N/A" if pd.isna(r) or r is None else r for r in responses_raw]
selected_response = cols[3].selectbox("Response", responses)

sample_types = ["All"] + pd.read_sql("SELECT DISTINCT sample_type FROM samples", conn)["sample_type"].tolist()
selected_sample_type = cols[4].selectbox("Sample Type", sample_types)

timepoints = ["All"] + pd.read_sql(
    "SELECT DISTINCT time_from_treatment_start FROM samples ORDER BY time_from_treatment_start",
    conn
)["time_from_treatment_start"].tolist()
selected_time = cols[5].selectbox("Time Point", timepoints)



cols2 = st.columns(6)

cols2[2].write("Age")
with cols2[2].expander("50 - 79"):
    min_age = st.number_input("Min", min_value=50, max_value=79, value=50)
    max_age = st.number_input("Max", min_value=50, max_value=79, value=79)


sexes = ["All"] + pd.read_sql("SELECT DISTINCT sex FROM subjects", conn)["sex"].tolist()
selected_sex = cols2[3].selectbox("Sex", sexes)


# ----------------------------
# Build query dynamically
# ----------------------------

where_conditions = ["1=1"]
params = []

if selected_projects:
    placeholders = ",".join(["?" for _ in selected_projects])
    where_conditions.append(f"p.project_name IN ({placeholders})")
    params.extend(selected_projects)

if selected_condition != "All":
    where_conditions.append("s.condition = ?")
    params.append(selected_condition)

if selected_treatment != "All":
    where_conditions.append("s.treatment = ?")
    params.append(selected_treatment)

if selected_response != "All":
    if selected_response == "N/A":
        where_conditions.append("s.response IS NULL")
    else:
        where_conditions.append("s.response = ?")
        params.append(selected_response)

if selected_sample_type != "All":
    where_conditions.append("sa.sample_type = ?")
    params.append(selected_sample_type)

if selected_time != "All":
    where_conditions.append("sa.time_from_treatment_start = ?")
    params.append(selected_time)

where_conditions.append("s.age >= ?")
params.append(min_age)

where_conditions.append("s.age <= ?")
params.append(max_age)

if selected_sex != "All":
    where_conditions.append("s.sex = ?")
    params.append(selected_sex)

where_clause = " AND ".join(where_conditions)

query = f"""
    SELECT
        sa.sample_id AS sample,
        p.project_name,
        s.response,
        s.condition,
        sa.sample_type,
        sa.time_from_treatment_start,
        sa.b_cell + sa.cd8_t_cell + sa.cd4_t_cell + sa.nk_cell + sa.monocyte AS total_count,
        sa.b_cell,
        sa.cd8_t_cell,
        sa.cd4_t_cell,
        sa.nk_cell,
        sa.monocyte
    FROM samples sa
    JOIN subjects s ON sa.subject_id = s.subject_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE {where_clause}
"""

df_wide = pd.read_sql(query, conn, params=params)

# ----------------------------
# Melt to long
# ----------------------------
cell_columns = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

df_long = df_wide.melt(
    id_vars=["sample", "project_name", "response", "condition", "sample_type", "time_from_treatment_start", "total_count"],
    value_vars=cell_columns,
    var_name="population",
    value_name="count"
)

df_long["percentage"] = round(df_long["count"] * 100.0 / df_long["total_count"], 2)
df_long = df_long.sort_values(by=["sample", "population"]).reset_index(drop=True)


# ----------------------------
# Section 1: Summary stats
# ----------------------------
st.subheader("Summary Statistics")
summary = df_long.groupby("population")["percentage"].agg(["mean", "std", "min", "max"]).round(2)
summary.columns = ["Mean %", "Std %", "Min %", "Max %"]
st.dataframe(summary)


# ----------------------------
# Section 2: Download
# ----------------------------
st.download_button(
    label="Download Full Table as CSV",
    data=df_long[["sample", "total_count", "population", "count", "percentage"]].to_csv(index=False),
    file_name="cell_populations.csv",
    mime="text/csv"
)


st.subheader("Sample Cell Counts")
st.dataframe(df_wide[["sample", "total_count", "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]])

# ----------------------------
# Section 3: Paginated raw table
# ----------------------------
st.subheader("Raw Data")
st.caption(f"{len(df_long)} rows returned.")

page_size = 100
total_pages = max(1, len(df_long) // page_size + (1 if len(df_long) % page_size > 0 else 0))

pCols = st.columns(5)
page = pCols[4].number_input("Page", min_value=1, max_value=total_pages, value=1)
start = (page - 1) * page_size
end = start + page_size

pCols[0].write("")
pCols[0].write("")  
pCols[0].caption(f"Page {page} of {total_pages}  \nRows {start+1} to {min(end, len(df_long))}")

st.dataframe(df_long.iloc[start:end][["sample", "total_count", "population", "count", "percentage"]])


# ----------------------------
# Section 4: Cell populations over time
# ----------------------------
st.subheader("Cell Populations Over Time")

fig_time = px.box(
    df_long,
    x="time_from_treatment_start",
    y="percentage",
    color="response",
    facet_col="population",
    title="Cell Population % Over Time",
    labels={
        "time_from_treatment_start": "Day",
        "percentage": "% of Total Cells",
        "response": "Response",
        "population": "Cell Type"
    },
    category_orders={"time_from_treatment_start": [0, 10, 20]}
)
st.plotly_chart(fig_time, use_container_width=True)

# ----------------------------
# Section 5: Responders vs Non-Responders
# ----------------------------
st.subheader("Responders vs Non-Responders")

cursor = conn.cursor()
cursor.execute(f"""
    SELECT
        s.response,
        p.project_name,
        COUNT(DISTINCT s.subject_id) AS subject_count
    FROM subjects s
    JOIN projects p ON s.project_id = p.project_id
    JOIN samples sa ON sa.subject_id = s.subject_id
    WHERE {where_clause}
    GROUP BY p.project_name, s.response
""", params)

df_counts = pd.DataFrame(cursor.fetchall(), columns=["response", "project_name", "subject_count"])

df_combined = df_counts.groupby("response")["subject_count"].sum().reset_index()
df_combined["project_name"] = "All Studies"
df_all = pd.concat([df_counts, df_combined], ignore_index=True)

studies = ["All Studies"] + sorted(df_counts["project_name"].unique().tolist())

fig_resp = make_subplots(
    rows=2, cols=3,
    subplot_titles=studies,
    specs=[
        [{"colspan": 3}, None, None],
        [{}, {}, {}]
    ]
)

colors = {"yes": "steelblue", "no": "salmon"}
positions = [(1, 1), (2, 1), (2, 2), (2, 3)]

for i, study in enumerate(studies):
    df_study = df_all[df_all["project_name"] == study]
    row, col = positions[i]

    for response in ["yes", "no"]:
        df_resp = df_study[df_study["response"] == response]
        fig_resp.add_trace(
            go.Bar(
                x=df_resp["response"],
                y=df_resp["subject_count"],
                name=response,
                marker_color=colors[response],
                showlegend=(i == 0)
            ),
            row=row, col=col
        )

fig_resp.update_layout(
    title="Responders vs Non-Responders by Study",
    barmode="group",
    height=700
)

st.plotly_chart(fig_resp, use_container_width=True)

conn.close()

