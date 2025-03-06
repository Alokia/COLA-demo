# prepare

Make sure you have anaconda installed.

```bash
# Create a virtual environment with the name cola, using version 3.11.5 of python
conda create -n cola python=3.11.5

# Activate the virtual environment
conda activate cola
```

Next, install the packages you need to run.

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

# run
input your task in gaia_task.txt

then run the following command

```bash
python main.py
```

