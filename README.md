# ddtool
Simple thermal accumulation calcuation tool




Uses matplotlib, pandas, and xlrd python packages
'''
conda install matplotlib pandas xlrd
'''


make executable using pyinstaller
pyinststaller can be installed via conda
> pyinstaller -D ddtool_html.py




conda create -n exe python=3
activate exe
conda install -c conda-forge numpy
pip install pandas
pip install pyinstaller pypiwin32 
pip install pandas matplotlib xlrd


for UPX, download UPX (eg. upx394w) and put it under the directory upx (eg. upx\upx394w)
pyinstaller --clean -D --upx-dir upx\upx394w ddtool_html.py