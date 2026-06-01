import sqlite3
import csv
import os
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px


conn = sqlite3.connect("cell_count_db.db")
cursor = conn.cursor()

### DATABASE INITIALIZATION ###

# projects table creation
cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_id      INTEGER PRIMARY KEY,
        project_name    TEXT NOT NULL
    )
""")
print("projects table created.")

# subjects table creation
cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id      INTEGER PRIMARY KEY,
        project_id      INTEGER NOT NULL,
        subject_name    TEXT NOT NULL,
        condition       TEXT, 
        age             INTEGER,
        sex             TEXT,
        treatment       TEXT,
        response        TEXT, 
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
    )
""")
print("subjects table created.")

# samples table creation
cursor.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        sample_id                   INTEGER PRIMARY KEY,
        subject_id                  INTEGER NOT NULL,
        sample_name                 TEXT NOT NULL,
        sample_type                 TEXT,
        time_from_treatment_start   INTEGER,
        b_cell                      REAL,
        cd8_t_cell                  REAL,
        cd4_t_cell                  REAL,
        nk_cell                     REAL,
        monocyte                    REAL,
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
    )
""")
print("samples table created.")

print("db initialized.")


#-----------------------------------------------------#
# load data

base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "cell-count.csv")

df = pd.read_csv(csv_path)

# Ensure numbers are numbers and not strings
numeric_columns = [
    'age', 
    'time_from_treatment_start', 
    'b_cell', 
    'cd8_t_cell', 
    'cd4_t_cell', 
    'nk_cell', 
    'monocyte'
]
df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

# load projects data
projects_hmap = {}
for proj_name in df["project"].unique():

    proj_id = int(proj_name.replace("prj", ""))
    cursor.execute('INSERT OR IGNORE INTO projects (project_id, project_name) VALUES (?, ?)',   
                    (proj_id, proj_name))
    projects_hmap[proj_name] = proj_id

conn.commit()

# load subjects data
subject_headers = ["subject", "project", "condition", "age", "sex", "treatment", "response"]
subjects_unique = df[subject_headers].drop_duplicates()
subjects_hmap = {}

for _, row in subjects_unique.iterrows():
    proj_id = projects_hmap[row["project"]]
    subj_id = int(row["subject"].replace("sbj", ""))
    cursor.execute(
        """
        INSERT OR IGNORE INTO subjects 
        (subject_id, project_id, subject_name, condition, age, sex, treatment, response) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        (subj_id, proj_id, row["subject"], row['condition'], row['age'], row['sex'], row['treatment'], row['response'])
    )

    subjects_hmap[row["subject"]] = subj_id

conn.commit()

# load sample data
for _, row in df.iterrows():

    subj_id = subjects_hmap[row["subject"]]
    samp_id = int(row["sample"].replace("sample", ""))
    cursor.execute(
        """
        INSERT OR IGNORE INTO samples 
        (sample_id, subject_id, sample_name, sample_type, time_from_treatment_start, 
        b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte)  
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        (samp_id, subj_id, row["sample"], row["sample_type"], row["time_from_treatment_start"], 
        row['b_cell'], row['cd8_t_cell'], row['cd4_t_cell'], row['nk_cell'], row['monocyte'])
    )

conn.commit()


pd.read_sql("SELECT * FROM projects", conn).to_csv("output/projects.csv", index=False)
pd.read_sql("SELECT * FROM subjects", conn).to_csv("output/subjects.csv", index=False)
pd.read_sql("SELECT * FROM samples", conn).to_csv("output/samples.csv", index=False)


# --------------------------------------------------------------------
# part 2

cursor.execute("""
    SELECT
        sa.sample_id AS sample,
        sa.b_cell + sa.cd8_t_cell + sa.cd4_t_cell + sa.nk_cell + sa.monocyte AS total_count,
        sa.b_cell,
        sa.cd8_t_cell,
        sa.cd4_t_cell,
        sa.nk_cell,
        sa.monocyte
    FROM samples sa
    JOIN subjects s ON sa.subject_id = s.subject_id
""")

df_wide = pd.DataFrame(cursor.fetchall(), columns=[
    "sample", "total_count", "b_cell", "cd8_t_cell", 
    "cd4_t_cell", "nk_cell", "monocyte"
])

cell_columns = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

df_long = df_wide.melt(
    id_vars = ["sample", "total_count"],
    value_vars = cell_columns,
    var_name = "population",
    value_name = "count"
)

df_long["percentage"] = round(df_long["count"] * 100.0 / df_long["total_count"], 2)
df_long = df_long.sort_values(by=["sample", "population"]).reset_index(drop=True)

print(df_long[["sample", "total_count", "population", "count", "percentage"]])
df_long.to_csv("output/cell_percentages.csv", index=False)


# --------------------------------------------------------------------
# part 3


## Box Plot HTML 1 ##

cursor.execute("""
    SELECT
        sa.sample_id AS sample,
        s.response,
        p.project_name,
        sa.b_cell + sa.cd8_t_cell + sa.cd4_t_cell + sa.nk_cell + sa.monocyte AS total_count,
        sa.b_cell,
        sa.cd8_t_cell,
        sa.cd4_t_cell,
        sa.nk_cell,
        sa.monocyte
    FROM samples sa
    JOIN subjects s ON sa.subject_id = s.subject_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE
        s.condition = 'melanoma'
""")

df_wide = pd.DataFrame(cursor.fetchall(), columns=[
    "sample", "response", "project_name", "total_count", 
    "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"
])

cell_columns = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

df_long = df_wide.melt(
    id_vars=["sample", "response", "project_name", "total_count"],
    value_vars=cell_columns,
    var_name="population",
    value_name="count"
)

df_long["percentage"] = round(df_long["count"] * 100.0 / df_long["total_count"], 2)

fig = px.box(
    df_long,
    x="population",
    y="percentage",
    color="response",
    facet_col="project_name",     # one panel per study
    title="Cell Population Percentage (time_taken combined) — Melanoma",
    labels={
        "population": "Cell Type",
        "percentage": "% of Total Cells",
        "response": "Response",
        "project_name": "Study"
    }
)

fig.write_html("output/melanoma_boxplot_1.html")


## Box Plot HTML 2 ##

cursor.execute("""
    SELECT
        sa.sample_id AS sample,
        s.response,
        p.project_name,
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
    WHERE
        s.condition = 'melanoma'
""")

df_wide = pd.DataFrame(cursor.fetchall(), columns=[
    "sample", "response", "project_name", "time_from_treatment_start",
    "total_count", "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"
])

cell_columns = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

df_long = df_wide.melt(
    id_vars=["sample", "response", "project_name", "time_from_treatment_start", "total_count"],
    value_vars=cell_columns,
    var_name="population",
    value_name="count"
)

df_long["percentage"] = round(df_long["count"] * 100.0 / df_long["total_count"], 2)


studies = df_long["project_name"].unique()

with open("output/melanoma_boxplot_2.html", "w") as f:
    for study in studies:
        df_study = df_long[df_long["project_name"] == study]

        fig = px.box(
            df_study,
            x="time_from_treatment_start",   # time on x axis
            y="percentage",
            color="response",
            facet_col="population",           # one panel per cell type
            title=f"Cell Populations Over Time — {study}",
            labels={
                "time_from_treatment_start": "Day",
                "percentage": "% of Total Cells",
                "response": "Response",
                "population": "Cell Type"
            },
            category_orders={
                "time_from_treatment_start": [0, 10, 20]  # ensure day order
            }
        )

        f.write(f"<h1>{study}</h1>")
        f.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))
        f.write("<hr>")



## Responders vs Non-responders

cursor.execute("""
    SELECT
        s.response,
        p.project_name,
        COUNT(DISTINCT s.subject_id) AS subject_count
    FROM subjects s
    JOIN projects p ON s.project_id = p.project_id
    WHERE
        s.condition = 'melanoma'
    GROUP BY
        p.project_name, s.response
""")

df_counts = pd.DataFrame(cursor.fetchall(), columns=[
    "response", "project_name", "subject_count"
])

# add a combined row across all studies
df_combined = df_counts.groupby("response")["subject_count"].sum().reset_index()
df_combined["project_name"] = "All Studies"

# stack them together
df_all = pd.concat([df_counts, df_combined], ignore_index=True)

# plot
fig = px.bar(
    df_all,
    x="project_name",
    y="subject_count",
    color="response",
    barmode="group",
    title="Responders vs Non-Responders by Study",
    labels={
        "project_name": "Study",
        "subject_count": "Number of Subjects",
        "response": "Response"
    },
    category_orders={
        "project_name": sorted(df_counts["project_name"].unique().tolist()) + ["All Studies"]
    }
)

with open("output/melanoma_responders.html", "w") as f:
    f.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))


conn.close()

print("done.")

