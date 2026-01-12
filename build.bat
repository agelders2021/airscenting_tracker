REM pyinstaller --onefile --windowed --collect-all tkinterdnd2 --hidden-import babel.numbers airscenting_logger.py
pyinstaller airscenting_logger.spec
copy dist\airscenting_logger.exe .
pyinstaller trailing_logger.spec
REM pyinstaller --onefile --windowed --collect-all tkinterdnd2 --exclude-module matplotlib --exclude-module numpy --exclude-module scipy --exclude-module PyQt5 --hidden-import babel.numbers trailing_logger.py
copy dist\trailing_logger.exe .
