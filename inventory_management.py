import csv  # Add this import
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, 
                             QFrame, QScrollArea, QCheckBox, QComboBox,
                             QMessageBox, QSplitter, QHeaderView, QMenuBar,
                             QDialog, QDialogButtonBox, QTextEdit, QSpinBox,
                             QDoubleSpinBox, QInputDialog, QFileDialog,
                             QListWidget, QColorDialog)  #

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QAction, QKeySequence, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime
from product_management import DatabaseManager
import sqlite3
import json
import os
import tempfile
import subprocess
class InventoryManagementDialog(QDialog):
    """Comprehensive Inventory Management Dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.init_database_tables()
        self.init_ui()
        self.load_inventory()
        
    def init_database_tables(self):
        """Initialize additional database tables for inventory tracking"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Add missing columns to products table if they don't exist
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN purchase_price REAL DEFAULT 0.0')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN wholesale_price REAL DEFAULT 0.0')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN min_stock_threshold INTEGER DEFAULT 10')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN supplier TEXT DEFAULT ""')
            except sqlite3.OperationalError:
                pass
            
            # Stock movements table for tracking changes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    movement_type TEXT CHECK(movement_type IN ('IN', 'OUT', 'ADJUSTMENT')),
                    quantity_change INTEGER,
                    old_quantity INTEGER,
                    new_quantity INTEGER,
                    reason TEXT,
                    reference_number TEXT,
                    movement_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'POS User',
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error initializing inventory tables: {e}")
    
    def init_ui(self):
        self.setWindowTitle("Inventory Management")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Search and filter
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Product name, barcode, or supplier...")
        self.search_input.textChanged.connect(self.filter_inventory)
        
        # Filter options
        filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Products",
            "Low Stock",
            "Out of Stock", 
            "In Stock",
            "High Value Items"
        ])
        self.filter_combo.currentTextChanged.connect(self.filter_inventory)
        
        # Category filter
        category_label = QLabel("Category:")
        self.category_filter = QComboBox()
        self.load_category_filter()
        self.category_filter.currentTextChanged.connect(self.filter_inventory)
        
        toolbar_layout.addWidget(search_label)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(filter_label)
        toolbar_layout.addWidget(self.filter_combo)
        toolbar_layout.addWidget(category_label)
        toolbar_layout.addWidget(self.category_filter)
        toolbar_layout.addStretch()
        
        # Action buttons
        self.stock_adjust_btn = QPushButton("📦 Stock Adjustment")
        self.stock_adjust_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #357ABD; }
        """)
        self.stock_adjust_btn.clicked.connect(self.open_stock_adjustment)
        
        self.stock_history_btn = QPushButton("📊 Stock History")
        self.stock_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #138496; }
        """)
        self.stock_history_btn.clicked.connect(self.show_stock_history)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_inventory)
        
        toolbar_layout.addWidget(self.stock_adjust_btn)
        toolbar_layout.addWidget(self.stock_history_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Inventory table
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(12)
        self.inventory_table.setHorizontalHeaderLabels([
            'ID', 'Product Name', 'Barcode', 'Category', 'Current Stock',
            'Min Threshold', 'Purchase Price', 'Wholesale Price', 'Sale Price',
            'Stock Value', 'Supplier', 'Status'
        ])
        
        # Set column properties
        header = self.inventory_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Product Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Barcode
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Category
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Stock
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Min Threshold
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Purchase Price
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Wholesale Price
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Sale Price
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)  # Stock Value
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)  # Supplier
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)  # Status
        
        # Set column widths
        self.inventory_table.setColumnWidth(0, 50)   # ID
        self.inventory_table.setColumnWidth(2, 120)  # Barcode
        self.inventory_table.setColumnWidth(3, 100)  # Category
        self.inventory_table.setColumnWidth(4, 80)   # Stock
        self.inventory_table.setColumnWidth(5, 80)   # Min Threshold
        self.inventory_table.setColumnWidth(6, 90)   # Purchase Price
        self.inventory_table.setColumnWidth(7, 100)  # Wholesale Price
        self.inventory_table.setColumnWidth(8, 90)   # Sale Price
        self.inventory_table.setColumnWidth(9, 100)  # Stock Value
        self.inventory_table.setColumnWidth(10, 120) # Supplier
        self.inventory_table.setColumnWidth(11, 80)  # Status
        
        # Hide ID column
        self.inventory_table.setColumnHidden(0, True)
        
        # Table properties
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setSortingEnabled(True)
        
        # Double-click to adjust stock
        self.inventory_table.itemDoubleClicked.connect(self.quick_stock_adjustment)
        
        main_layout.addWidget(self.inventory_table)
        
        # Summary panel
        summary_layout = QHBoxLayout()
        
        # Statistics
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        stats_layout = QHBoxLayout()
        
        self.total_products_label = QLabel("Total Products: 0")
        self.low_stock_label = QLabel("Low Stock: 0")
        self.out_stock_label = QLabel("Out of Stock: 0")
        self.total_value_label = QLabel("Total Value: $0.00")
        
        # Style labels
        for label in [self.total_products_label, self.low_stock_label, 
                     self.out_stock_label, self.total_value_label]:
            label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 8px;
                    font-weight: bold;
                    margin: 2px;
                }
            """)
        
        self.low_stock_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                margin: 2px;
                color: #856404;
            }
        """)
        
        self.out_stock_label.setStyleSheet("""
            QLabel {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                margin: 2px;
                color: #721c24;
            }
        """)
        
        stats_layout.addWidget(self.total_products_label)
        stats_layout.addWidget(self.low_stock_label)
        stats_layout.addWidget(self.out_stock_label)
        stats_layout.addWidget(self.total_value_label)
        stats_layout.addStretch()
        
        stats_frame.setLayout(stats_layout)
        summary_layout.addWidget(stats_frame)
        
        main_layout.addLayout(summary_layout)
        
        # Dialog buttons
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export to CSV")
        export_btn.clicked.connect(self.export_inventory)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.close)
        
        buttons_layout.addWidget(export_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
    
    def load_category_filter(self):
        """Load categories for filter dropdown"""
        try:
            self.category_filter.clear()
            self.category_filter.addItem("All Categories")
            
            categories = self.db_manager.get_categories()
            for cat_id, cat_name, color_code in categories:
                self.category_filter.addItem(cat_name)
                
        except Exception as e:
            print(f"Error loading category filter: {e}")
    
    def load_inventory(self):
        """Load all inventory data"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Get products with category information
            cursor.execute('''
                SELECT p.id, p.name, p.barcode, COALESCE(c.name, 'General') as category,
                       p.quantity, COALESCE(p.min_stock_threshold, 10) as min_threshold,
                       COALESCE(p.purchase_price, 0) as purchase_price,
                       COALESCE(p.wholesale_price, 0) as wholesale_price,
                       p.sale_price, COALESCE(p.supplier, '') as supplier
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.name
            ''')
            
            inventory_data = cursor.fetchall()
            conn.close()
            
            self.display_inventory(inventory_data)
            self.update_summary_statistics(inventory_data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load inventory: {str(e)}")
    
    def display_inventory(self, inventory_data):
        """Display inventory data in table"""
        self.inventory_table.setRowCount(len(inventory_data))
        
        for row, (product_id, name, barcode, category, quantity, min_threshold,
                 purchase_price, wholesale_price, sale_price, supplier) in enumerate(inventory_data):
            
            # ID (hidden)
            self.inventory_table.setItem(row, 0, QTableWidgetItem(str(product_id)))
            
            # Product Name
            self.inventory_table.setItem(row, 1, QTableWidgetItem(name))
            
            # Barcode
            self.inventory_table.setItem(row, 2, QTableWidgetItem(barcode))
            
            # Category
            self.inventory_table.setItem(row, 3, QTableWidgetItem(category))
            
            # Current Stock
            stock_item = QTableWidgetItem(str(quantity))
            if quantity <= 0:
                stock_item.setBackground(QColor("#f8d7da"))  # Red for out of stock
            elif quantity <= min_threshold:
                stock_item.setBackground(QColor("#fff3cd"))  # Yellow for low stock
            else:
                stock_item.setBackground(QColor("#d4edda"))  # Green for good stock
            self.inventory_table.setItem(row, 4, stock_item)
            
            # Min Threshold
            self.inventory_table.setItem(row, 5, QTableWidgetItem(str(min_threshold)))
            
            # Purchase Price
            self.inventory_table.setItem(row, 6, QTableWidgetItem(f"{purchase_price:.2f}"))
            
            # Wholesale Price
            self.inventory_table.setItem(row, 7, QTableWidgetItem(f"{wholesale_price:.2f}"))
            
            # Sale Price
            self.inventory_table.setItem(row, 8, QTableWidgetItem(f"{sale_price:.2f}"))
            
            # Stock Value (quantity * purchase_price)
            stock_value = quantity * purchase_price
            self.inventory_table.setItem(row, 9, QTableWidgetItem(f"{stock_value:.2f}"))
            
            # Supplier
            self.inventory_table.setItem(row, 10, QTableWidgetItem(supplier))
            
            # Status
            if quantity <= 0:
                status = "Out of Stock"
                status_color = QColor("#dc3545")
            elif quantity <= min_threshold:
                status = "Low Stock"
                status_color = QColor("#ffc107")
            else:
                status = "In Stock"
                status_color = QColor("#28a745")
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(status_color)
            self.inventory_table.setItem(row, 11, status_item)
    
    def update_summary_statistics(self, inventory_data):
        """Update summary statistics"""
        total_products = len(inventory_data)
        low_stock_count = 0
        out_stock_count = 0
        total_value = 0.0
        
        for (product_id, name, barcode, category, quantity, min_threshold,
             purchase_price, wholesale_price, sale_price, supplier) in inventory_data:
            
            if quantity <= 0:
                out_stock_count += 1
            elif quantity <= min_threshold:
                low_stock_count += 1
            
            total_value += quantity * purchase_price
        
        self.total_products_label.setText(f"Total Products: {total_products}")
        self.low_stock_label.setText(f"Low Stock: {low_stock_count}")
        self.out_stock_label.setText(f"Out of Stock: {out_stock_count}")
        self.total_value_label.setText(f"Total Value: ${total_value:.2f}")
    
    def filter_inventory(self):
        """Filter inventory based on search and filter criteria"""
        search_text = self.search_input.text().lower()
        filter_option = self.filter_combo.currentText()
        category_filter = self.category_filter.currentText()
        
        for row in range(self.inventory_table.rowCount()):
            show_row = True
            
            # Search filter
            if search_text:
                name = self.inventory_table.item(row, 1).text().lower()
                barcode = self.inventory_table.item(row, 2).text().lower()
                supplier = self.inventory_table.item(row, 10).text().lower()
                
                if not (search_text in name or search_text in barcode or search_text in supplier):
                    show_row = False
            
            # Category filter
            if show_row and category_filter != "All Categories":
                category = self.inventory_table.item(row, 3).text()
                if category != category_filter:
                    show_row = False
            
            # Stock level filter
            if show_row and filter_option != "All Products":
                quantity = int(self.inventory_table.item(row, 4).text())
                min_threshold = int(self.inventory_table.item(row, 5).text())
                purchase_price = float(self.inventory_table.item(row, 6).text())
                
                if filter_option == "Low Stock" and quantity > min_threshold:
                    show_row = False
                elif filter_option == "Out of Stock" and quantity > 0:
                    show_row = False
                elif filter_option == "In Stock" and quantity <= 0:
                    show_row = False
                elif filter_option == "High Value Items" and (quantity * purchase_price) < 500:
                    show_row = False
            
            self.inventory_table.setRowHidden(row, not show_row)
    
    def quick_stock_adjustment(self, item):
        """Quick stock adjustment on double-click"""
        row = item.row()
        product_id = int(self.inventory_table.item(row, 0).text())
        product_name = self.inventory_table.item(row, 1).text()
        current_stock = int(self.inventory_table.item(row, 4).text())
        
        self.open_stock_adjustment(product_id, product_name, current_stock)
    
    def open_stock_adjustment(self, product_id=None, product_name=None, current_stock=None):
        """Open stock adjustment dialog"""
        dialog = StockAdjustmentDialog(self, product_id, product_name, current_stock)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_inventory()  # Refresh inventory
            if self.parent_window:
                self.parent_window.load_products_from_database()  # Refresh main window
    
    def show_stock_history(self):
        """Show stock movement history"""
        current_row = self.inventory_table.currentRow()
        product_id = None
        
        if current_row >= 0:
            product_id = int(self.inventory_table.item(current_row, 0).text())
        
        dialog = StockHistoryDialog(self, product_id)
        dialog.exec()
    
    def export_inventory(self):
        """Export inventory to CSV"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Inventory", f"inventory_{timestamp}.csv",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    import csv
                    writer = csv.writer(csvfile)
                    
                    # Write headers
                    headers = []
                    for col in range(1, self.inventory_table.columnCount()):  # Skip ID column
                        headers.append(self.inventory_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # Write data
                    for row in range(self.inventory_table.rowCount()):
                        if not self.inventory_table.isRowHidden(row):
                            row_data = []
                            for col in range(1, self.inventory_table.columnCount()):  # Skip ID column
                                item = self.inventory_table.item(row, col)
                                row_data.append(item.text() if item else "")
                            writer.writerow(row_data)
                
                QMessageBox.information(self, "Success", f"Inventory exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export inventory: {str(e)}")


class StockAdjustmentDialog(QDialog):
    """Stock Adjustment Dialog"""
    
    def __init__(self, parent=None, product_id=None, product_name=None, current_stock=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.product_id = product_id
        self.product_name = product_name
        self.current_stock = current_stock
        self.init_ui()
        
        if product_id:
            self.load_product_details()
    
    def init_ui(self):
        self.setWindowTitle("Stock Adjustment")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Product selection
        product_group = QFrame()
        product_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        product_layout = QVBoxLayout()
        
        product_title = QLabel("Product Selection")
        product_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        product_layout.addWidget(product_title)
        
        # Product search/selection
        search_layout = QHBoxLayout()
        search_label = QLabel("Product:")
        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        self.product_combo.setPlaceholderText("Search or select product...")
        self.load_products()
        self.product_combo.currentTextChanged.connect(self.on_product_selected)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.product_combo)
        product_layout.addLayout(search_layout)
        
        # Current stock display
        self.current_stock_label = QLabel("Current Stock: 0")
        self.current_stock_label.setStyleSheet("""
            QLabel {
                background-color: #e9ecef;
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        product_layout.addWidget(self.current_stock_label)
        
        product_group.setLayout(product_layout)
        layout.addWidget(product_group)
        
        # Adjustment details
        adjustment_group = QFrame()
        adjustment_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        adjustment_layout = QVBoxLayout()
        
        adjustment_title = QLabel("Stock Adjustment Details")
        adjustment_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        adjustment_layout.addWidget(adjustment_title)
        
        # Adjustment type
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        self.adjustment_type = QComboBox()
        self.adjustment_type.addItems([
            "Stock In (Add Stock)",
            "Stock Out (Remove Stock)", 
            "Adjustment (Set Exact Amount)"
        ])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.adjustment_type)
        adjustment_layout.addLayout(type_layout)
        
        # Quantity
        qty_layout = QHBoxLayout()
        qty_label = QLabel("Quantity:")
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999999)
        self.quantity_input.setValue(1)
        qty_layout.addWidget(qty_label)
        qty_layout.addWidget(self.quantity_input)
        adjustment_layout.addLayout(qty_layout)
        
        # Reason
        reason_layout = QHBoxLayout()
        reason_label = QLabel("Reason:")
        self.reason_combo = QComboBox()
        self.reason_combo.setEditable(True)
        self.reason_combo.addItems([
            "Received new stock",
            "Sold to customer",
            "Damaged goods",
            "Expired products",
            "Theft/Loss",
            "Count correction",
            "Transfer to another location",
            "Return from customer",
            "Initial stock entry",
            "Other"
        ])
        reason_layout.addWidget(reason_label)
        reason_layout.addWidget(self.reason_combo)
        adjustment_layout.addLayout(reason_layout)
        
        # Reference number
        ref_layout = QHBoxLayout()
        ref_label = QLabel("Reference:")
        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Invoice number, PO number, etc.")
        ref_layout.addWidget(ref_label)
        ref_layout.addWidget(self.reference_input)
        adjustment_layout.addLayout(ref_layout)
        
        # Notes
        notes_label = QLabel("Notes:")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Additional notes...")
        adjustment_layout.addWidget(notes_label)
        adjustment_layout.addWidget(self.notes_input)
        
        # New stock preview
        self.new_stock_label = QLabel("New Stock: 0")
        self.new_stock_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
                color: #155724;
            }
        """)
        adjustment_layout.addWidget(self.new_stock_label)
        
        # Update preview when values change
        self.adjustment_type.currentTextChanged.connect(self.update_preview)
        self.quantity_input.valueChanged.connect(self.update_preview)
        
        adjustment_group.setLayout(adjustment_layout)
        layout.addWidget(adjustment_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Adjustment")
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_adjustment)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def load_products(self):
        """Load all products into combo box"""
        try:
            products = self.db_manager.get_all_products()
            self.product_combo.clear()
            
            for product in products:
                product_id, name, barcode = product[0], product[1], product[2]
                display_text = f"{name} ({barcode})"
                self.product_combo.addItem(display_text, product_id)
                
        except Exception as e:
            print(f"Error loading products: {e}")
    
    def load_product_details(self):
        """Load details for pre-selected product"""
        if self.product_id and self.product_name:
            # Find and select the product in combo box
            for i in range(self.product_combo.count()):
                if self.product_combo.itemData(i) == self.product_id:
                    self.product_combo.setCurrentIndex(i)
                    break
            
            self.current_stock_label.setText(f"Current Stock: {self.current_stock}")
            self.update_preview()
    
    def on_product_selected(self):
        """Handle product selection"""
        current_index = self.product_combo.currentIndex()
        if current_index >= 0:
            self.product_id = self.product_combo.itemData(current_index)
            if self.product_id:
                # Get current stock
                try:
                    conn = sqlite3.connect(self.db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT quantity FROM products WHERE id = ?', (self.product_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        self.current_stock = result[0]
                        self.current_stock_label.setText(f"Current Stock: {self.current_stock}")
                        self.update_preview()
                        
                except Exception as e:
                    print(f"Error getting current stock: {e}")
    
    def update_preview(self):
        """Update new stock preview"""
        if self.current_stock is None:
            return
            
        adjustment_type = self.adjustment_type.currentText()
        quantity = self.quantity_input.value()
        
        if "Stock In" in adjustment_type:
            new_stock = self.current_stock + quantity
        elif "Stock Out" in adjustment_type:
            new_stock = max(0, self.current_stock - quantity)
        else:  # Adjustment
            new_stock = quantity
        
        self.new_stock_label.setText(f"New Stock: {new_stock}")
        
        # Color coding
        if new_stock < self.current_stock:
            self.new_stock_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 5px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 12px;
                    color: #721c24;
                }
            """)
        else:
            self.new_stock_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 5px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 12px;
                    color: #155724;
                }
            """)
    
    def save_adjustment(self):
        """Save stock adjustment"""
        if not self.product_id:
            QMessageBox.warning(self, "Validation Error", "Please select a product!")
            return
        
        if self.current_stock is None:
            QMessageBox.warning(self, "Error", "Unable to determine current stock!")
            return
        
        adjustment_type = self.adjustment_type.currentText()
        quantity = self.quantity_input.value()
        reason = self.reason_combo.currentText()
        reference = self.reference_input.text().strip()
        notes = self.notes_input.toPlainText().strip()
        
        # Calculate new stock
        if "Stock In" in adjustment_type:
            new_stock = self.current_stock + quantity
            quantity_change = quantity
            movement_type = "IN"
        elif "Stock Out" in adjustment_type:
            new_stock = max(0, self.current_stock - quantity)
            quantity_change = -quantity
            movement_type = "OUT"
        else:  # Adjustment
            new_stock = quantity
            quantity_change = quantity - self.current_stock
            movement_type = "ADJUSTMENT"
        
        if not reason:
            QMessageBox.warning(self, "Validation Error", "Please provide a reason for the adjustment!")
            return
        
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Update product stock
            cursor.execute('UPDATE products SET quantity = ? WHERE id = ?',
                         (new_stock, self.product_id))
            
            # Record stock movement
            cursor.execute('''
                INSERT INTO stock_movements 
                (product_id, movement_type, quantity_change, old_quantity, new_quantity,
                 reason, reference_number, notes, movement_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.product_id, movement_type, quantity_change, self.current_stock,
                  new_stock, reason, reference, notes, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", 
                                  f"Stock adjustment saved successfully!\n\n"
                                  f"Old Stock: {self.current_stock}\n"
                                  f"New Stock: {new_stock}\n"
                                  f"Change: {quantity_change:+d}")
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save stock adjustment: {str(e)}")


class StockHistoryDialog(QDialog):
    """Stock Movement History Dialog"""
    
    def __init__(self, parent=None, product_id=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.product_id = product_id
        self.init_ui()
        self.load_history()
    
    def init_ui(self):
        self.setWindowTitle("Stock Movement History")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Product filter
        product_label = QLabel("Product:")
        self.product_filter = QComboBox()
        self.product_filter.addItem("All Products", None)
        self.load_product_filter()
        self.product_filter.currentIndexChanged.connect(self.load_history)
        
        # Date range
        date_label = QLabel("Date Range:")
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("YYYY-MM-DD")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("YYYY-MM-DD")
        
        filter_btn = QPushButton("Filter")
        filter_btn.clicked.connect(self.load_history)
        
        filter_layout.addWidget(product_label)
        filter_layout.addWidget(self.product_filter)
        filter_layout.addWidget(date_label)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("to"))
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(filter_btn)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            'Date', 'Product', 'Type', 'Change', 'Old Stock', 'New Stock',
            'Reason', 'Reference', 'Notes'
        ])
        
        # Set column properties
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Product
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Change
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Old Stock
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # New Stock
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Reason
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Reference
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # Notes
        
        self.history_table.setColumnWidth(0, 130)  # Date
        self.history_table.setColumnWidth(2, 80)   # Type
        self.history_table.setColumnWidth(3, 70)   # Change
        self.history_table.setColumnWidth(4, 80)   # Old Stock
        self.history_table.setColumnWidth(5, 80)   # New Stock
        self.history_table.setColumnWidth(7, 100)  # Reference
        
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True)
        
        layout.addWidget(self.history_table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export")
        export_btn.clicked.connect(self.export_history)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.close)
        
        buttons_layout.addWidget(export_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def load_product_filter(self):
        """Load products for filter"""
        try:
            products = self.db_manager.get_all_products()
            for product_id, name, barcode in [(p[0], p[1], p[2]) for p in products]:
                self.product_filter.addItem(f"{name} ({barcode})", product_id)
            
            # Select specific product if provided
            if self.product_id:
                for i in range(self.product_filter.count()):
                    if self.product_filter.itemData(i) == self.product_id:
                        self.product_filter.setCurrentIndex(i)
                        break
                        
        except Exception as e:
            print(f"Error loading product filter: {e}")
    
    def load_history(self):
        """Load stock movement history"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Build query based on filters
            query = '''
                SELECT sm.movement_date, p.name, sm.movement_type, sm.quantity_change,
                       sm.old_quantity, sm.new_quantity, sm.reason, sm.reference_number,
                       sm.notes
                FROM stock_movements sm
                JOIN products p ON sm.product_id = p.id
                WHERE 1=1
            '''
            params = []
            
            # Product filter
            selected_product_id = self.product_filter.currentData()
            if selected_product_id:
                query += ' AND sm.product_id = ?'
                params.append(selected_product_id)
            
            # Date range filter
            date_from = self.date_from.text().strip()
            date_to = self.date_to.text().strip()
            
            if date_from:
                query += ' AND DATE(sm.movement_date) >= ?'
                params.append(date_from)
            
            if date_to:
                query += ' AND DATE(sm.movement_date) <= ?'
                params.append(date_to)
            
            query += ' ORDER BY sm.movement_date DESC'
            
            cursor.execute(query, params)
            history_data = cursor.fetchall()
            conn.close()
            
            self.display_history(history_data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")
    
    def display_history(self, history_data):
        """Display history data in table"""
        self.history_table.setRowCount(len(history_data))
        
        for row, (date, product, movement_type, change, old_qty, new_qty,
                 reason, reference, notes) in enumerate(history_data):
            
            # Format date
            try:
                date_obj = datetime.fromisoformat(date)
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = str(date)
            
            self.history_table.setItem(row, 0, QTableWidgetItem(formatted_date))
            self.history_table.setItem(row, 1, QTableWidgetItem(product))
            
            # Movement type with color
            type_item = QTableWidgetItem(movement_type)
            if movement_type == "IN":
                type_item.setForeground(QColor("#28a745"))
            elif movement_type == "OUT":
                type_item.setForeground(QColor("#dc3545"))
            else:
                type_item.setForeground(QColor("#ffc107"))
            self.history_table.setItem(row, 2, type_item)
            
            # Quantity change with color
            change_item = QTableWidgetItem(f"{change:+d}")
            if change > 0:
                change_item.setForeground(QColor("#28a745"))
            else:
                change_item.setForeground(QColor("#dc3545"))
            self.history_table.setItem(row, 3, change_item)
            
            self.history_table.setItem(row, 4, QTableWidgetItem(str(old_qty)))
            self.history_table.setItem(row, 5, QTableWidgetItem(str(new_qty)))
            self.history_table.setItem(row, 6, QTableWidgetItem(reason or ""))
            self.history_table.setItem(row, 7, QTableWidgetItem(reference or ""))
            self.history_table.setItem(row, 8, QTableWidgetItem(notes or ""))
    
    def export_history(self):
        """Export history to CSV"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Stock History", f"stock_history_{timestamp}.csv",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    import csv
                    writer = csv.writer(csvfile)
                    
                    # Write headers
                    headers = []
                    for col in range(self.history_table.columnCount()):
                        headers.append(self.history_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # Write data
                    for row in range(self.history_table.rowCount()):
                        row_data = []
                        for col in range(self.history_table.columnCount()):
                            item = self.history_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                
                QMessageBox.information(self, "Success", f"History exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export history: {str(e)}")


# Update POSMainWindow methods
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