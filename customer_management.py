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
import csv
from product_management import DatabaseManager
class CustomerManagementDialog(QDialog):
    """Customer Management Dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.init_database_tables()
        self.init_ui()
        self.load_customers()
        
    def init_database_tables(self):
        """Initialize customer-related database tables"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contact_number TEXT,
                    cnic_tax_id TEXT,
                    company_name TEXT,
                    address TEXT,
                    email TEXT,
                    credit_limit REAL DEFAULT 0.0,
                    current_balance REAL DEFAULT 0.0,
                    customer_type TEXT DEFAULT 'Regular' CHECK(customer_type IN ('Regular', 'VIP', 'Wholesale')),
                    discount_percentage REAL DEFAULT 0.0,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_purchase_date TEXT,
                    total_purchases REAL DEFAULT 0.0,
                    notes TEXT
                )
            ''')
            
            # Customer transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    transaction_type TEXT CHECK(transaction_type IN ('SALE', 'PAYMENT', 'CREDIT', 'DEBIT')),
                    amount REAL,
                    description TEXT,
                    reference_number TEXT,
                    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'POS User',
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # Add customer_id to sales table if not exists
            try:
                cursor.execute('ALTER TABLE sales ADD COLUMN customer_id INTEGER')
                cursor.execute('ALTER TABLE sales ADD COLUMN customer_name TEXT')
            except sqlite3.OperationalError:
                pass  # Columns already exist
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error initializing customer tables: {e}")
    
    def init_ui(self):
        self.setWindowTitle("Customer Management")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left panel - Customer list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Search and filters
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Name, contact, company, or CNIC...")
        self.search_input.textChanged.connect(self.filter_customers)
        
        # Customer type filter
        type_label = QLabel("Type:")
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Regular", "VIP", "Wholesale"])
        self.type_filter.currentTextChanged.connect(self.filter_customers)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(type_label)
        search_layout.addWidget(self.type_filter)
        left_layout.addLayout(search_layout)
        
        # Customer list table
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(7)
        self.customer_table.setHorizontalHeaderLabels([
            'ID', 'Name', 'Contact', 'Company', 'Type', 'Balance', 'Last Purchase'
        ])
        
        # Set column properties
        header = self.customer_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Contact
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Company
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Type
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Balance
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Last Purchase
        
        self.customer_table.setColumnWidth(0, 50)   # ID
        self.customer_table.setColumnWidth(2, 120)  # Contact
        self.customer_table.setColumnWidth(4, 80)   # Type
        self.customer_table.setColumnWidth(5, 100)  # Balance
        self.customer_table.setColumnWidth(6, 120)  # Last Purchase
        
        # Hide ID column
        self.customer_table.setColumnHidden(0, True)
        
        self.customer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.itemSelectionChanged.connect(self.on_customer_selected)
        
        left_layout.addWidget(self.customer_table)
        
        # Customer list buttons
        list_buttons_layout = QHBoxLayout()
        
        self.add_customer_btn = QPushButton("➕ Add Customer")
        self.add_customer_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.add_customer_btn.clicked.connect(self.add_customer)
        
        self.edit_customer_btn = QPushButton("✏️ Edit Customer")
        self.edit_customer_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)
        self.edit_customer_btn.clicked.connect(self.edit_customer)
        self.edit_customer_btn.setEnabled(False)
        
        self.delete_customer_btn = QPushButton("🗑️ Delete Customer")
        self.delete_customer_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        self.delete_customer_btn.clicked.connect(self.delete_customer)
        self.delete_customer_btn.setEnabled(False)
        
        list_buttons_layout.addWidget(self.add_customer_btn)
        list_buttons_layout.addWidget(self.edit_customer_btn)
        list_buttons_layout.addWidget(self.delete_customer_btn)
        list_buttons_layout.addStretch()
        
        left_layout.addLayout(list_buttons_layout)
        left_panel.setLayout(left_layout)
        
        # Right panel - Customer details and history
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Customer details form
        details_group = QFrame()
        details_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        details_group.setStyleSheet("QFrame { border: 2px solid #ccc; border-radius: 10px; padding: 10px; }")
        details_layout = QVBoxLayout()
        
        details_title = QLabel("Customer Details")
        details_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px;")
        details_layout.addWidget(details_title)
        
        # Form fields in a grid
        form_layout = QGridLayout()
        
        # Row 0: Name and Contact
        form_layout.addWidget(QLabel("Name:*"), 0, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Customer name...")
        form_layout.addWidget(self.name_input, 0, 1)
        
        form_layout.addWidget(QLabel("Contact:"), 0, 2)
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Phone number...")
        form_layout.addWidget(self.contact_input, 0, 3)
        
        # Row 1: CNIC and Company
        form_layout.addWidget(QLabel("CNIC/Tax ID:"), 1, 0)
        self.cnic_input = QLineEdit()
        self.cnic_input.setPlaceholderText("CNIC or Tax ID...")
        form_layout.addWidget(self.cnic_input, 1, 1)
        
        form_layout.addWidget(QLabel("Company:"), 1, 2)
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Company name...")
        form_layout.addWidget(self.company_input, 1, 3)
        
        # Row 2: Email and Customer Type
        form_layout.addWidget(QLabel("Email:"), 2, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("customer@email.com")
        form_layout.addWidget(self.email_input, 2, 1)
        
        form_layout.addWidget(QLabel("Type:"), 2, 2)
        self.customer_type_combo = QComboBox()
        self.customer_type_combo.addItems(["Regular", "VIP", "Wholesale"])
        form_layout.addWidget(self.customer_type_combo, 2, 3)
        
        # Row 3: Credit Limit and Discount
        form_layout.addWidget(QLabel("Credit Limit:"), 3, 0)
        self.credit_limit_input = QDoubleSpinBox()
        self.credit_limit_input.setMaximum(999999.99)
        self.credit_limit_input.setDecimals(2)
        form_layout.addWidget(self.credit_limit_input, 3, 1)
        
        form_layout.addWidget(QLabel("Discount %:"), 3, 2)
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(100.0)
        self.discount_input.setDecimals(2)
        self.discount_input.setSuffix("%")
        form_layout.addWidget(self.discount_input, 3, 3)
        
        details_layout.addLayout(form_layout)
        
        # Address
        address_layout = QHBoxLayout()
        address_layout.addWidget(QLabel("Address:"))
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(60)
        self.address_input.setPlaceholderText("Customer address...")
        address_layout.addWidget(self.address_input)
        details_layout.addLayout(address_layout)
        
        # Notes
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Notes:"))
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlaceholderText("Additional notes...")
        notes_layout.addWidget(self.notes_input)
        details_layout.addLayout(notes_layout)
        
        # Form buttons
        form_buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Customer")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.save_btn.clicked.connect(self.save_customer)
        
        self.clear_btn = QPushButton("🗑️ Clear Form")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        self.clear_btn.clicked.connect(self.clear_form)
        
        form_buttons_layout.addWidget(self.save_btn)
        form_buttons_layout.addWidget(self.clear_btn)
        form_buttons_layout.addStretch()
        details_layout.addLayout(form_buttons_layout)
        
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        # Customer statistics
        stats_group = QFrame()
        stats_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        stats_group.setStyleSheet("QFrame { border: 2px solid #ccc; border-radius: 10px; padding: 10px; }")
        stats_layout = QVBoxLayout()
        
        stats_title = QLabel("Customer Statistics")
        stats_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; margin-bottom: 5px;")
        stats_layout.addWidget(stats_title)
        
        stats_info_layout = QHBoxLayout()
        
        self.total_purchases_label = QLabel("Total Purchases: $0.00")
        self.current_balance_label = QLabel("Current Balance: $0.00")
        self.last_purchase_label = QLabel("Last Purchase: Never")
        
        for label in [self.total_purchases_label, self.current_balance_label, self.last_purchase_label]:
            label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 5px;
                    font-weight: bold;
                    margin: 2px;
                }
            """)
        
        stats_info_layout.addWidget(self.total_purchases_label)
        stats_info_layout.addWidget(self.current_balance_label)
        stats_info_layout.addWidget(self.last_purchase_label)
        
        stats_layout.addLayout(stats_info_layout)
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # Customer transaction history
        history_group = QFrame()
        history_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        history_group.setStyleSheet("QFrame { border: 2px solid #ccc; border-radius: 10px; padding: 10px; }")
        history_layout = QVBoxLayout()
        
        history_title_layout = QHBoxLayout()
        history_title = QLabel("Transaction History")
        history_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        
        # History action buttons
        self.add_payment_btn = QPushButton("💰 Add Payment")
        self.add_payment_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #138496; }
        """)
        self.add_payment_btn.clicked.connect(self.add_payment)
        self.add_payment_btn.setEnabled(False)
        
        self.add_credit_btn = QPushButton("💳 Add Credit")
        self.add_credit_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.add_credit_btn.clicked.connect(self.add_credit)
        self.add_credit_btn.setEnabled(False)
        
        history_title_layout.addWidget(history_title)
        history_title_layout.addStretch()
        history_title_layout.addWidget(self.add_payment_btn)
        history_title_layout.addWidget(self.add_credit_btn)
        
        history_layout.addLayout(history_title_layout)
        
        # Transaction history table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Amount', 'Description', 'Reference', 'Balance'
        ])
        
        # Set column properties
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Date
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Type
        history_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Amount
        history_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Description
        history_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Reference
        history_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Balance
        
        self.history_table.setColumnWidth(0, 120)  # Date
        self.history_table.setColumnWidth(1, 80)   # Type
        self.history_table.setColumnWidth(2, 100)  # Amount
        self.history_table.setColumnWidth(4, 120)  # Reference
        self.history_table.setColumnWidth(5, 100)  # Balance
        
        self.history_table.setMaximumHeight(200)
        self.history_table.setAlternatingRowColors(True)
        
        history_layout.addWidget(self.history_table)
        history_group.setLayout(history_layout)
        right_layout.addWidget(history_group)
        
        right_panel.setLayout(right_layout)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        # Dialog buttons
        dialog_buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export Customers")
        export_btn.clicked.connect(self.export_customers)
        
        report_btn = QPushButton("📊 Customer Report")
        report_btn.clicked.connect(self.show_customer_report)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_customers)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.close)
        
        dialog_buttons_layout.addWidget(export_btn)
        dialog_buttons_layout.addWidget(report_btn)
        dialog_buttons_layout.addWidget(refresh_btn)
        dialog_buttons_layout.addStretch()
        dialog_buttons_layout.addWidget(close_btn)
        
        # Final layout
        final_layout = QVBoxLayout()
        final_layout.addLayout(main_layout)
        final_layout.addLayout(dialog_buttons_layout)
        
        self.setLayout(final_layout)
        
        # Initialize form state
        self.current_customer_id = None
        self.clear_form()
    
    def load_customers(self):
        """Load all customers into table"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, contact_number, company_name, customer_type,
                       current_balance, last_purchase_date
                FROM customers
                ORDER BY name
            ''')
            
            customers = cursor.fetchall()
            conn.close()
            
            self.customer_table.setRowCount(len(customers))
            
            for row, (cust_id, name, contact, company, cust_type, balance, last_purchase) in enumerate(customers):
                self.customer_table.setItem(row, 0, QTableWidgetItem(str(cust_id)))
                self.customer_table.setItem(row, 1, QTableWidgetItem(name or ""))
                self.customer_table.setItem(row, 2, QTableWidgetItem(contact or ""))
                self.customer_table.setItem(row, 3, QTableWidgetItem(company or ""))
                self.customer_table.setItem(row, 4, QTableWidgetItem(cust_type or "Regular"))
                
                # Balance with color coding
                balance_item = QTableWidgetItem(f"${balance:.2f}")
                if balance > 0:
                    balance_item.setForeground(QColor("#dc3545"))  # Red for debt
                elif balance < 0:
                    balance_item.setForeground(QColor("#28a745"))  # Green for credit
                self.customer_table.setItem(row, 5, balance_item)
                
                # Last purchase date
                last_purchase_text = "Never"
                if last_purchase:
                    try:
                        date_obj = datetime.fromisoformat(last_purchase)
                        last_purchase_text = date_obj.strftime('%Y-%m-%d')
                    except:
                        last_purchase_text = str(last_purchase)
                
                self.customer_table.setItem(row, 6, QTableWidgetItem(last_purchase_text))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load customers: {str(e)}")
    
    def filter_customers(self):
        """Filter customers based on search and type"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        for row in range(self.customer_table.rowCount()):
            show_row = True
            
            # Search filter
            if search_text:
                name = self.customer_table.item(row, 1).text().lower()
                contact = self.customer_table.item(row, 2).text().lower()
                company = self.customer_table.item(row, 3).text().lower()
                
                if not (search_text in name or search_text in contact or search_text in company):
                    show_row = False
            
            # Type filter
            if show_row and type_filter != "All Types":
                customer_type = self.customer_table.item(row, 4).text()
                if customer_type != type_filter:
                    show_row = False
            
            self.customer_table.setRowHidden(row, not show_row)
    
    def on_customer_selected(self):
        """Handle customer selection"""
        current_row = self.customer_table.currentRow()
        if current_row >= 0:
            customer_id = int(self.customer_table.item(current_row, 0).text())
            self.load_customer_details(customer_id)
            
            # Enable action buttons
            self.edit_customer_btn.setEnabled(True)
            self.delete_customer_btn.setEnabled(True)
            self.add_payment_btn.setEnabled(True)
            self.add_credit_btn.setEnabled(True)
    
    def load_customer_details(self, customer_id):
        """Load customer details into form"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Get customer details
            cursor.execute('''
                SELECT name, contact_number, cnic_tax_id, company_name, address,
                       email, credit_limit, current_balance, customer_type,
                       discount_percentage, notes, total_purchases, last_purchase_date
                FROM customers
                WHERE id = ?
            ''', (customer_id,))
            
            customer = cursor.fetchone()
            
            if customer:
                (name, contact, cnic, company, address, email, credit_limit,
                 balance, cust_type, discount, notes, total_purchases, last_purchase) = customer
                
                # Populate form
                self.current_customer_id = customer_id
                self.name_input.setText(name or "")
                self.contact_input.setText(contact or "")
                self.cnic_input.setText(cnic or "")
                self.company_input.setText(company or "")
                self.address_input.setPlainText(address or "")
                self.email_input.setText(email or "")
                self.credit_limit_input.setValue(credit_limit or 0.0)
                self.discount_input.setValue(discount or 0.0)
                self.notes_input.setPlainText(notes or "")
                
                # Set customer type
                type_index = self.customer_type_combo.findText(cust_type or "Regular")
                if type_index >= 0:
                    self.customer_type_combo.setCurrentIndex(type_index)
                
                # Update statistics
                self.total_purchases_label.setText(f"Total Purchases: ${total_purchases or 0:.2f}")
                self.current_balance_label.setText(f"Current Balance: ${balance or 0:.2f}")
                
                last_purchase_text = "Never"
                if last_purchase:
                    try:
                        date_obj = datetime.fromisoformat(last_purchase)
                        last_purchase_text = date_obj.strftime('%Y-%m-%d')
                    except:
                        last_purchase_text = str(last_purchase)
                
                self.last_purchase_label.setText(f"Last Purchase: {last_purchase_text}")
                
                # Load transaction history
                self.load_customer_history(customer_id)
            
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load customer details: {str(e)}")
    
    def load_customer_history(self, customer_id):
        """Load customer transaction history"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT transaction_date, transaction_type, amount, description,
                       reference_number
                FROM customer_transactions
                WHERE customer_id = ?
                ORDER BY transaction_date DESC
                LIMIT 50
            ''', (customer_id,))
            
            transactions = cursor.fetchall()
            conn.close()
            
            self.history_table.setRowCount(len(transactions))
            
            running_balance = 0
            for row, (date, trans_type, amount, description, reference) in enumerate(transactions):
                # Format date
                try:
                    date_obj = datetime.fromisoformat(date)
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                except:
                    formatted_date = str(date)
                
                self.history_table.setItem(row, 0, QTableWidgetItem(formatted_date))
                
                # Transaction type with color
                type_item = QTableWidgetItem(trans_type)
                if trans_type == "SALE":
                    type_item.setForeground(QColor("#dc3545"))  # Red
                    running_balance += amount
                elif trans_type == "PAYMENT":
                    type_item.setForeground(QColor("#28a745"))  # Green
                    running_balance -= amount
                elif trans_type == "CREDIT":
                    type_item.setForeground(QColor("#007bff"))  # Blue
                    running_balance -= amount
                else:  # DEBIT
                    type_item.setForeground(QColor("#ffc107"))  # Yellow
                    running_balance += amount
                
                self.history_table.setItem(row, 1, type_item)
                
                # Amount with color
                amount_item = QTableWidgetItem(f"${amount:.2f}")
                if trans_type in ["SALE", "DEBIT"]:
                    amount_item.setForeground(QColor("#dc3545"))  # Red for charges
                else:
                    amount_item.setForeground(QColor("#28a745"))  # Green for payments
                
                self.history_table.setItem(row, 2, amount_item)
                self.history_table.setItem(row, 3, QTableWidgetItem(description or ""))
                self.history_table.setItem(row, 4, QTableWidgetItem(reference or ""))
                self.history_table.setItem(row, 5, QTableWidgetItem(f"${running_balance:.2f}"))
            
        except Exception as e:
            print(f"Error loading customer history: {e}")
    
    def add_customer(self):
        """Start adding new customer"""
        self.clear_form()
        self.name_input.setFocus()
    
    def edit_customer(self):
        """Edit selected customer (form is already populated)"""
        if self.current_customer_id:
            self.name_input.setFocus()
    
    def delete_customer(self):
        """Delete selected customer"""
        if not self.current_customer_id:
            return
        
        current_row = self.customer_table.currentRow()
        if current_row < 0:
            return
        
        customer_name = self.customer_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Delete Customer",
            f"Are you sure you want to delete customer '{customer_name}'?\n\n"
            f"This will also delete all transaction history for this customer.\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(self.db_manager.db_path)
                cursor = conn.cursor()
                
                # Delete customer transactions first
                cursor.execute('DELETE FROM customer_transactions WHERE customer_id = ?',
                             (self.current_customer_id,))
                
                # Delete customer
                cursor.execute('DELETE FROM customers WHERE id = ?', (self.current_customer_id,))
                
                conn.commit()
                conn.close()
                
                QMessageBox.information(self, "Success", f"Customer '{customer_name}' deleted successfully!")
                self.load_customers()
                self.clear_form()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete customer: {str(e)}")
    
    def save_customer(self):
        """Save customer (add or edit)"""
        name = self.name_input.text().strip()
        contact = self.contact_input.text().strip()
        cnic = self.cnic_input.text().strip()
        company = self.company_input.text().strip()
        address = self.address_input.toPlainText().strip()
        email = self.email_input.text().strip()
        credit_limit = self.credit_limit_input.value()
        customer_type = self.customer_type_combo.currentText()
        discount = self.discount_input.value()
        notes = self.notes_input.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Customer name is required!")
            return
        
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            if self.current_customer_id:
                # Update existing customer
                cursor.execute('''
                    UPDATE customers SET
                        name = ?, contact_number = ?, cnic_tax_id = ?, company_name = ?,
                        address = ?, email = ?, credit_limit = ?, customer_type = ?,
                        discount_percentage = ?, notes = ?
                    WHERE id = ?
                ''', (name, contact, cnic, company, address, email, credit_limit,
                      customer_type, discount, notes, self.current_customer_id))
                message = f"Customer '{name}' updated successfully!"
            else:
                # Add new customer
                cursor.execute('''
                    INSERT INTO customers (name, contact_number, cnic_tax_id, company_name,
                                         address, email, credit_limit, customer_type,
                                         discount_percentage, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, contact, cnic, company, address, email, credit_limit,
                      customer_type, discount, notes))
                message = f"Customer '{name}' added successfully!"
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", message)
            self.load_customers()
            self.clear_form()
            
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Error", "A customer with this information already exists!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save customer: {str(e)}")
    
    def clear_form(self):
        """Clear the form"""
        self.current_customer_id = None
        self.name_input.clear()
        self.contact_input.clear()
        self.cnic_input.clear()
        self.company_input.clear()
        self.address_input.clear()
        self.email_input.clear()
        self.credit_limit_input.setValue(0.0)
        self.customer_type_combo.setCurrentIndex(0)
        self.discount_input.setValue(0.0)
        self.notes_input.clear()
        
        # Clear statistics
        self.total_purchases_label.setText("Total Purchases: $0.00")
        self.current_balance_label.setText("Current Balance: $0.00")
        self.last_purchase_label.setText("Last Purchase: Never")
        
        # Clear history
        self.history_table.setRowCount(0)
        
        # Disable action buttons
        self.edit_customer_btn.setEnabled(False)
        self.delete_customer_btn.setEnabled(False)
        self.add_payment_btn.setEnabled(False)
        self.add_credit_btn.setEnabled(False)
        
        # Clear selection
        self.customer_table.clearSelection()
    
    def add_payment(self):
        """Add payment transaction"""
        if not self.current_customer_id:
            return
        
        dialog = CustomerTransactionDialog(self, self.current_customer_id, "PAYMENT")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_customer_details(self.current_customer_id)
            self.load_customers()
    
    def add_credit(self):
        """Add credit transaction"""
        if not self.current_customer_id:
            return
        
        dialog = CustomerTransactionDialog(self, self.current_customer_id, "CREDIT")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_customer_details(self.current_customer_id)
            self.load_customers()
    
    def export_customers(self):
        """Export customers to CSV"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Customers", f"customers_{timestamp}.csv",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                conn = sqlite3.connect(self.db_manager.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT name, contact_number, cnic_tax_id, company_name, address,
                           email, customer_type, credit_limit, current_balance,
                           discount_percentage, total_purchases, last_purchase_date, notes
                    FROM customers
                    ORDER BY name
                ''')
                
                customers = cursor.fetchall()
                conn.close()
                
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write headers
                    headers = ['Name', 'Contact', 'CNIC/Tax ID', 'Company', 'Address',
                              'Email', 'Type', 'Credit Limit', 'Current Balance',
                              'Discount %', 'Total Purchases', 'Last Purchase', 'Notes']
                    writer.writerow(headers)
                    
                    # Write data
                    for customer in customers:
                        writer.writerow(customer)
                
                QMessageBox.information(self, "Success", f"Customers exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export customers: {str(e)}")
    
    def show_customer_report(self):
        """Show customer report dialog"""
        dialog = CustomerReportDialog(self)
        dialog.exec()


class CustomerTransactionDialog(QDialog):
    """Dialog for adding customer transactions (payments/credits)"""
    
    def __init__(self, parent=None, customer_id=None, transaction_type="PAYMENT"):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else parent.db_manager
        self.customer_id = customer_id
        self.transaction_type = transaction_type
        self.init_ui()
    
    def init_ui(self):
        title = "Add Payment" if self.transaction_type == "PAYMENT" else "Add Credit"
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Transaction details
        details_group = QFrame()
        details_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        details_layout = QVBoxLayout()
        
        details_title = QLabel(f"{title} Details")
        details_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        details_layout.addWidget(details_title)
        
        # Amount
        amount_layout = QHBoxLayout()
        amount_label = QLabel("Amount:*")
        amount_label.setMinimumWidth(80)
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(999999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("$")
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.amount_input)
        details_layout.addLayout(amount_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setMinimumWidth(80)
        self.description_input = QLineEdit()
        if self.transaction_type == "PAYMENT":
            self.description_input.setPlaceholderText("Payment received...")
        else:
            self.description_input.setPlaceholderText("Credit adjustment...")
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.description_input)
        details_layout.addLayout(desc_layout)
        
        # Reference
        ref_layout = QHBoxLayout()
        ref_label = QLabel("Reference:")
        ref_label.setMinimumWidth(80)
        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Receipt number, check number, etc.")
        ref_layout.addWidget(ref_label)
        ref_layout.addWidget(self.reference_input)
        details_layout.addLayout(ref_layout)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton(f"💾 Save {title}")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        save_btn.clicked.connect(self.save_transaction)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def save_transaction(self):
        """Save the transaction"""
        amount = self.amount_input.value()
        description = self.description_input.text().strip()
        reference = self.reference_input.text().strip()
        
        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than 0!")
            return
        
        if not description:
            description = f"{self.transaction_type.title()} transaction"
        
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Add transaction
            cursor.execute('''
                INSERT INTO customer_transactions 
                (customer_id, transaction_type, amount, description, reference_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.customer_id, self.transaction_type, amount, description, reference))
            
            # Update customer balance
            if self.transaction_type == "PAYMENT":
                # Payment reduces balance (customer paid money)
                cursor.execute('''
                    UPDATE customers 
                    SET current_balance = current_balance - ?
                    WHERE id = ?
                ''', (amount, self.customer_id))
            else:  # CREDIT
                # Credit reduces balance (we gave customer credit)
                cursor.execute('''
                    UPDATE customers 
                    SET current_balance = current_balance - ?
                    WHERE id = ?
                ''', (amount, self.customer_id))
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", 
                                  f"{self.transaction_type.title()} of ${amount:.2f} saved successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save transaction: {str(e)}")


class CustomerReportDialog(QDialog):
    """Customer Report Dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else parent.db_manager
        self.init_ui()
        self.generate_report()
    
    def init_ui(self):
        self.setWindowTitle("Customer Report")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Report options
        options_layout = QHBoxLayout()
        
        report_type_label = QLabel("Report Type:")
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Summary Report",
            "Top Customers",
            "Outstanding Balances", 
            "Customer Activity"
        ])
        
        generate_btn = QPushButton("📊 Generate Report")
        generate_btn.clicked.connect(self.generate_report)
        
        options_layout.addWidget(report_type_label)
        options_layout.addWidget(self.report_type_combo)
        options_layout.addWidget(generate_btn)
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # Report display
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.report_text)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export Report")
        export_btn.clicked.connect(self.export_report)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.close)
        
        buttons_layout.addWidget(export_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def generate_report(self):
        """Generate the selected report"""
        report_type = self.report_type_combo.currentText()
        
        try:
            if report_type == "Summary Report":
                self.generate_summary_report()
            elif report_type == "Top Customers":
                self.generate_top_customers_report()
            elif report_type == "Outstanding Balances":
                self.generate_outstanding_balances_report()
            elif report_type == "Customer Activity":
                self.generate_activity_report()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
    
    def generate_summary_report(self):
        """Generate customer summary report"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Get summary statistics
        cursor.execute('SELECT COUNT(*) FROM customers')
        total_customers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM customers WHERE customer_type = "VIP"')
        vip_customers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM customers WHERE current_balance > 0')
        customers_with_balance = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(current_balance) FROM customers WHERE current_balance > 0')
        total_outstanding = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(total_purchases) FROM customers')
        total_sales = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(total_purchases) FROM customers WHERE total_purchases > 0')
        avg_purchase = cursor.fetchone()[0] or 0
        
        conn.close()
        
        report = f"""
CUSTOMER SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

CUSTOMER STATISTICS:
• Total Customers: {total_customers:,}
• VIP Customers: {vip_customers:,}
• Regular Customers: {total_customers - vip_customers:,}

FINANCIAL OVERVIEW:
• Customers with Outstanding Balance: {customers_with_balance:,}
• Total Outstanding Amount: ${total_outstanding:,.2f}
• Total Sales to Date: ${total_sales:,.2f}
• Average Purchase per Customer: ${avg_purchase:,.2f}

CUSTOMER BREAKDOWN BY TYPE:
"""
        
        # Add customer type breakdown
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT customer_type, COUNT(*), SUM(total_purchases), SUM(current_balance)
            FROM customers
            GROUP BY customer_type
            ORDER BY COUNT(*) DESC
        ''')
        
        type_stats = cursor.fetchall()
        conn.close()
        
        for cust_type, count, sales, balance in type_stats:
            report += f"• {cust_type}: {count:,} customers, ${sales or 0:,.2f} sales, ${balance or 0:,.2f} balance\n"
        
        self.report_text.setPlainText(report)
    
    def generate_top_customers_report(self):
        """Generate top customers report"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, company_name, total_purchases, current_balance, customer_type
            FROM customers
            WHERE total_purchases > 0
            ORDER BY total_purchases DESC
            LIMIT 20
        ''')
        
        top_customers = cursor.fetchall()
        conn.close()
        
        report = f"""
TOP CUSTOMERS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

TOP 20 CUSTOMERS BY TOTAL PURCHASES:

{'Rank':<4} {'Customer Name':<20} {'Company':<15} {'Purchases':<12} {'Balance':<10} {'Type':<8}
{'-'*70}
"""
        
        for i, (name, company, purchases, balance, cust_type) in enumerate(top_customers, 1):
            company_short = (company or "")[:14]
            name_short = name[:19]
            report += f"{i:<4} {name_short:<20} {company_short:<15} ${purchases:>10.2f} ${balance:>8.2f} {cust_type:<8}\n"
        
        self.report_text.setPlainText(report)
    
    def generate_outstanding_balances_report(self):
        """Generate outstanding balances report"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, company_name, contact_number, current_balance, credit_limit
            FROM customers
            WHERE current_balance > 0
            ORDER BY current_balance DESC
        ''')
        
        outstanding = cursor.fetchall()
        conn.close()
        
        total_outstanding = sum(balance for _, _, _, balance, _ in outstanding)
        
        report = f"""
OUTSTANDING BALANCES REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

CUSTOMERS WITH OUTSTANDING BALANCES:
Total Outstanding Amount: ${total_outstanding:,.2f}
Number of Customers: {len(outstanding):,}

{'Customer Name':<20} {'Company':<15} {'Contact':<12} {'Balance':<10} {'Credit Limit':<12}
{'-'*80}
"""
        
        for name, company, contact, balance, credit_limit in outstanding:
            company_short = (company or "")[:14]
            contact_short = (contact or "")[:11]
            name_short = name[:19]
            report += f"{name_short:<20} {company_short:<15} {contact_short:<12} ${balance:>8.2f} ${credit_limit:>10.2f}\n"
        
        self.report_text.setPlainText(report)
    
    def generate_activity_report(self):
        """Generate customer activity report"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Recent activity
        cursor.execute('''
            SELECT c.name, ct.transaction_date, ct.transaction_type, ct.amount, ct.description
            FROM customer_transactions ct
            JOIN customers c ON ct.customer_id = c.id
            ORDER BY ct.transaction_date DESC
            LIMIT 50
        ''')
        
        recent_activity = cursor.fetchall()
        conn.close()
        
        report = f"""
CUSTOMER ACTIVITY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

RECENT CUSTOMER TRANSACTIONS (Last 50):

{'Date':<12} {'Customer':<20} {'Type':<8} {'Amount':<10} {'Description':<25}
{'-'*80}
"""
        
        for name, date, trans_type, amount, description in recent_activity:
            try:
                date_obj = datetime.fromisoformat(date)
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except:
                formatted_date = str(date)[:10]
            
            name_short = name[:19]
            desc_short = (description or "")[:24]
            report += f"{formatted_date:<12} {name_short:<20} {trans_type:<8} ${amount:>8.2f} {desc_short:<25}\n"
        
        self.report_text.setPlainText(report)
    
    def export_report(self):
        """Export report to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_type = self.report_type_combo.currentText().replace(' ', '_').lower()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Report", f"customer_{report_type}_{timestamp}.txt",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_text.toPlainText())
                
                QMessageBox.information(self, "Success", f"Report exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export report: {str(e)}")


class CustomerSelectionDialog(QDialog):
    """Dialog for selecting customer during POS sale"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.selected_customer = None
        self.init_ui()
        self.load_customers()
    
    def init_ui(self):
        self.setWindowTitle("Select Customer")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Customer name, contact, or company...")
        self.search_input.textChanged.connect(self.filter_customers)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Customer list
        self.customer_list = QTableWidget()
        self.customer_list.setColumnCount(5)
        self.customer_list.setHorizontalHeaderLabels(['ID', 'Name', 'Contact', 'Company', 'Balance'])
        
        # Set column properties
        header = self.customer_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.customer_list.setColumnWidth(0, 50)
        self.customer_list.setColumnWidth(2, 120)
        self.customer_list.setColumnWidth(4, 100)
        self.customer_list.setColumnHidden(0, True)
        
        self.customer_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_list.setAlternatingRowColors(True)
        self.customer_list.itemDoubleClicked.connect(self.select_customer)
        
        layout.addWidget(self.customer_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        select_btn = QPushButton("✓ Select Customer")
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        select_btn.clicked.connect(self.select_customer)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        no_customer_btn = QPushButton("👤 No Customer")
        no_customer_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        no_customer_btn.clicked.connect(self.no_customer)
        
        buttons_layout.addWidget(select_btn)
        buttons_layout.addWidget(no_customer_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def load_customers(self):
        """Load customers into list"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, contact_number, company_name, current_balance
                FROM customers
                ORDER BY name
            ''')
            
            customers = cursor.fetchall()
            conn.close()
            
            self.customer_list.setRowCount(len(customers))
            
            for row, (cust_id, name, contact, company, balance) in enumerate(customers):
                self.customer_list.setItem(row, 0, QTableWidgetItem(str(cust_id)))
                self.customer_list.setItem(row, 1, QTableWidgetItem(name or ""))
                self.customer_list.setItem(row, 2, QTableWidgetItem(contact or ""))
                self.customer_list.setItem(row, 3, QTableWidgetItem(company or ""))
                
                balance_item = QTableWidgetItem(f"${balance:.2f}")
                if balance > 0:
                    balance_item.setForeground(QColor("#dc3545"))
                elif balance < 0:
                    balance_item.setForeground(QColor("#28a745"))
                self.customer_list.setItem(row, 4, balance_item)
            
        except Exception as e:
            print(f"Error loading customers: {e}")
    
    def filter_customers(self):
        """Filter customers based on search"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.customer_list.rowCount()):
            show_row = True
            
            if search_text:
                name = self.customer_list.item(row, 1).text().lower()
                contact = self.customer_list.item(row, 2).text().lower() 
                company = self.customer_list.item(row, 3).text().lower()
                
                if not (search_text in name or search_text in contact or search_text in company):
                    show_row = False
            
            self.customer_list.setRowHidden(row, not show_row)
    
    def select_customer(self):
        """Select the chosen customer"""
        current_row = self.customer_list.currentRow()
        if current_row >= 0:
            customer_id = int(self.customer_list.item(current_row, 0).text())
            customer_name = self.customer_list.item(current_row, 1).text()
            
            self.selected_customer = {
                'id': customer_id,
                'name': customer_name
            }
            
            self.accept()
    
    def no_customer(self):
        """Proceed without selecting a customer"""
        self.selected_customer = None
        self.accept()


# Update POSMainWindow methods
def open_customer_management(self):
    """Open customer management dialog"""
    try:
        dialog = CustomerManagementDialog(self)
        dialog.exec()
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open customer management: {str(e)}")

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
                QMessageBox.information(self, "Customer Selected", 
                                      f"Customer: {dialog.selected_customer['name']}")
            else:
                self.current_customer = None
                self.statusBar().showMessage("No customer selected", 2000)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open customer selection: {str(e)}")