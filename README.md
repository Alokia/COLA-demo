# Overview
This is a demonstration code during the development period, for the sake of subsequent research, we do not intend to open the full code for the time being.
However, the demonstration code already contains all the mechanisms introduced in all the papers, and the full code only optimizes the execution logic and the interaction process, with no additional innovations.

# Prepare

Make sure you have anaconda installed.

```bash
# Create a virtual environment with the name cola, using version 3.11.5 of python
conda create -n cola python=3.11.5

# Activate the virtual environment
conda activate cola
```

```bash
pip install openai==1.40.1
pip install pillow==10.3.0
pip install pyyaml==6.0.1
pip install pandas==2.1.4
pip install openpyxl==3.1.5

conda install conda-forge::faiss==1.7.4

pip install PyAutoGUI==0.9.54
pip install pywinauto==0.6.8
pip install pydantic==2.8.2

conda install anaconda::psutil==5.9.0
pip install python-docx==1.1.2
```

# Run
input your task in task.txt

then run the following command

```bash
python main.py
```

