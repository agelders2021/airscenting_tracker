# Makefile for SAR-K9-training-record
# Requires: GNU Make 3.81+, PyInstaller, Windows 11
# Usage:  make          - build the exe
#         make clean    - remove build artifacts
#         make rebuild  - clean then build

PYINSTALLER = pyinstaller
SPEC_FILE   = sar-k9-training-record.spec
TARGET      = SAR-K9-training-record.exe
DIST_EXE    = dist\$(TARGET)

# All Python source files that comprise the application
SOURCES = sar-k9-training-record.py \
          about_dialog.py \
          air_helper.py \
          air_ui.py \
          backup_management.py \
          backup_sync.py \
          config.py \
          database.py \
          export_pdf.py \
          help_window.py \
          lock_manager.py \
          password_manager.py \
          schema.py \
          setup_tab.py \
          splash_screen.py \
          status_bar.py \
          sv.py \
          t_ui_database.py \
          tips.py \
          trail_helper.py \
          trail_ui.py \
          ui_database.py \
          ui_file_operations.py \
          ui_form_management.py \
          ui_misc2.py \
          ui_misc_data_ops.py \
          ui_navigation.py \
          ui_trailing.py \
          ui_utils.py \
          working_dialog.py

.PHONY: all clean rebuild

all: $(TARGET)

$(TARGET): $(SOURCES) $(SPEC_FILE)
	$(PYINSTALLER) $(SPEC_FILE)
	copy $(DIST_EXE) .

clean:
	if exist build rmdir /s /q build
	if exist dist  rmdir /s /q dist
	if exist $(TARGET) del $(TARGET)

rebuild: clean all
