REM pyinstaller --onefile --windowed --collect-all tkinterdnd2 --hidden-import babel.numbers airscenting_logger.py
REM pyinstaller airscenting_logger.spec
REM copy dist\airscenting_logger.exe .
REM pyinstaller trailing_logger.spec
REM pyinstaller --onefile --windowed --collect-all tkinterdnd2 --exclude-module matplotlib --exclude-module numpy --exclude-module scipy --exclude-module PyQt5 --hidden-import babel.numbers trailing_logger.py
REM copy dist\trailing_logger.exe .
pyinstaller sar-k9-training-record.spec
copy dist\SAR-K9-training-record.exe .
