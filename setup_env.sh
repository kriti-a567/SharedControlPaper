pip install uv

uv venv

source .venv/bin/activate

uv sync

uv pip install --editable .       
cd notebooks  
jupyter execute *.ipynb
