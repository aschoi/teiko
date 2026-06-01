

## Relational Database Schema Design Decisions  

I chose a database schema using 3 tables. This seemed to make the most sense to me, since three of the columns (project, subject, sample) had unique ids that could be utilized as primary keys. The relationship is as follows:  

&nbsp;&nbsp;&nbsp;&nbsp;project -> subject -> sample  

This strikes the best balance between reducing duplication while maintaining a reasonable logical hierarchy. I chose to have project be a table, even though it only currently is made up of 3 rows (prj1, prj2, prj3), because I'm making the assumption that there would be relevaent metadata that would be associated with a given project that wasn't necessarily included in the assessement csv. Having a separate table for projects also makes it easier to add additional meta data later on, if need be.  

Subject as a table makes sense, because there are 3 samples per subject, and each subject would be considered an "entity" onto itself.  

### The database layout:  

projects:  
| Column | Type | Constraint |
|---|---|---|
| project_id | INTEGER | PRIMARY KEY |
| project_name | TEXT | |

subjects:
| Column | Type | Constraint |
|---|---|---|
| subject_id | INTEGER | PRIMARY KEY |
| project_id | INTEGER | FOREIGN KEY → projects(project_id) |
| subject_name | TEXT | |
| condition | TEXT | |
| age | INTEGER | |
| sex | TEXT | |
| treatment | TEXT | |
| response | TEXT | |


samples:  
| Column | Type | Constraint |
|---|---|---|
| sample_id | INTEGER | PRIMARY KEY |
| subject_id | INTEGER | FOREIGN KEY → subjects(subject_id) |
| sample_name | TEXT | |
| sample_type | TEXT | |
| time_from_treatment_start | INTEGER | |
| b_cell | REAL | |
| cd8_t_cell | REAL | |
| cd4_t_cell | REAL | |
| nk_cell | REAL | |
| monocyte | REAL | |


A major engineering decision and tradeoff comes from deciding between performance vs storage. As a db scales, one option would be to have fewer tables, which would increase overall performance, because not as many joins would be needed. However this approach suffers in two ways. First, storage capacity starts to become a concern. Second, if data within a table or column needs to be updated, it could lead to "missed updates" which in turn leads to db inconsistency. If we care about ensuring these two problems, storage limits and inconsistency, occur infrequently, then we could instead split our data up into many more tables. This approach can suffer though, because that means in order to retrieve data, more joins will be needed during execution, which in turn creates performance issues. The approach I've chosen here attempts to strike the balance between performance and storage concerns, though I'm sure it could be improved upon.  

When make dashboard is executed, this is the dashboard link:  
http://localhost:8501/  

I also want to mention, I used Claude and ChatGPT for some of the SQL syntax and heavily for the streamlit dashboard. The specific workflow that was asked of me during this assessment was new to me. While I truly believe I would be able to grok this workflow quickly given just a little time, since this was the first time I've seen this particular type of workflow, I needed the additional assistance, especially when it came to syntax and terminology.  



## Statistical Analysis  

Most of the data seemed noisy to me. The only aspect that stood out SLIGHTLY to me was in project 1, cd 4 t-cell rose slightly.  

responders (median percent)  
| Time | percentage |
|---|---|
| 0 | 29.81 |
| 7 | 30.69 |
| 14 | 31.52 |

non-responders (median)  
| Time | percentage |
|---|---|
| 0 | 29.81 |
| 7 | 29.31 |
| 14 | 30.01 |   

Non-responders stay relatively flat, but responders over the course of 14 (time intervals. days?) have a cd 4 t-cell percentage rise delta of 0.88 and 0.83 for a total of 1.71. This isn't necessarily a big delta, but its also not nothing. Its at least enough to make it worth mentioning. 


## Data Subset Analysis  
Conditions  
- projcts: all projects  
- condition: melanoma  
- treatment: miraclib  
- response: yes  
- sample type: PBMC  
- time: 0  
- sex: M  

b_cell count avg: 10,401.28