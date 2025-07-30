import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, 
                             QFrame, QScrollArea, QCheckBox, QComboBox,
                             QMessageBox, QSplitter, QHeaderView, QMenuBar,
                             QDialog, QDialogButtonBox, QTextEdit, QSpinBox,QListWidget,
                             QDoubleSpinBox, QInputDialog, QFileDialog)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QAction, QKeySequence, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime
import sqlite3
import json
import os
import tempfile
import subprocess
from category_management import CategoryManagementDialog
from inventory_management import InventoryManagementDialog, StockAdjustmentDialog
from customer_management import CustomerManagementDialog, CustomerSelectionDialog
# ReportLab imports for professional PDF receipts
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available. Install with: pip install reportlab")

# Import the product management database
try:
    from product_management import DatabaseManager
except ImportError:
    # Create a simple fallback if product_management is not available
    class DatabaseManager:
        def __init__(self, db_path="pos_database.db"):
            self.db_path = db_path
            self.init_fallback_db()
            
        def init_fallback_db(self):
            """Initialize basic database structure"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic products table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                sale_price REAL DEFAULT 0.0,
                quantity INTEGER DEFAULT 0
            )
            ''')
            
            # Sales table for receipts
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_number TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                subtotal REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                tax_amount REAL DEFAULT 0.0,
                total_amount REAL DEFAULT 0.0,
                payment_amount REAL DEFAULT 0.0,
                change_amount REAL DEFAULT 0.0,
                sale_date TEXT DEFAULT CURRENT_TIMESTAMP,
                cashier TEXT DEFAULT 'POS User'
            )
            ''')
            
            # Sale items table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER,
                product_id INTEGER,
                product_name TEXT,
                quantity REAL,
                unit_price REAL,
                total_price REAL,
                FOREIGN KEY (sale_id) REFERENCES sales (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')
            
            conn.commit()
            conn.close()
            
        def search_products(self, query):
            """Search products by name or barcode"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, barcode, '', 0, sale_price, '', '', 0 
                FROM products 
                WHERE name LIKE ? OR barcode LIKE ?
                LIMIT 20
            ''', (f'%{query}%', f'%{query}%'))
            products = cursor.fetchall()
            conn.close()
            return products
            
        def save_sale(self, sale_data, sale_items):
            """Save sale and items to database"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Insert sale
                cursor.execute('''
                    INSERT INTO sales (receipt_number, subtotal, discount_amount, tax_amount, 
                                     total_amount, payment_amount, change_amount, sale_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', sale_data)
                
                sale_id = cursor.lastrowid
                
                # Insert sale items
                for item in sale_items:
                    cursor.execute('''
                        INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (sale_id, item['product_id'], item['description'], item['quantity'], item['price'], item['total']))
                
                conn.commit()
                return sale_id
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
            
        def get_product_by_barcode(self, barcode):
            """Get product by barcode"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, barcode, '', 0, 0, 0, 0, sale_price 
                FROM products 
                WHERE barcode = ?
            ''', (barcode,))
            product = cursor.fetchone()
            conn.close()
            return product
            
        def get_all_products(self):
            """Get all products"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, barcode, '', quantity, sale_price, '', '', 0 
                FROM products 
                ORDER BY name
                LIMIT 50
            ''')
            products = cursor.fetchall()
            conn.close()
            return products
            
        def save_sale(self, sale_data, sale_items):
            """Save sale and items to database"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Insert sale
                cursor.execute('''
                    INSERT INTO sales (receipt_number, subtotal, discount_amount, tax_amount, 
                                     total_amount, payment_amount, change_amount, sale_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', sale_data)
                
                sale_id = cursor.lastrowid
                
                # Insert sale items
                for item in sale_items:
                    cursor.execute('''
                        INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (sale_id, item['product_id'], item['description'], item['quantity'], item['price'], item['total']))
                
                conn.commit()
                return sale_id
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

class ProductButton(QPushButton):
    """Custom product button with category styling"""
    def __init__(self, text, category_color="#FF6B6B", product_data=None):
        super().__init__(text)
        self.product_data = product_data or {}
        self.setMinimumSize(120, 80)
        self.setMaximumSize(200, 120)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {category_color};
                border: 2px solid #333;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 11px;
                text-align: center;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(category_color)};
                border: 3px solid #555;
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(category_color, 0.3)};
            }}
        """)
    
    def darken_color(self, color, factor=0.2):
        """Darken a hex color by a factor"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * (1 - factor)) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

class NumericKeypad(QWidget):
    """Numeric keypad widget for quantity and payment input"""
    number_clicked = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        layout.setSpacing(5)
        
        # Number buttons
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('.', 3, 0), ('0', 3, 1), ('CLR', 3, 2)
        ]
        
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setMinimumSize(60, 50)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90E2;
                    border: 2px solid #333;
                    border-radius: 5px;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #357ABD;
                }
                QPushButton:pressed {
                    background-color: #2E5F8A;
                }
            """)
            btn.clicked.connect(lambda checked, t=text: self.number_clicked.emit(t))
            layout.addWidget(btn, row, col)
        
        self.setLayout(layout)

class OrderTable(QTableWidget):
    """Order display table widget"""
    item_quantity_changed = pyqtSignal(int, float)
    item_removed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize OrderTable with optimized column sizing"""
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['DESCRIPTION', 'QTY', 'PRICE', 'TOTAL', 'ACTION', 'BARCODE'])
        
        # Get header and set resize modes
        header = self.horizontalHeader()
        
        # Fixed column widths optimized for the right panel
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Description - takes remaining space
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # QTY - fixed width
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # PRICE - fixed width  
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # TOTAL - fixed width
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # ACTION - fixed width
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # BARCODE - fixed width
        
        # Set optimal fixed widths for right panel (assuming ~400px total width)
        self.setColumnWidth(1, 50)   # QTY - smaller
        self.setColumnWidth(2, 70)   # PRICE - medium
        self.setColumnWidth(3, 80)   # TOTAL - medium
        self.setColumnWidth(4, 50)   # ACTION - smaller for button
        self.setColumnWidth(5, 100)  # BARCODE - medium
        
        # Description will take remaining space (~50px) which should be enough
        
        # Hide barcode column by default
        self.setColumnHidden(5, True)
        
        # Set minimum section sizes to prevent over-compression
        header.setMinimumSectionSize(40)
        
        # Styling for better visibility
        self.setStyleSheet("""
            QTableWidget {
                background-color: #E8F4F8;
                border: 2px solid #333;
                gridline-color: #333;
                font-size: 11px;
                selection-background-color: #4A90E2;
            }
            QHeaderView::section {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #333;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 3px;
                border-bottom: 1px solid #ccc;
            }
            QTableWidget::item:selected {
                background-color: #357ABD;
                color: white;
            }
        """)
        
        # Set row height for better fit
        self.verticalHeader().setDefaultSectionSize(25)
        self.verticalHeader().hide()  # Hide row numbers
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

class PDFReceiptDialog(QDialog):
    """PDF receipt preview and print dialog"""
    def __init__(self, pdf_file, parent=None):
        super().__init__(parent)
        self.pdf_file = pdf_file
        self.pos_window = parent
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("PDF Receipt - 80x297mm Format")
        self.setMinimumSize(400, 600)
        
        layout = QVBoxLayout()
        
        # Status label
        status_label = QLabel("📄 Professional PDF Receipt Generated")
        status_label.setStyleSheet("""
            QLabel {
                background-color: #2E8B57;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(status_label)
        
        # File info
        info_text = QTextEdit()
        info_content = f"""
📄 PDF Receipt Details:

📍 Format: 80x297mm thermal paper
📍 File: {os.path.basename(self.pdf_file)}
📍 Location: {self.pdf_file}
📍 Size: {os.path.getsize(self.pdf_file) / 1024:.1f} KB
📍 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🖨️ Printing Options:
• Direct Print: Automatically sends to default thermal printer
• Manual Print: Opens file for manual printer selection
• Save Copy: Save to custom location

📋 Receipt Features:
• Professional PDF layout
• Optimized for 80mm thermal printers
• Perfect margins and spacing
• High-quality fonts and formatting
• Automatic paper size detection

🔧 Supported Printers:
• Epson TM-T88IV/V
• Star TSP143III
• Citizen CT-S310II
• Most ESC/POS thermal printers
        """
        
        info_text.setPlainText(info_content)
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Arial", 10))
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        layout.addWidget(info_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Direct print button
        direct_print_btn = QPushButton("🖨️ Print Now")
        direct_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
        """)
        direct_print_btn.clicked.connect(self.direct_print)
        
        # Manual print button
        manual_print_btn = QPushButton("📋 Manual Print")
        manual_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        manual_print_btn.clicked.connect(self.manual_print)
        
        # Save copy button
        save_btn = QPushButton("💾 Save Copy")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FF8C00;
            }
        """)
        save_btn.clicked.connect(self.save_copy)
        
        # View PDF button
        view_btn = QPushButton("👁️ View PDF")
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #6A5ACD;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5A4FCF;
            }
        """)
        view_btn.clicked.connect(self.view_pdf)
        
        # Close button
        close_btn = QPushButton("✖️ Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(direct_print_btn)
        button_layout.addWidget(manual_print_btn)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(view_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def direct_print(self):
        """Direct print to thermal printer"""
        if self.pos_window:
            self.pos_window.print_pdf_direct(self.pdf_file)
        self.close()
    
    def manual_print(self):
        """Open PDF for manual printing"""
        try:
            if os.name == "nt":  # Windows
                os.startfile(self.pdf_file)
            elif os.name == "posix":  # macOS and Linux
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", self.pdf_file])
            
            QMessageBox.information(self, "PDF Opened", 
                                  "PDF receipt opened in default viewer.\n"
                                  "Please select your thermal printer and print.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {e}")
    
    def save_copy(self):
        """Save copy of PDF to custom location"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Receipt", f"receipt_80x297mm_{timestamp}.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.pdf_file, file_path)
                QMessageBox.information(self, "Success", 
                                      f"PDF receipt saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {e}")
    
    def view_pdf(self):
        """View PDF in default viewer"""
        self.manual_print()

class ReceiptDialog(QDialog):
    """Receipt preview and print dialog"""
    def __init__(self, receipt_text, parent=None):
        super().__init__(parent)
        self.receipt_text = receipt_text
        self.receipt_saved = False
        self.pos_window = parent  # Store reference to main POS window
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Receipt Preview - 80x297mm Paper")
        self.setMinimumSize(380, 800)  # Adjusted for 80x297mm paper ratio
        self.setMaximumSize(420, 900)  # Keep it narrow but taller for 297mm length
        
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2E8B57;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        # Receipt preview
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.receipt_text)
        
        # Use monospace font optimized for 80mm thermal printer
        font = QFont("Courier New", 9)  # Font size for 40 characters width
        font.setFixedPitch(True)
        self.text_edit.setFont(font)
        self.text_edit.setReadOnly(True)
        
        # Style to look like 80x297mm thermal paper
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                font-family: 'Courier New';
                line-height: 1.3;
                max-width: 350px;
            }
        """)
        
        layout.addWidget(self.text_edit)
        
        # Paper info label
        paper_info = QLabel("📄 80x297mm paper (40 chars width) - Thermal Receipt")
        paper_info.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 5px;
                background-color: #f0f0f0;
                border-radius: 3px;
                text-align: center;
            }
        """)
        layout.addWidget(paper_info)
        
        # Size info
        size_info = QLabel("Perfect for 80mm thermal printers with long paper")
        size_info.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 10px;
                padding: 3px;
                text-align: center;
                font-style: italic;
            }
        """)
        layout.addWidget(size_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        print_btn = QPushButton("🖨️ Print")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        print_btn.clicked.connect(self.print_receipt)
        
        # Thermal printer button
        thermal_btn = QPushButton("🔥 Thermal")
        thermal_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #FF4444;
            }
        """)
        thermal_btn.clicked.connect(self.print_thermal)
        thermal_btn.setToolTip("Direct thermal printer (ESC/POS)")
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
        """)
        save_btn.clicked.connect(self.save_receipt)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(print_btn)
        button_layout.addWidget(thermal_btn)
        button_layout.addWidget(save_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def showEvent(self, event):
        """Show status when dialog opens"""
        super().showEvent(event)
        if self.receipt_saved:
            self.status_label.setText("✅ Sale saved to database successfully!")
            self.status_label.show()
        else:
            self.status_label.setText("⚠️ Sale not saved to database!")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #FF6B6B;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            self.status_label.show()
    
    def print_receipt(self):
        """Print the receipt optimized for thermal printer"""
        printer = QPrinter()
        
        # Basic printer configuration (simplified for compatibility)
        printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
        
        print_dialog = QPrintDialog(printer, self)
        print_dialog.setWindowTitle("Print Receipt - Thermal Printer")
        
        if print_dialog.exec() == QDialog.DialogCode.Accepted:
            # Use the text edit's built-in print method
            self.text_edit.print(printer)
            QMessageBox.information(self, "Success", "Receipt sent to printer!")
            
            # For direct thermal printer communication (ESC/POS commands):
            # self.print_to_thermal_printer()
    
    def print_to_thermal_printer(self):
        """Direct thermal printer communication optimized for 80x297mm paper"""
        # ESC/POS commands specifically for 80x297mm thermal paper
        
        esc_pos_commands = []
        
        # Initialize printer
        esc_pos_commands.append(b'\x1b\x40')  # ESC @ (Initialize printer)
        
        # Set character set for international characters
        esc_pos_commands.append(b'\x1b\x74\x00')  # ESC t 0 (Character set)
        
        # Set print area for 80mm paper (40 characters)
        esc_pos_commands.append(b'\x1d\x57\x00\x00\x00\x00\x40\x01\x00\x00')  # Set print area
        
        # Set line spacing optimized for 297mm length
        esc_pos_commands.append(b'\x1b\x33\x18')  # ESC 3 (line spacing = 24/180 inch)
        
        # Set font size (normal - perfect for 40 chars on 80mm)
        esc_pos_commands.append(b'\x1d\x21\x00')  # GS ! 0 (normal font size)
        
        # Receipt text (convert to bytes)
        receipt_bytes = self.receipt_text.encode('utf-8', errors='ignore')
        esc_pos_commands.append(receipt_bytes)
        
        # Add extra spacing for the long 297mm paper
        esc_pos_commands.append(b'\n\n\n\n\n')  # Extra line feeds
        
        # Cut paper (full cut)
        esc_pos_commands.append(b'\x1d\x56\x42\x00')  # GS V B 0 (Full cut)
        
        # Combine all commands
        full_command = b''.join(esc_pos_commands)
        
        # For Windows thermal printer communication, you can use:
        # Method 1: Direct port printing
        """
        import win32print
        import win32api
        
        printer_name = win32print.GetDefaultPrinter()
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Receipt 80x297mm", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, full_command)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
        """
        
        # Method 2: Serial/USB communication for thermal printers
        """
        import serial
        try:
            # Common COM ports for thermal printers
            for port in ['COM1', 'COM2', 'COM3', 'COM4']:
                try:
                    printer = serial.Serial(port, 9600, timeout=1)
                    printer.write(full_command)
                    printer.close()
                    print(f"Receipt sent to thermal printer on {port}")
                    break
                except:
                    continue
        except Exception as e:
            print(f"Serial printing failed: {e}")
        """
        
        print(f"ESC/POS command ready for 80x297mm: {len(full_command)} bytes")
        print("Optimized for 40-character width thermal printing")
        
        # Specific settings for popular thermal printers with 80x297mm paper:
        # Epson TM-T88V: Use ESC/POS commands as above
        # Star TSP143III: Compatible with ESC/POS
        # Citizen CT-S310II: ESC/POS compatible
        
        return full_command
    
    def print_via_windows_printer(self):
        """Alternative printing method using Windows raw printing"""
        try:
            # This requires: pip install pywin32
            import win32print
            import win32api
            
            # Get default printer or specify thermal printer name
            printer_name = win32print.GetDefaultPrinter()
            
            # Open printer
            hPrinter = win32print.OpenPrinter(printer_name)
            
            try:
                # Start print job
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("POS Receipt", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                
                # Send receipt text directly
                receipt_bytes = self.receipt_text.encode('utf-8')
                win32print.WritePrinter(hPrinter, receipt_bytes)
                
                # End print job
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                
                QMessageBox.information(self, "Success", f"Receipt sent to {printer_name}")
                
            finally:
                win32print.ClosePrinter(hPrinter)
                
        except ImportError:
            QMessageBox.warning(self, "Missing Module", 
                              "Windows printing requires: pip install pywin32")
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Printing failed: {str(e)}")
    
    def save_receipt(self):
        """Save receipt to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Receipt - 80x297mm Format", f"receipt_80x297mm_{timestamp}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# Receipt formatted for 80x297mm thermal paper\n")
                    f.write("# Character width: 40 chars\n")
                    f.write("# Paper size: 80mm x 297mm\n")
                    f.write("# Generated by POS System\n")
                    f.write("#" + "="*38 + "\n\n")
                    f.write(self.receipt_text)
                QMessageBox.information(self, "Success", 
                                      f"Receipt saved for 80x297mm paper:\n{file_path}\n\n"
                                      "Format: 40 characters width\n"
                                      "Perfect for thermal printers")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save receipt: {str(e)}")
    
    def print_thermal(self):
        """Show thermal printing options for 80x297mm paper"""
        reply = QMessageBox.question(
            self, "Thermal Printer - 80x297mm Paper",
            "Choose thermal printing method for 80x297mm paper:\n\n"
            "📍 ESC/POS Commands: Direct thermal printer communication\n"
            "   (40 characters width, optimized spacing)\n\n"
            "🖨️ Windows Raw: Windows thermal printer drivers\n"
            "   (Automatic paper handling)\n\n"
            "❓ Which method would you like to use?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # ESC/POS method for 80x297mm
            def create_escpos_for_80x297mm():
                esc_pos_commands = []
                
                # Initialize printer
                esc_pos_commands.append(b'\x1b\x40')  # ESC @ (Initialize)
                
                # Set character set to UTF-8
                esc_pos_commands.append(b'\x1b\x74\x00')  # ESC t 0
                
                # Set line spacing for better readability on long paper
                esc_pos_commands.append(b'\x1b\x33\x20')  # ESC 3 (set line spacing to 32/180 inch)
                
                # Set font size (normal for 40 chars on 80mm)
                esc_pos_commands.append(b'\x1d\x21\x00')  # GS ! 0 (normal font)
                
                # Receipt text
                receipt_bytes = self.receipt_text.encode('utf-8', errors='ignore')
                esc_pos_commands.append(receipt_bytes)
                
                # Add extra line feeds for 297mm paper
                esc_pos_commands.append(b'\n\n\n\n')  # Extra spacing
                
                # Cut paper (full cut)
                esc_pos_commands.append(b'\x1d\x56\x42\x00')  # GS V B 0
                
                return b''.join(esc_pos_commands)
            
            commands = create_escpos_for_80x297mm()
            QMessageBox.information(self, "ESC/POS Ready - 80x297mm", 
                                  f"ESC/POS commands generated ({len(commands)} bytes)\n"
                                  "Optimized for 80x297mm thermal paper\n\n"
                                  "Features:\n"
                                  "• 40 character width for perfect 80mm fit\n"
                                  "• Proper line spacing for 297mm length\n"
                                  "• UTF-8 encoding support\n"
                                  "• Automatic paper cutting\n\n"
                                  "Compatible with:\n"
                                  "• Epson TM-T88IV/V\n"
                                  "• Star TSP143III\n"
                                  "• Citizen CT-S310II\n"
                                  "• Most ESC/POS thermal printers")
                
        elif reply == QMessageBox.StandardButton.No:
            # Windows raw printing method
            def windows_print_80x297mm():
                try:
                    import win32print
                    
                    # Get default printer
                    printer_name = win32print.GetDefaultPrinter()
                    
                    # Open printer
                    hPrinter = win32print.OpenPrinter(printer_name)
                    
                    try:
                        # Start print job with specific settings for thermal printer
                        hJob = win32print.StartDocPrinter(hPrinter, 1, ("POS Receipt 80x297mm", None, "RAW"))
                        win32print.StartPagePrinter(hPrinter)
                        
                        # Send receipt optimized for 80x297mm
                        receipt_bytes = self.receipt_text.encode('utf-8')
                        win32print.WritePrinter(hPrinter, receipt_bytes)
                        
                        # End print job
                        win32print.EndPagePrinter(hPrinter)
                        win32print.EndDocPrinter(hPrinter)
                        
                        QMessageBox.information(self, "Success", 
                                              f"Receipt sent to {printer_name}\n"
                                              "Format: 80x297mm thermal paper\n"
                                              "Width: 40 characters")
                        
                    finally:
                        win32print.ClosePrinter(hPrinter)
                        
                except ImportError:
                    QMessageBox.warning(self, "Missing Module", 
                                      "Windows printing requires:\n"
                                      "pip install pywin32\n\n"
                                      "Alternative: Use ESC/POS method")
                except Exception as e:
                    QMessageBox.critical(self, "Print Error", 
                                        f"Printing failed: {str(e)}\n\n"
                                        "Try ESC/POS method instead")
            
            windows_print_80x297mm()
        # Cancel does nothing

class POSMainWindow(QMainWindow):
    """Main POS Window"""
    def __init__(self):
        super().__init__()
        self.current_order = []
        self.order_items = []  
        self.subtotal = 0.0
        self.discount_amount = 0.0
        self.discount_percentage = 0.0
        self.tax_rate = 0.15  
        self.current_customer = None  # Add this line
        self.tax_enabled = True
        self.current_payment = 0.0
        self.current_quantity_input = ""
        
        # Add pagination variables
        self.current_product_page = 0
        self.products_per_page = 16  # 4x4 grid
        self.current_products_list = []
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize barcode buffer for keyboard wedge scanners
        self.barcode_buffer = ""
        self.barcode_timer = QTimer()
        self.barcode_timer.timeout.connect(self.process_barcode_buffer)
        self.barcode_timer.setSingleShot(True)
        
        self.init_ui()
        self.setup_menu()
        self.load_products_from_database()
        
    def init_ui(self):
        self.setWindowTitle("POS System - Wholesale Dealer")
        self.setMinimumSize(1024, 768)
        self.resize(1024, 768)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with margins
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        central_widget.setLayout(main_layout)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Product selection
        left_panel = self.create_product_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Order and controls
        right_panel = self.create_order_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions for 1024x768 (considering menu bar ~30px and margins)
        # Left: ~580px, Right: ~420px for better balance
        splitter.setSizes([580, 420])
        
        # Set main window styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
        """)
        
        # Add status bar
        status_message = "Ready - Scan barcode or search for products"
        if REPORTLAB_AVAILABLE:
            status_message += " | PDF receipts enabled"
        else:
            status_message += " | Install ReportLab for PDF receipts: pip install reportlab"
            
        self.statusBar().showMessage(status_message)
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                padding: 5px;
            }
        """)
    
    def setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        
        new_order_action = QAction('&New Order', self)
        new_order_action.setShortcut('Ctrl+N')
        new_order_action.setStatusTip('Start a new order')
        new_order_action.triggered.connect(self.new_order)
        file_menu.addAction(new_order_action)
        
        # Quick payment action
        quick_payment_action = QAction('&Quick Payment', self)
        quick_payment_action.setShortcut('F12')
        quick_payment_action.setStatusTip('Process payment quickly')
        quick_payment_action.triggered.connect(self.process_payment)
        file_menu.addAction(quick_payment_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit the application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Products Menu
        products_menu = menubar.addMenu('&Products')
        
        add_product_action = QAction('&Add Product', self)
        add_product_action.setShortcut('Ctrl+P')
        add_product_action.setStatusTip('Add new product')
        add_product_action.triggered.connect(self.open_product_management)
        products_menu.addAction(add_product_action)
        
        manage_categories_action = QAction('&Manage Categories', self)
        manage_categories_action.triggered.connect(self.open_category_management)
        products_menu.addAction(manage_categories_action)
        
        # Inventory Menu
        inventory_menu = menubar.addMenu('&Inventory')
        
        view_inventory_action = QAction('&View Inventory', self)
        view_inventory_action.triggered.connect(self.open_inventory_management)
        inventory_menu.addAction(view_inventory_action)
        
        stock_adjustment_action = QAction('&Stock Adjustment', self)
        stock_adjustment_action.triggered.connect(self.open_stock_adjustment)
        inventory_menu.addAction(stock_adjustment_action)
        
        # Customers Menu
        customers_menu = menubar.addMenu('&Customers')
        
        manage_customers_action = QAction('&Manage Customers', self)
        manage_customers_action.triggered.connect(self.open_customer_management)
        customers_menu.addAction(manage_customers_action)
        
        # Vendors Menu
        vendors_menu = menubar.addMenu('&Vendors')
        
        manage_vendors_action = QAction('&Manage Vendors', self)
        manage_vendors_action.triggered.connect(self.open_vendor_management)
        vendors_menu.addAction(manage_vendors_action)
        
        # Reports Menu
        reports_menu = menubar.addMenu('&Reports')
        
        sales_report_action = QAction('&Sales Report', self)
        sales_report_action.triggered.connect(self.open_sales_report)
        reports_menu.addAction(sales_report_action)
        
        inventory_report_action = QAction('&Inventory Report', self)
        inventory_report_action.triggered.connect(self.open_inventory_report)
        reports_menu.addAction(inventory_report_action)
        
        customer_report_action = QAction('&Customer Report', self)
        customer_report_action.triggered.connect(self.open_customer_report)
        reports_menu.addAction(customer_report_action)
        
        # POS Menu
        pos_menu = menubar.addMenu('P&OS')
        
        # Barcode scan action
        barcode_action = QAction('&Scan Barcode', self)
        barcode_action.setShortcut('F1')
        barcode_action.setStatusTip('Manual barcode entry')
        barcode_action.triggered.connect(self.manual_barcode_entry)
        pos_menu.addAction(barcode_action)
        
        # Search focus action
        search_action = QAction('&Search Products', self)
        search_action.setShortcut('Ctrl+F')
        search_action.setStatusTip('Focus on search field')
        search_action.triggered.connect(lambda: self.search_input.setFocus())
        pos_menu.addAction(search_action)
        
        hold_order_action = QAction('&Hold Order', self)
        hold_order_action.setShortcut('F2')
        hold_order_action.triggered.connect(self.hold_order)
        pos_menu.addAction(hold_order_action)
        
        recall_order_action = QAction('&Recall Order', self)
        recall_order_action.setShortcut('F3')
        recall_order_action.triggered.connect(self.recall_order)
        pos_menu.addAction(recall_order_action)
        
        pos_menu.addSeparator()
        
        settings_action = QAction('&Settings', self)
        settings_action.triggered.connect(self.open_settings)
        pos_menu.addAction(settings_action)
        
        # Help Menu
        help_menu = menubar.addMenu('&Help')
        
        # ReportLab installation help
        reportlab_action = QAction('Install &ReportLab for PDF Receipts', self)
        reportlab_action.triggered.connect(self.show_reportlab_help)
        help_menu.addAction(reportlab_action)
        
        help_menu.addSeparator()
        
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_product_panel(self):
        """Create the left panel with optimized layout and space management"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Search bar - compact
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        search_label = QLabel("Search:")
        search_label.setMinimumWidth(50)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Product name or barcode...")
        self.search_input.textChanged.connect(self.search_products)
        self.search_input.returnPressed.connect(self.on_search_enter)
        
        # Compact barcode button
        barcode_btn = QPushButton("Scan")
        barcode_btn.setMaximumWidth(60)
        barcode_btn.clicked.connect(self.manual_barcode_entry)
        barcode_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 5px;
                border: none;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
        """)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(barcode_btn)
        layout.addLayout(search_layout)
        
        # Product grid area with fixed height for 4x4 grid
        scroll_area = QScrollArea()
        scroll_area.setMaximumHeight(360)  # Fixed height for 4 rows of products (4 * 90px)
        scroll_area.setMinimumHeight(360)
        scroll_widget = QWidget()
        
        # Create 4x4 grid layout
        self.product_grid = QGridLayout()
        self.product_grid.setSpacing(5)
        
        # Set fixed row and column sizes for consistent 4x4 grid
        for row in range(4):
            self.product_grid.setRowMinimumHeight(row, 85)
            self.product_grid.setRowStretch(row, 0)
        
        for col in range(4):
            self.product_grid.setColumnMinimumWidth(col, 120)
            self.product_grid.setColumnStretch(col, 1)
        
        scroll_widget.setLayout(self.product_grid)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(scroll_area)
        
        # Navigation buttons - compact
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)
        
        prior_btn = QPushButton("◄ Prior")
        prior_btn.setMaximumHeight(35)
        prior_btn.clicked.connect(self.previous_products_page)
        prior_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                border: 2px solid #333;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #FFC107; }
        """)
        
        # Page indicator
        self.page_label = QLabel("Page 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; color: #333;")
        
        next_btn = QPushButton("Next ►")
        next_btn.setMaximumHeight(35)
        next_btn.clicked.connect(self.next_products_page)
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                border: 2px solid #333;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #FFC107; }
        """)
        
        nav_layout.addWidget(prior_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)
        
        # Category buttons - limited to 2x5 grid with fixed height
        category_frame = QFrame()
        category_frame.setMaximumHeight(180)  # Fixed height for 2 rows of categories
        category_frame.setMinimumHeight(180)
        category_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        category_frame.setStyleSheet("QFrame { border: 1px solid #ccc; background-color: #f9f9f9; }")
        
        category_layout = QGridLayout()
        category_layout.setSpacing(5)
        category_layout.setContentsMargins(5, 5, 5, 5)
        
        # Set fixed dimensions for category grid (2 rows x 5 columns)
        for row in range(2):
            category_layout.setRowMinimumHeight(row, 80)
            category_layout.setRowStretch(row, 0)
        
        for col in range(5):
            category_layout.setColumnMinimumWidth(col, 100)
            category_layout.setColumnStretch(col, 1)
        
        self.load_category_buttons(category_layout)
        category_frame.setLayout(category_layout)
        layout.addWidget(category_frame)
        
        # Function buttons - more compact grid
        func_frame = QFrame()
        func_frame.setMaximumHeight(120)  # Fixed height for function buttons
        func_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        func_frame.setStyleSheet("QFrame { border: 1px solid #ccc; background-color: #f9f9f9; }")
        
        func_layout = QGridLayout()
        func_layout.setSpacing(3)
        func_layout.setContentsMargins(5, 5, 5, 5)
        
        function_buttons = [
            ("Discount %", self.apply_percentage_discount), ("Customer", self.select_customer), 
            ("Discount Rs", self.apply_fixed_discount), ("Tax Toggle", self.toggle_tax), 
            ("Comments", self.add_comments), ("Sub Total", self.show_subtotal),
            ("Refund", self.process_refund), ("Duplicate", self.duplicate_order), 
            ("Bill Cancel", self.cancel_bill), ("Void Last", self.void_last_item)
        ]
        
        for i, (text, func) in enumerate(function_buttons):
            btn = QPushButton(text)
            btn.setMaximumHeight(25)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90E2;
                    border: 1px solid #333;
                    border-radius: 3px;
                    color: white;
                    font-weight: bold;
                    font-size: 9px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #357ABD;
                }
            """)
            btn.clicked.connect(func)
            func_layout.addWidget(btn, i // 5, i % 5)
        
        func_frame.setLayout(func_layout)
        layout.addWidget(func_frame)
        
        panel.setLayout(layout)
        return panel

    # Add pagination methods
    def previous_products_page(self):
        """Go to previous products page"""
        if self.current_product_page > 0:
            self.current_product_page -= 1
            self.update_products_page()

    def next_products_page(self):
        """Go to next products page"""
        max_pages = (len(self.current_products_list) - 1) // self.products_per_page
        if self.current_product_page < max_pages:
            self.current_product_page += 1
            self.update_products_page()

    def update_products_page(self):
        """Update the product display for current page"""
        start_idx = self.current_product_page * self.products_per_page
        end_idx = start_idx + self.products_per_page
        page_products = self.current_products_list[start_idx:end_idx]
        
        self.display_products(page_products)
        
        # Update page label
        total_pages = max(1, (len(self.current_products_list) + self.products_per_page - 1) // self.products_per_page)
        self.page_label.setText(f"Page {self.current_product_page + 1}/{total_pages}")

    def load_products_from_database(self):
        """Load products from database with pagination support"""
        try:
            products = self.db_manager.get_all_products()
            self.current_products_list = products
            self.current_product_page = 0
            self.update_products_page()
        except Exception as e:
            print(f"Error loading products: {e}")
            self.current_products_list = []
            self.display_no_products_message()

    def search_products(self, text):
        """Search products with pagination support"""
        if not text.strip():
            self.load_products_from_database()
            return
        
        try:
            products = self.db_manager.search_products(text.strip())
            self.current_products_list = products
            self.current_product_page = 0
            self.update_products_page()
        except Exception as e:
            print(f"Error searching products: {e}")
            self.current_products_list = []
            self.display_no_products_message()

    def load_category_products(self, category_name):
        """Load products from a specific category with pagination support"""
        try:
            if category_name == "All" or category_name == "All Products":
                products = self.db_manager.get_all_products()
            else:
                products = self.db_manager.get_products_by_category(category_name)
            
            self.current_products_list = products
            self.current_product_page = 0
            self.update_products_page()
            
            # Update status bar to show current category
            self.statusBar().showMessage(f"Category: {category_name} - {len(products)} products found", 3000)
            
        except Exception as e:
            print(f"Error loading category products: {e}")
            self.current_products_list = []
            self.display_no_products_message()
            self.statusBar().showMessage(f"Error loading category: {category_name}", 3000)
    
    def load_category_buttons(self, category_layout):
        """Load category buttons in a limited 2x5 grid (10 categories max visible)"""
        try:
            categories = self.db_manager.get_categories()
            
            # Always add "All Products" button first
            all_btn = ProductButton("All Products", "#4A90E2")
            all_btn.clicked.connect(lambda: self.load_category_products("All"))
            category_layout.addWidget(all_btn, 0, 0)
            
            if not categories:
                return
            
            # Limit to 9 categories (plus "All Products" = 10 total in 2x5 grid)
            categories_to_show = categories[:9]
            
            # Add categories from database in 2x5 grid
            for i, (cat_id, cat_name, color_code) in enumerate(categories_to_show):
                btn = ProductButton(cat_name, color_code or "#4A90E2")
                btn.clicked.connect(lambda checked, name=cat_name: self.load_category_products(name))
                
                # Calculate position: 5 columns, 2 rows
                # Position 0 is taken by "All Products", so start from position 1
                pos = i + 1
                row = pos // 5
                col = pos % 5
                
                category_layout.addWidget(btn, row, col)
            
            # If there are more than 9 categories, add a "More..." button
            if len(categories) > 9:
                more_btn = ProductButton("More...", "#666666")
                more_btn.clicked.connect(self.show_more_categories)
                # Place at position 9 (last slot in 2x5 grid)
                category_layout.addWidget(more_btn, 1, 4)
                
        except Exception as e:
            print(f"Error loading categories: {e}")
            # Fallback button
            all_btn = ProductButton("All Products", "#4A90E2")
            all_btn.clicked.connect(lambda: self.load_category_products("All"))
            category_layout.addWidget(all_btn, 0, 0)


    def show_more_categories(self):
        """Show a dialog with all categories for selection"""
        try:
            categories = self.db_manager.get_categories()
            if not categories:
                return
            
            # Create category selection dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Category")
            dialog.setMinimumSize(400, 300)
            
            layout = QVBoxLayout()
            
            # Search box for categories
            search_box = QLineEdit()
            search_box.setPlaceholderText("Search categories...")
            layout.addWidget(search_box)
            
            # Category list
            category_list = QListWidget()
            category_list.addItem("All Products")
            
            for cat_id, cat_name, color_code in categories:
                category_list.addItem(cat_name)
            
            # Filter categories based on search
            def filter_categories():
                search_text = search_box.text().lower()
                for i in range(category_list.count()):
                    item = category_list.item(i)
                    item.setHidden(search_text not in item.text().lower())
            
            search_box.textChanged.connect(filter_categories)
            
            # Double-click to select
            def on_category_selected():
                current_item = category_list.currentItem()
                if current_item:
                    category_name = current_item.text()
                    self.load_category_products(category_name)
                    dialog.close()
            
            category_list.itemDoubleClicked.connect(on_category_selected)
            layout.addWidget(category_list)
            
            # Buttons
            button_layout = QHBoxLayout()
            select_btn = QPushButton("Select")
            select_btn.clicked.connect(on_category_selected)
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.close)
            
            button_layout.addWidget(select_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load categories: {str(e)}")
            
    def load_category_products(self, category_name):
        """Load products from a specific category"""
        try:
            if category_name == "All" or category_name == "All Products":
                # Load all products
                products = self.db_manager.get_all_products()
            else:
                # Load products from specific category
                products = self.db_manager.get_products_by_category(category_name)
            
            self.display_products(products[:20])  # Show first 20 products
            
            # Update status bar to show current category
            self.statusBar().showMessage(f"Category: {category_name} - {len(products)} products found", 3000)
            
        except Exception as e:
            print(f"Error loading category products: {e}")
            self.display_no_products_message()
            self.statusBar().showMessage(f"Error loading category: {category_name}", 3000)
    def create_order_panel(self):
        """Create the right panel with order display and controls"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Order table - flexible sizing
        self.order_table = OrderTable()
        self.order_table.itemDoubleClicked.connect(self.edit_order_item)
        layout.addWidget(self.order_table, 1)  # Give it stretch factor of 1
        
        # Keypad and totals - fixed sizing
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(5)
        
        # Numeric keypad - responsive sizing
        self.keypad = NumericKeypad()
        self.keypad.number_clicked.connect(self.handle_keypad_input)
        self.keypad.setMaximumWidth(250)  # Limit max width but allow scaling
        self.keypad.setMinimumWidth(200)  # Ensure minimum usability
        
        # Additional keypad buttons
        keypad_layout = QVBoxLayout()
        keypad_layout.addWidget(self.keypad)
        
        # Special buttons
        special_layout = QHBoxLayout()
        special_layout.setSpacing(5)
        
        payment_btn = QPushButton("Payment")
        payment_btn.setMinimumSize(70, 50)
        payment_btn.setMaximumSize(100, 50)
        payment_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                border: 2px solid #333;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
        """)
        payment_btn.clicked.connect(self.process_payment)
        
        qty_btn = QPushButton("F11\nQty")
        qty_btn.setMinimumSize(50, 50)
        qty_btn.setMaximumSize(70, 50)
        qty_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                border: 2px solid #333;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        qty_btn.clicked.connect(self.change_quantity)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setMinimumSize(50, 50)
        remove_btn.setMaximumSize(80, 50)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC143C;
                border: 2px solid #333;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        remove_btn.clicked.connect(self.remove_selected_item)
        
        special_layout.addWidget(payment_btn)
        special_layout.addWidget(qty_btn)
        special_layout.addWidget(remove_btn)
        keypad_layout.addLayout(special_layout)
        
        bottom_layout.addLayout(keypad_layout)
        
        # Totals panel
        totals_layout = QVBoxLayout()
        totals_layout.setSpacing(5)
        
        # Amount display
        self.amount_display = QLineEdit("0.00")
        self.amount_display.setStyleSheet("""
            QLineEdit {
                background-color: #2E8B57;
                color: white;
                font-size: 22px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border: 2px solid #333;
                max-height: 60px;
            }
        """)
        self.amount_display.setReadOnly(True)
        totals_layout.addWidget(self.amount_display)
        
        # Till and other info
        till_layout = QHBoxLayout()
        till_label = QLabel("Terminal: 001")
        till_layout.addWidget(till_label)
        
        # Tax checkbox
        self.tax_checkbox = QCheckBox("Tax")
        self.tax_checkbox.setChecked(True)
        self.tax_checkbox.stateChanged.connect(self.toggle_tax_checkbox)
        till_layout.addWidget(self.tax_checkbox)
        
        totals_layout.addLayout(till_layout)
        
        # Subtotal
        subtotal_layout = QHBoxLayout()
        subtotal_layout.addWidget(QLabel("SUBTOTAL:"))
        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet("""
            QLabel {
                background-color: #4A90E2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
                border: 1px solid #333;
                min-width: 80px;
            }
        """)
        subtotal_layout.addWidget(self.subtotal_label)
        totals_layout.addLayout(subtotal_layout)
        
        # Discount
        discount_layout = QHBoxLayout()
        discount_layout.addWidget(QLabel("DISCOUNT:"))
        self.discount_label = QLabel("0.00")
        self.discount_label.setStyleSheet("""
            QLabel {
                background-color: #FF6B6B;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
                border: 1px solid #333;
                min-width: 80px;
            }
        """)
        discount_layout.addWidget(self.discount_label)
        totals_layout.addLayout(discount_layout)
        
        # Tax
        tax_layout = QHBoxLayout()
        tax_layout.addWidget(QLabel("TAX:"))
        self.tax_label = QLabel("0.00")
        self.tax_label.setStyleSheet("""
            QLabel {
                background-color: #FFA500;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
                border: 1px solid #333;
                min-width: 80px;
            }
        """)
        tax_layout.addWidget(self.tax_label)
        totals_layout.addLayout(tax_layout)
        
        # Total
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("TOTAL:"))
        self.total_label = QLabel("0.00")
        self.total_label.setStyleSheet("""
            QLabel {
                background-color: #2E8B57;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                text-align: center;
                border: 2px solid #333;
                min-width: 80px;
            }
        """)
        total_layout.addWidget(self.total_label)
        totals_layout.addLayout(total_layout)
        
        # Payment
        payment_layout = QHBoxLayout()
        payment_layout.addWidget(QLabel("PAYMENT:"))
        self.payment_label = QLabel("0.00")
        self.payment_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
                border: 1px solid #333;
                min-width: 80px;
            }
        """)
        payment_layout.addWidget(self.payment_label)
        totals_layout.addLayout(payment_layout)
        
        # Change
        change_layout = QHBoxLayout()
        change_layout.addWidget(QLabel("CHANGE:"))
        self.change_label = QLabel("0.00")
        self.change_label.setStyleSheet("""
            QLabel {
                background-color: #8B0000;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
                border: 1px solid #333;
                min-width: 80px;
            }
        """)
        change_layout.addWidget(self.change_label)
        totals_layout.addLayout(change_layout)
        
        bottom_layout.addLayout(totals_layout)
        layout.addLayout(bottom_layout, 0)  # Don't stretch the bottom section
        
        panel.setLayout(layout)
        return panel
    
    def load_products_from_database(self):
        """Load products from database into the grid"""
        try:
            products = self.db_manager.get_all_products()
            self.display_products(products[:20])  # Show first 20 products
        except Exception as e:
            print(f"Error loading products: {e}")
            self.display_no_products_message()
    
    def display_products(self, products):
        """Display products in a fixed 4x4 grid (16 products per page)"""
        # Clear existing products
        for i in reversed(range(self.product_grid.count())): 
            widget = self.product_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        if not products:
            self.display_no_products_message()
            return
        
        # Display products in exactly 4x4 grid (16 products)
        products_to_show = products[:16]  # Limit to 16 products for 4x4 grid
        
        for i, product in enumerate(products_to_show):
            product_data = {
                'id': product[0],
                'name': product[1],
                'barcode': product[2],
                'sale_price': product[5],
                'category': product[6] if len(product) > 6 and product[6] else 'General'
            }
            
            # Determine color based on category or use default
            color = "#FF6B6B"  # Default color
            if len(product) > 6 and product[6]:  # Has category
                color = self.get_category_color(product[6])
            
            btn = ProductButton(product[1], color, product_data)
            btn.clicked.connect(lambda checked, data=product_data: self.add_product_to_order(data))
            
            # Fixed 4x4 grid layout
            row = i // 4  # 4 columns per row
            col = i % 4
            self.product_grid.addWidget(btn, row, col)
        
        # Fill empty slots with placeholder buttons if less than 16 products
        for i in range(len(products_to_show), 16):
            placeholder = QPushButton("Empty Slot")
            placeholder.setMinimumSize(120, 80)
            placeholder.setMaximumSize(200, 120)
            placeholder.setEnabled(False)
            placeholder.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    color: #999;
                    font-style: italic;
                    font-size: 10px;
                }
            """)
            
            row = i // 4
            col = i % 4
            self.product_grid.addWidget(placeholder, row, col)
    
    def display_no_products_message(self):
        """Display message when no products are available"""
        empty_label = QLabel("No products available.\nUse Products menu to add products.")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                padding: 20px;
                border: 2px dashed #ccc;
                border-radius: 10px;
            }
        """)
        self.product_grid.addWidget(empty_label, 0, 0, 1, 5)
    
    def get_category_color(self, category_name):
        """Get color for category (simplified version)"""
        # Simple hash-based color assignment
        colors = ["#FF6B6B", "#4ECDC4", "#04C2ED", "#00BC64", "#FDC716", "#FF53FF", "#FF8147", "#4E41FF"]
        return colors[hash(category_name) % len(colors)]
    
    def search_products(self, text):
        """Search products by name or barcode"""
        if not text.strip():
            self.load_products_from_database()
            return
        
        try:
            # Search in database
            products = self.db_manager.search_products(text.strip())
            self.display_products(products)
        except Exception as e:
            print(f"Error searching products: {e}")
            self.display_no_products_message()
    
    def on_search_enter(self):
        """Handle Enter key in search field - try to add product directly"""
        search_text = self.search_input.text().strip()
        if not search_text:
            return
        
        # Try to find exact match by barcode first
        try:
            product = self.db_manager.get_product_by_barcode(search_text)
            if product:
                product_data = {
                    'id': product[0],
                    'name': product[1],
                    'barcode': product[2],
                    'sale_price': product[8],  # sale_price is at index 8 in product tuple
                    'category': 'General'
                }
                self.add_product_to_order(product_data)
                self.search_input.clear()
                return
        except Exception as e:
            print(f"Error searching by barcode: {e}")
        
        # If no exact barcode match, show search results
        self.search_products(search_text)
    
    def manual_barcode_entry(self):
        """Manual barcode entry dialog"""
        barcode, ok = QInputDialog.getText(
            self, "Barcode Entry", 
            "Enter or scan barcode:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and barcode.strip():
            self.process_barcode(barcode.strip())
    
    def process_barcode(self, barcode):
        """Process scanned or entered barcode"""
        try:
            product = self.db_manager.get_product_by_barcode(barcode)
            if product:
                product_data = {
                    'id': product[0],
                    'name': product[1],
                    'barcode': product[2],
                    'sale_price': product[8],  # sale_price is at index 8
                    'category': 'General'
                }
                self.add_product_to_order(product_data)
                
                # Show success message briefly
                self.statusBar().showMessage(f"Added: {product[1]}", 2000)
            else:
                # Product not found
                QMessageBox.warning(self, "Product Not Found", 
                                  f"No product found with barcode: {barcode}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error processing barcode: {str(e)}")
    
    def process_barcode_buffer(self):
        """Process accumulated barcode data from keyboard wedge scanner"""
        if self.barcode_buffer:
            self.process_barcode(self.barcode_buffer)
            self.barcode_buffer = ""
    
    def keyPressEvent(self, event):
        """Handle keyboard input for barcode scanners"""
        # Handle barcode scanner input (keyboard wedge mode)
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.barcode_buffer:
                self.process_barcode_buffer()
            else:
                super().keyPressEvent(event)
        elif event.text().isdigit():
            # Accumulate digits for barcode
            self.barcode_buffer += event.text()
            self.barcode_timer.start(500)  # 500ms timeout for barcode completion
        else:
            # Reset buffer for non-digit keys
            self.barcode_buffer = ""
            super().keyPressEvent(event)
    
    def add_product_to_order(self, product_data):
        """Add selected product to the order"""
        if not product_data:
            return
            
        # Check if product already exists in order
        for i, item in enumerate(self.order_items):
            if item['barcode'] == product_data.get('barcode', ''):
                # Increase quantity
                item['quantity'] += 1
                item['total'] = item['quantity'] * item['price']
                self.update_order_display()
                self.calculate_totals()
                return
        
        # Add new item
        order_item = {
            'description': product_data.get('name', 'Unknown Product'),
            'quantity': 1,
            'price': float(product_data.get('sale_price', 0)),
            'total': float(product_data.get('sale_price', 0)),
            'barcode': product_data.get('barcode', ''),
            'product_id': product_data.get('id', 0)
        }
        
        self.order_items.append(order_item)
        self.update_order_display()
        self.calculate_totals()
    
    def update_order_display(self):
        """Update the order table display"""
        self.order_table.setRowCount(len(self.order_items))
        
        for i, item in enumerate(self.order_items):
            self.order_table.setItem(i, 0, QTableWidgetItem(item['description']))
            self.order_table.setItem(i, 1, QTableWidgetItem(f"{item['quantity']:.2f}"))
            self.order_table.setItem(i, 2, QTableWidgetItem(f"{item['price']:.2f}"))
            self.order_table.setItem(i, 3, QTableWidgetItem(f"{item['total']:.2f}"))
            
            # Add remove button
            remove_btn = QPushButton("X")
            remove_btn.setMaximumSize(30, 30)
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DC143C;
                    color: white;
                    border: 1px solid #333;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            remove_btn.clicked.connect(lambda checked, row=i: self.remove_order_item(row))
            self.order_table.setCellWidget(i, 4, remove_btn)
            
            self.order_table.setItem(i, 5, QTableWidgetItem(item['barcode']))
    
    def remove_order_item(self, row):
        """Remove item from order"""
        if 0 <= row < len(self.order_items):
            del self.order_items[row]
            self.update_order_display()
            self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate order totals"""
        self.subtotal = sum(item['total'] for item in self.order_items)
        
        # Apply discount
        if self.discount_percentage > 0:
            self.discount_amount = (self.subtotal * self.discount_percentage) / 100
        
        subtotal_after_discount = self.subtotal - self.discount_amount
        
        # Calculate tax
        tax_amount = 0
        if self.tax_enabled:
            tax_amount = (subtotal_after_discount * self.tax_rate)
        
        total = subtotal_after_discount + tax_amount
        change = self.current_payment - total if self.current_payment > total else 0
        
        # Update display
        self.subtotal_label.setText(f"{self.subtotal:.2f}")
        self.discount_label.setText(f"{self.discount_amount:.2f}")
        self.tax_label.setText(f"{tax_amount:.2f}")
        self.total_label.setText(f"{total:.2f}")
        self.amount_display.setText(f"{total:.2f}")
        self.payment_label.setText(f"{self.current_payment:.2f}")
        self.change_label.setText(f"{change:.2f}")
    
    def handle_keypad_input(self, value):
        """Handle numeric keypad input"""
        if value == "CLR":
            self.current_quantity_input = ""
            self.amount_display.setText("0.00")
        else:
            self.current_quantity_input += value
            try:
                amount = float(self.current_quantity_input)
                self.amount_display.setText(f"{amount:.2f}")
            except ValueError:
                pass
    
    def create_receipt(self):
        """Create professional PDF receipt using ReportLab for 80x297mm paper with customer info"""
        if not REPORTLAB_AVAILABLE:
            # Fallback to text receipt if ReportLab not available
            return self.create_text_receipt()
        
        if not self.order_items:
            return None
        
        # Receipt configuration for 80x297mm paper
        receipt_width = 80 * mm  # 80mm width
        base_height = 130 * mm   # Increased base height for customer info
        item_height = 5 * mm     # Height per item
        
        # Calculate dynamic height based on items (max 297mm)
        calculated_height = base_height + (len(self.order_items) * item_height)
        receipt_height = min(calculated_height, 297 * mm)  # Cap at 297mm
        
        # Create temporary PDF file
        receipt_file = os.path.join(tempfile.gettempdir(), f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        try:
            c = canvas.Canvas(receipt_file, pagesize=(receipt_width, receipt_height))
            y_position = receipt_height - 10 * mm  # Start from top with margin
            
            # Define compact column positions for 80mm width
            left_margin = 1 * mm
            right_margin = 1 * mm
            usable_width = receipt_width - left_margin - right_margin  # 78mm usable
            
            # Store Header
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(receipt_width / 2, y_position, "WHOLESALE DEALER POS")
            y_position -= 4 * mm
            
            c.setFont("Helvetica", 9)
            c.drawCentredString(receipt_width / 2, y_position, "Your Business Name")
            y_position -= 3 * mm
            c.drawCentredString(receipt_width / 2, y_position, "123 Business Street")
            y_position -= 3 * mm
            c.drawCentredString(receipt_width / 2, y_position, "City, State 12345")
            y_position -= 3 * mm
            c.drawCentredString(receipt_width / 2, y_position, "Phone: (555) 123-4567")
            y_position -= 5 * mm
            
            # Separator line
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 4 * mm
            
            # Receipt Details
            receipt_number = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"
            c.setFont("Helvetica", 8)
            c.drawString(left_margin, y_position, f"Receipt #: {receipt_number}")
            y_position -= 3 * mm
            c.drawString(left_margin, y_position, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y_position -= 3 * mm
            c.drawString(left_margin, y_position, "Cashier: POS User")
            y_position -= 3 * mm
            
            # Customer information if available
            if self.current_customer:
                c.drawString(left_margin, y_position, f"Customer: {self.current_customer['name']}")
                y_position -= 3 * mm
            
            y_position -= 1 * mm
            
            # Items Header
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 3 * mm
            
            c.setFont("Helvetica-Bold", 7)
            c.drawString(left_margin, y_position, "Item")
            c.drawString(left_margin + 45 * mm, y_position, "Qty")
            c.drawString(left_margin + 55 * mm, y_position, "Price")
            c.drawString(left_margin + 67 * mm, y_position, "Tot")
            y_position -= 3 * mm
            
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 3 * mm
            
            # Items with compact alignment
            c.setFont("Helvetica", 6)
            for item in self.order_items:
                # Item name (truncate to fit in 45mm ≈ 18 chars at 6pt)
                item_name = item['description']
                if len(item_name) > 18:
                    item_name = item_name[:15] + "..."
                
                c.drawString(left_margin, y_position, item_name)
                
                # Quantity
                qty_text = f"{item['quantity']:.1f}"
                c.drawRightString(left_margin + 54 * mm, y_position, qty_text)
                
                # Price
                price_text = f"{item['price']:.0f}"
                c.drawRightString(left_margin + 66 * mm, y_position, price_text)
                
                # Total
                total_text = f"{item['total']:.0f}"
                c.drawRightString(left_margin + 77 * mm, y_position, total_text)
                
                y_position -= 3.5 * mm
                
                # Check if we're running out of space
                if y_position < 35 * mm:
                    break
            
            # Totals Section
            y_position -= 2 * mm
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 4 * mm
            
            # Calculate totals
            if self.tax_enabled:
                tax_amount = (self.subtotal - self.discount_amount) * self.tax_rate
            else:
                tax_amount = 0
            
            total = self.subtotal - self.discount_amount + tax_amount
            
            c.setFont("Helvetica", 8)
            
            # Subtotal
            c.drawString(left_margin, y_position, "Subtotal:")
            c.drawRightString(receipt_width - right_margin, y_position, f"{self.subtotal:.2f}")
            y_position -= 3 * mm
            
            # Discount (if applicable)
            if self.discount_amount > 0:
                c.drawString(left_margin, y_position, "Discount:")
                c.drawRightString(receipt_width - right_margin, y_position, f"-{self.discount_amount:.2f}")
                y_position -= 3 * mm
            
            # Tax (if applicable)
            if self.tax_enabled and tax_amount > 0:
                c.drawString(left_margin, y_position, f"Tax ({int(self.tax_rate * 100)}%):")
                c.drawRightString(receipt_width - right_margin, y_position, f"{tax_amount:.2f}")
                y_position -= 3 * mm
            
            # Total
            y_position -= 1 * mm
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 4 * mm
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left_margin, y_position, "TOTAL:")
            c.drawRightString(receipt_width - right_margin, y_position, f"{total:.2f}")
            y_position -= 5 * mm
            
            # Payment & Change
            c.setFont("Helvetica", 8)
            c.drawString(left_margin, y_position, "Payment:")
            c.drawRightString(receipt_width - right_margin, y_position, f"{self.current_payment:.2f}")
            y_position -= 3 * mm
            
            change = self.current_payment - total if self.current_payment > total else 0
            c.drawString(left_margin, y_position, "Change:")
            c.drawRightString(receipt_width - right_margin, y_position, f"{change:.2f}")
            y_position -= 5 * mm
            
            # Footer
            c.line(left_margin, y_position, receipt_width - right_margin, y_position)
            y_position -= 4 * mm
            
            c.setFont("Helvetica", 8)
            c.drawCentredString(receipt_width / 2, y_position, "Thank you for your business!")
            y_position -= 3 * mm
            
            if self.current_customer:
                c.drawCentredString(receipt_width / 2, y_position, f"Thank you, {self.current_customer['name']}!")
                y_position -= 3 * mm
            
            c.drawCentredString(receipt_width / 2, y_position, "Please come again!")
            y_position -= 4 * mm
            
            c.setFont("Helvetica", 7)
            c.drawCentredString(receipt_width / 2, y_position, "Return Policy: 30 days")
            y_position -= 2.5 * mm
            c.drawCentredString(receipt_width / 2, y_position, "Keep this receipt for returns")
            
            # Save PDF
            c.save()
            
            # Store receipt data for database
            self.last_receipt_data = {
                'receipt_number': receipt_number,
                'subtotal': self.subtotal,
                'discount_amount': self.discount_amount,
                'tax_amount': tax_amount,
                'total_amount': total,
                'payment_amount': self.current_payment,
                'change_amount': change,
                'sale_date': datetime.now().isoformat(),
                'receipt_file': receipt_file
            }
            
            # Verify the file was created successfully
            if os.path.exists(receipt_file) and os.path.getsize(receipt_file) > 0:
                return receipt_file
            else:
                print("PDF creation failed - file not created or empty")
                return self.create_text_receipt()
                
        except Exception as e:
            print(f"Error creating PDF receipt: {e}")
            # Return text receipt as fallback
            return self.create_text_receipt()

    # Update the create_text_receipt method to include customer info
    def create_text_receipt(self):
        """Compact text receipt with customer info for 80mm thermal paper"""
        receipt_lines = []
        
        # Header (32 characters wide for 80mm paper)
        receipt_lines.append("================================")
        receipt_lines.append("     WHOLESALE DEALER POS")
        receipt_lines.append("      Your Business Name")
        receipt_lines.append("    123 Business Street")
        receipt_lines.append("      City, State 12345")
        receipt_lines.append("    Phone: (555) 123-4567")
        receipt_lines.append("================================")
        receipt_lines.append("")
        
        # Receipt info
        receipt_number = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"
        receipt_lines.append(f"Receipt #: {receipt_number}")
        receipt_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        receipt_lines.append(f"Cashier: POS User")
        
        # Customer info if available
        if self.current_customer:
            receipt_lines.append(f"Customer: {self.current_customer['name'][:22]}")
        
        receipt_lines.append("--------------------------------")
        receipt_lines.append("")
        
        # Compact items header (32 chars total)
        receipt_lines.append("Item            Qty  Prc  Tot")
        receipt_lines.append("--------------------------------")
        
        # Items with tight alignment for 32 chars
        for item in self.order_items:
            # Item name (15 chars max)
            name = item['description'][:15].ljust(15)
            # Qty (3 chars)
            qty_str = f"{item['quantity']:.0f}".rjust(3)
            # Price (4 chars)
            price_str = f"{item['price']:.0f}".rjust(4)
            # Total (5 chars)
            total_str = f"{item['total']:.0f}".rjust(5)
            
            # Create 32-char line
            line = f"{name} {qty_str} {price_str} {total_str}"
            receipt_lines.append(line)
        
        receipt_lines.append("--------------------------------")
        receipt_lines.append("")
        
        # Totals with compact alignment
        receipt_lines.append(f"{'Subtotal:':<20} {self.subtotal:>10.2f}")
        
        if self.discount_amount > 0:
            receipt_lines.append(f"{'Discount:':<20} -{self.discount_amount:>9.2f}")
        
        if self.tax_enabled:
            tax_amount = (self.subtotal - self.discount_amount) * self.tax_rate
            receipt_lines.append(f"{'Tax:':<20} {tax_amount:>10.2f}")
        else:
            tax_amount = 0
        
        total = self.subtotal - self.discount_amount + tax_amount
        receipt_lines.append("================================")
        receipt_lines.append(f"{'TOTAL:':<20} {total:>10.2f}")
        receipt_lines.append("================================")
        receipt_lines.append("")
        
        # Payment info
        receipt_lines.append(f"{'Payment:':<20} {self.current_payment:>10.2f}")
        change = self.current_payment - total if self.current_payment > total else 0
        receipt_lines.append(f"{'Change:':<20} {change:>10.2f}")
        receipt_lines.append("")
        
        # Footer
        receipt_lines.append("================================")
        receipt_lines.append("    Thank you for your business!")
        
        if self.current_customer:
            customer_name = self.current_customer['name'][:20]
            receipt_lines.append(f"    Thank you, {customer_name}!")
        
        receipt_lines.append("       Please come again!")
        receipt_lines.append("")
        receipt_lines.append("      Return Policy: 30 days")
        receipt_lines.append("   Keep this receipt for returns")
        receipt_lines.append("================================")
        
        # Store data for fallback
        self.last_receipt_data = {
            'receipt_number': receipt_number,
            'subtotal': self.subtotal,
            'discount_amount': self.discount_amount,
            'tax_amount': tax_amount,
            'total_amount': total,
            'payment_amount': self.current_payment,
            'change_amount': change,
            'sale_date': datetime.now().isoformat()
        }
        
        return "\n".join(receipt_lines)
        
    def save_sale_to_database(self):
        """Save the sale to database"""
        if not self.order_items:
            return False
        
        try:
            # Get receipt data (should be created by create_receipt method)
            if not hasattr(self, 'last_receipt_data') or not self.last_receipt_data:
                QMessageBox.warning(self, "Warning", "Receipt data not found!")
                return False
            
            receipt_data = self.last_receipt_data
            
            # Prepare sale data tuple for database
            sale_data = (
                receipt_data['receipt_number'],
                receipt_data['subtotal'],
                receipt_data['discount_amount'],
                receipt_data['tax_amount'],
                receipt_data['total_amount'],
                receipt_data['payment_amount'],
                receipt_data['change_amount'],
                receipt_data['sale_date']
            )
            
            # Save to database using the database manager
            sale_id = self.db_manager.save_sale(sale_data, self.order_items)
            
            if sale_id:
                self.statusBar().showMessage(
                    f"Sale saved successfully! Receipt: {receipt_data['receipt_number']}", 
                    3000
                )
                return True
            else:
                QMessageBox.warning(self, "Warning", "Failed to save sale to database!")
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error saving sale: {str(e)}")
            return False
    def print_receipt(self):
        """Print or preview receipt"""
        if not self.order_items:
            QMessageBox.warning(self, "Warning", "No items in order to print!")
            return
        
        receipt_data = self.create_receipt()
        
        if isinstance(receipt_data, str):
            # Text receipt - show in dialog
            dialog = ReceiptDialog(receipt_data, self)
            dialog.exec()
        else:
            # PDF receipt - print directly or show options
            if receipt_data and os.path.exists(receipt_data):
                reply = QMessageBox.question(
                    self, "Receipt Ready", 
                    "Choose action:\n"
                    "• Yes: Print directly to thermal printer\n"
                    "• No: Preview and print options\n"
                    "• Cancel: Save only",
                    QMessageBox.StandardButton.Yes | 
                    QMessageBox.StandardButton.No | 
                    QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Direct print to thermal printer
                    self.print_pdf_direct(receipt_data)
                elif reply == QMessageBox.StandardButton.No:
                    # Show preview dialog
                    dialog = PDFReceiptDialog(receipt_data, self)
                    dialog.exec()
                # Cancel just saves the file in temp directory
            else:
                QMessageBox.critical(self, "Error", "Failed to create receipt!")
    
    def print_pdf_direct(self, pdf_file):
        """Print PDF receipt directly to thermal printer"""
        try:
            if os.name == "nt":  # Windows
                # Try to find SumatraPDF in common locations
                sumatra_paths = [
                    r"C:\Users\DeLL\AppData\Local\SumatraPDF\SumatraPDF.exe",
                    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
                    os.path.expanduser(r"~\AppData\Local\SumatraPDF\SumatraPDF.exe")
                ]
                
                sumatra_path = None
                for path in sumatra_paths:
                    if os.path.exists(path):
                        sumatra_path = path
                        break
                
                if sumatra_path:
                    # Silent print to default printer
                    subprocess.run([sumatra_path, "-print-to-default", pdf_file], 
                                 check=True, shell=True)
                    QMessageBox.information(self, "Success", 
                                          "Receipt sent to thermal printer!\n"
                                          f"PDF saved: {pdf_file}")
                else:
                    # Fallback: try to print using Windows default
                    os.startfile(pdf_file, "print")
                    QMessageBox.information(self, "Print", 
                                          "Receipt opened for printing.\n"
                                          "Please select your thermal printer.")
                    
            else:  # macOS & Linux
                # Use lp command for Unix-like systems
                subprocess.run(["lp", pdf_file], check=True)
                QMessageBox.information(self, "Success", 
                                      "Receipt sent to printer!\n"
                                      f"PDF saved: {pdf_file}")
                
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Print Error", 
                              f"Failed to print receipt: {e}\n"
                              f"PDF saved at: {pdf_file}")
        except Exception as e:
            QMessageBox.warning(self, "Print Error", 
                              f"Print error: {e}\n"
                              f"PDF saved at: {pdf_file}")
        
        try:
            # Prepare sale data
            receipt_data = self.last_receipt_data
            sale_data = (
                receipt_data['receipt_number'],
                receipt_data['subtotal'],
                receipt_data['discount_amount'],
                receipt_data['tax_amount'],
                receipt_data['total_amount'],
                receipt_data['payment_amount'],
                receipt_data['change_amount'],
                receipt_data['sale_date']
            )
            
            # Save to database
            sale_id = self.db_manager.save_sale(sale_data, self.order_items)
            
            if sale_id:
                self.statusBar().showMessage(f"Sale saved successfully! Receipt: {receipt_data['receipt_number']}", 3000)
                return True
            else:
                QMessageBox.warning(self, "Warning", "Failed to save sale to database!")
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving sale: {str(e)}")
            return False
    
    def print_receipt(self):
        """Print or preview receipt"""
        if not self.order_items:
            QMessageBox.warning(self, "Warning", "No items in order to print!")
            return
        
        receipt_text = self.create_receipt()
        dialog = ReceiptDialog(receipt_text, self)
        dialog.exec()

    # Menu action handlers
    def new_order(self):
        """Start a new order"""
        if self.order_items:
            reply = QMessageBox.question(self, "New Order", 
                                    "Current order will be lost. Continue?",
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.order_items.clear()
        self.current_payment = 0.0
        self.discount_amount = 0.0
        self.discount_percentage = 0.0
        self.current_quantity_input = ""
        self.current_customer = None  # Clear customer selection
        self.update_order_display()
        self.calculate_totals()
        
        # Update status bar
        self.statusBar().showMessage("New order started - Ready", 2000)
    
    def open_product_management(self):
        """Open product management dialog"""
        try:
            from product_management import ProductManagementDialog
            dialog = ProductManagementDialog(self)
            dialog.exec()
            # Refresh products after dialog closes
            self.load_products_from_database()
        except ImportError:
            QMessageBox.warning(self, "Module Not Found", 
                              "Product management module not found!\n"
                              "Please ensure product_management.py is in the same directory.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open product management: {str(e)}")
    
    def open_category_management(self):
        """Open category management dialog"""
        try:
            dialog = CategoryManagementDialog(self)
            dialog.exec()
            # Refresh products and categories after dialog closes
            self.load_products_from_database()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open category management: {str(e)}")
    
    def open_inventory_management(self):
        """Open inventory management dialog"""
        try:
            dialog = InventoryManagementDialog(self)
            dialog.exec()
            # Refresh products after dialog closes
            self.load_products_from_database()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open inventory management: {str(e)}")

    def open_stock_adjustment(self):
        """Open stock adjustment dialog"""
        try:
            dialog = StockAdjustmentDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_products_from_database()  # Refresh products
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open stock adjustment: {str(e)}")
    
    def open_customer_management(self):
        """Open customer management dialog"""
        try:
            dialog = CustomerManagementDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open customer management: {str(e)}")

    
    def open_vendor_management(self):
        QMessageBox.information(self, "Vendor Management", "Vendor management window will be implemented in separate module.")
    
    def open_sales_report(self):
        QMessageBox.information(self, "Sales Report", "Sales report window will be implemented in separate module.")
    
    def open_inventory_report(self):
        QMessageBox.information(self, "Inventory Report", "Inventory report window will be implemented in separate module.")
    
    def open_customer_report(self):
        QMessageBox.information(self, "Customer Report", "Customer report window will be implemented in separate module.")
    
    def hold_order(self):
        QMessageBox.information(self, "Hold Order", "Hold order functionality will be implemented.")
    
    def recall_order(self):
        QMessageBox.information(self, "Recall Order", "Recall order functionality will be implemented.")
    
    def open_settings(self):
        QMessageBox.information(self, "Settings", "Settings window will be implemented in separate module.")
    
    def show_reportlab_help(self):
        """Show ReportLab installation help"""
        help_text = """

🔧 Installation Instructions:

1️⃣ Open Command Prompt/Terminal as Administrator
2️⃣ Run the installation command:
   
   pip install reportlab

3️⃣ Restart the POS application
4️⃣ Professional PDF receipts will be automatically enabled!

✨ Benefits of PDF Receipts:
• Perfect formatting for 80x297mm thermal paper
• Professional fonts and layout
• Precise margins and spacing
• Direct thermal printer support
• High-quality print output
• Automatic paper size optimization

🖨️ Printing Features:
• Direct print to thermal printers
• SumatraPDF integration (Windows)
• Universal printer support
• ESC/POS compatibility

📋 Current Status: """ + ("✅ INSTALLED" if REPORTLAB_AVAILABLE else "❌ NOT INSTALLED") + """

💡 Note: Text-based receipts are used as fallback when ReportLab is not available.
        """
        
        QMessageBox.information(self, "ReportLab Installation Guide", help_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
🏪 Wholesale Dealer POS System

Version: 1.0.0
Built with: PyQt6 + SQLite

✨ Features:
• Product Management with Barcode Support
• Professional PDF Receipts (80x297mm)
• Thermal Printer Integration
• Real-time Inventory Tracking
• Customer & Vendor Management
• Comprehensive Sales Reporting
• Multi-currency Support
• Tax and Discount Calculations

🔧 Technical:
• Database: SQLite with automatic migration
• Receipt Engine: ReportLab PDF generation
• Barcode: Keyboard wedge scanner support
• Printing: ESC/POS thermal printer commands

📞 Support:
• GitHub: [Your Repository]
• Email: [Your Email]
• Documentation: [Your Docs URL]

© 2025 Your Business Name. All rights reserved.
        """
        
        QMessageBox.about(self, "About POS System", about_text)

    # Function button handlers
    def apply_percentage_discount(self):
        """Apply percentage discount"""
        percentage, ok = QInputDialog.getDouble(self, "Percentage Discount", 
                                              "Enter discount percentage:", 
                                              value=0, min=0, max=100, decimals=2)
        if ok:
            self.discount_percentage = percentage
            self.calculate_totals()
    
    def apply_fixed_discount(self):
        """Apply fixed amount discount"""
        amount, ok = QInputDialog.getDouble(self, "Fixed Discount", 
                                          "Enter discount amount:", 
                                          value=0, min=0, decimals=2)
        if ok:
            self.discount_amount = amount
            self.discount_percentage = 0  # Reset percentage discount
            self.calculate_totals()
    
    def select_customer(self):
        """Open customer selection dialog for POS"""
        try:
            dialog = CustomerSelectionDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.selected_customer:
                    self.current_customer = dialog.selected_customer
                    self.statusBar().showMessage(
                        f"Customer selected: {dialog.selected_customer['name']}", 3000
                    )
                    
                    # Update customer button text if you want
                    customer_text = f"Customer: {dialog.selected_customer['name'][:10]}..."
                    # You can update a customer display label here if you have one
                    
                else:
                    self.current_customer = None
                    self.statusBar().showMessage("No customer selected", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open customer selection: {str(e)}")

    
    def toggle_tax(self):
        """Toggle tax calculation"""
        self.tax_enabled = not self.tax_enabled
        self.tax_checkbox.setChecked(self.tax_enabled)
        self.calculate_totals()
    
    def toggle_tax_checkbox(self):
        """Handle tax checkbox toggle"""
        self.tax_enabled = self.tax_checkbox.isChecked()
        self.calculate_totals()
    
    def add_comments(self):
        QMessageBox.information(self, "Comments", "Comments functionality will be implemented.")
    
    def show_subtotal(self):
        QMessageBox.information(self, "Subtotal", f"Current subtotal: {self.subtotal:.2f}")
    
    def process_refund(self):
        QMessageBox.information(self, "Refund", "Refund functionality will be implemented.")
    
    def duplicate_order(self):
        QMessageBox.information(self, "Duplicate Order", "Duplicate order functionality will be implemented.")
    
    def cancel_bill(self):
        """Cancel current bill"""
        if self.order_items:
            reply = QMessageBox.question(self, "Cancel Bill", 
                                       "Are you sure you want to cancel this bill?",
                                       QMessageBox.StandardButton.Yes | 
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.new_order()
    
    def void_last_item(self):
        """Void the last item in order"""
        if self.order_items:
            self.order_items.pop()
            self.update_order_display()
            self.calculate_totals()
    
    def edit_order_item(self, item):
        """Edit order item on double click"""
        row = item.row()
        if 0 <= row < len(self.order_items):
            current_qty = self.order_items[row]['quantity']
            new_qty, ok = QInputDialog.getDouble(self, "Edit Quantity", 
                                               f"Enter new quantity for {self.order_items[row]['description']}:", 
                                               value=current_qty, min=0.01, decimals=2)
            if ok:
                self.order_items[row]['quantity'] = new_qty
                self.order_items[row]['total'] = new_qty * self.order_items[row]['price']
                self.update_order_display()
                self.calculate_totals()
    
    def change_quantity(self):
        """Change quantity of selected item"""
        current_row = self.order_table.currentRow()
        if current_row >= 0 and current_row < len(self.order_items):
            self.edit_order_item(self.order_table.item(current_row, 0))
    
    def remove_selected_item(self):
        """Remove selected item from order"""
        current_row = self.order_table.currentRow()
        if current_row >= 0:
            self.remove_order_item(current_row)
    
    def process_payment(self):
        """Process payment for the order with customer support"""
        if not self.order_items:
            QMessageBox.warning(self, "Warning", "No items in order!")
            return
        
        total = float(self.total_label.text())
        
        # Get payment amount
        try:
            if self.current_quantity_input:
                payment = float(self.current_quantity_input)
            else:
                payment, ok = QInputDialog.getDouble(self, "Payment", 
                                                f"Enter payment amount (Total: {total:.2f}):", 
                                                value=total, min=0, decimals=2)
                if not ok:
                    return
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid payment amount!")
            return
        
        if payment < total:
            reply = QMessageBox.question(
                self, "Insufficient Payment", 
                f"Payment amount ({payment:.2f}) is less than total ({total:.2f})!\n\nProcess as partial payment?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.current_payment = payment
        self.calculate_totals()
        
        # Create receipt (PDF or text)
        receipt_result = self.create_receipt()
        
        # Save sale to database with customer information
        sale_saved = self.save_sale_to_database()
        
        # Handle customer transaction if customer is selected
        if self.current_customer and sale_saved:
            try:
                conn = sqlite3.connect(self.db_manager.db_path)
                cursor = conn.cursor()
                
                # Add sale transaction to customer account
                cursor.execute('''
                    INSERT INTO customer_transactions 
                    (customer_id, transaction_type, amount, description, reference_number)
                    VALUES (?, ?, ?, ?, ?)
                ''', (self.current_customer['id'], 'SALE', total, 
                    f"POS Sale - {len(self.order_items)} items", 
                    self.last_receipt_data.get('receipt_number', '')))
                
                # Update customer balance and statistics
                cursor.execute('''
                    UPDATE customers 
                    SET current_balance = current_balance + ?,
                        total_purchases = total_purchases + ?,
                        last_purchase_date = ?
                    WHERE id = ?
                ''', (total, total, datetime.now().isoformat(), self.current_customer['id']))
                
                # Update the sale record with customer information
                cursor.execute('''
                    UPDATE sales 
                    SET customer_id = ?, customer_name = ?
                    WHERE receipt_number = ?
                ''', (self.current_customer['id'], self.current_customer['name'], 
                    self.last_receipt_data.get('receipt_number', '')))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Error updating customer transaction: {e}")
        
        # Show receipt based on type
        if isinstance(receipt_result, str):
            # Text receipt
            receipt_dialog = ReceiptDialog(receipt_result, self)
            receipt_dialog.receipt_saved = sale_saved
            receipt_dialog.exec()
        else:
            # PDF receipt
            if receipt_result and os.path.exists(receipt_result):
                if REPORTLAB_AVAILABLE:
                    customer_info = ""
                    if self.current_customer:
                        customer_info = f"\n👤 Customer: {self.current_customer['name']}"
                    
                    QMessageBox.information(self, "Payment Complete", 
                                        f"Payment processed successfully!{customer_info}\n\n"
                                        f"📄 Professional PDF receipt created\n"
                                        f"💾 Sale {'saved' if sale_saved else 'not saved'} to database\n"
                                        f"🖨️ Ready for thermal printer\n\n"
                                        f"Receipt: {self.last_receipt_data.get('receipt_number', 'N/A')}")
                    
                    # Show PDF dialog
                    pdf_dialog = PDFReceiptDialog(receipt_result, self)
                    pdf_dialog.exec()
                else:
                    QMessageBox.information(self, "Payment Complete", 
                                        "Payment processed successfully!\n"
                                        "Install ReportLab for professional PDF receipts:\n"
                                        "pip install reportlab")
            else:
                QMessageBox.warning(self, "Warning", "Payment processed but receipt creation failed!")
        
        # Ask if want to start new order
        reply = QMessageBox.question(self, "New Order", 
                                "Start new order?",
                                QMessageBox.StandardButton.Yes | 
                                QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.new_order()

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = POSMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()