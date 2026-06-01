setup:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

pipeline:
	. venv/bin/activate && python3 load_data.py
	. venv/bin/activate && python3 -m http.server 8502 --directory output

dashboard:
	. venv/bin/activate && streamlit run dashboard.py
