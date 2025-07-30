import sys
import sqlite3
import os
from datetime import datetime, date
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QTabWidget, QWidget,
                             QGroupBox, QCheckBox, QScrollArea, QSplitter,
                             QFrame, QProgressBar, QInputDialog, QApplication)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QFont, QIcon
import random
import string

class DatabaseManager:
    """Database manager for product-related operations"""
    
    def __init__(self, db_path="pos_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE NOT NULL,
            stock_type TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            sub_quantity INTEGER DEFAULT 1,
            purchase_price REAL DEFAULT 0.0,
            wholesale_price REAL DEFAULT 0.0,
            sale_price REAL DEFAULT 0.0,
            min_stock_threshold INTEGER DEFAULT 0,
            manufacture_date TEXT,
            expiry_date TEXT,
            shelf_number TEXT,
            category_id INTEGER,
            description TEXT,
            vendor_id INTEGER,
            image_path TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
        ''')
        
        # Categories table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            color_code TEXT DEFAULT '#4A90E2',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Vendors table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            tax_info TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Stock types table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            abbreviation TEXT,
            item_type TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Check if item_type column exists in stock_types table, if not add it
        cursor.execute("PRAGMA table_info(stock_types)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'item_type' not in columns:
            cursor.execute('ALTER TABLE stock_types ADD COLUMN item_type TEXT')
            print("Added item_type column to stock_types table")
        
        # Check if created_date column exists in stock_types table, if not add it
        if 'created_date' not in columns:
            cursor.execute('ALTER TABLE stock_types ADD COLUMN created_date TEXT DEFAULT CURRENT_TIMESTAMP')
            print("Added created_date column to stock_types table")
        
        conn.commit()
        conn.close()
    
    def generate_barcode(self):
        """Generate a unique barcode"""
        while True:
            # Generate 13-digit barcode
            barcode = ''.join(random.choices(string.digits, k=13))
            if not self.barcode_exists(barcode):
                return barcode
            
    def get_products_by_category(self, category_name):
        """Get products by category name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # First, try to get category ID
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_result = cursor.fetchone()
            
            if category_result:
                category_id = category_result[0]
                cursor.execute('''
                    SELECT id, name, barcode, '', quantity, sale_price, '', '', 0 
                    FROM products 
                    WHERE category_id = ?
                    ORDER BY name
                    LIMIT 50
                ''', (category_id,))
            else:
                # If category not found, return empty list
                return []
                
            products = cursor.fetchall()
            return products
            
        except Exception as e:
            print(f"Error getting products by category: {e}")
            return []
        finally:
            conn.close()

    def get_categories(self):
        """Get all categories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create categories table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color_code TEXT DEFAULT '#4A90E2'
                )
            ''')
            
            # Add category_id column to products table if it doesn't exist
            try:
                cursor.execute('ALTER TABLE products ADD COLUMN category_id INTEGER')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Get all categories
            cursor.execute('SELECT id, name, color_code FROM categories ORDER BY name')
            categories = cursor.fetchall()
            
            # If no categories exist, create some default ones
            if not categories:
                default_categories = [
                    ('General', '#4A90E2'),
                    ('Food', '#FF6B6B'),
                    ('Beverages', '#4ECDC4'),
                    ('Electronics', '#45B7D1'),
                    ('Clothing', '#96CEB4'),
                    ('Books', '#FFEAA7')
                ]
                
                for cat_name, cat_color in default_categories:
                    cursor.execute('INSERT OR IGNORE INTO categories (name, color_code) VALUES (?, ?)', 
                                (cat_name, cat_color))
                
                conn.commit()
                
                # Fetch categories again
                cursor.execute('SELECT id, name, color_code FROM categories ORDER BY name')
                categories = cursor.fetchall()
            
            return categories
            
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()
            
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
    
    def barcode_exists(self, barcode):
        """Check if barcode already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM products WHERE barcode = ?', (barcode,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def get_categories(self):
        """Get all categories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, color_code FROM categories ORDER BY name')
        categories = cursor.fetchall()
        conn.close()
        return categories
    
    def get_vendors(self):
        """Get all vendors"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM vendors ORDER BY name')
        vendors = cursor.fetchall()
        conn.close()
        return vendors
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
    
    def get_stock_types(self):
        """Get all stock types"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, abbreviation, item_type FROM stock_types ORDER BY name')
        stock_types = cursor.fetchall()
        conn.close()
        return stock_types
    
    def add_stock_type(self, name, abbreviation="", item_type=""):
        """Add new stock type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO stock_types (name, abbreviation, item_type) VALUES (?, ?, ?)',
                          (name, abbreviation, item_type))
            conn.commit()
            stock_type_id = cursor.lastrowid
            conn.close()
            return stock_type_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def save_product(self, product_data, product_id=None):
        """Save or update product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if product_id:
            # Update existing product
            cursor.execute('''
            UPDATE products SET name=?, barcode=?, stock_type=?, quantity=?, sub_quantity=?,
                               purchase_price=?, wholesale_price=?, sale_price=?, min_stock_threshold=?,
                               manufacture_date=?, expiry_date=?, shelf_number=?, category_id=?,
                               description=?, vendor_id=?, image_path=?, updated_date=CURRENT_TIMESTAMP
            WHERE id=?
            ''', (*product_data, product_id))
        else:
            # Insert new product
            cursor.execute('''
            INSERT INTO products (name, barcode, stock_type, quantity, sub_quantity,
                                 purchase_price, wholesale_price, sale_price, min_stock_threshold,
                                 manufacture_date, expiry_date, shelf_number, category_id,
                                 description, vendor_id, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', product_data)
        
        conn.commit()
        conn.close()
    
    def get_product(self, product_id):
        """Get product by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        return product
    
    def get_all_products(self):
        """Get all products with category and vendor names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT p.id, p.name, p.barcode, p.stock_type, p.quantity, p.sale_price,
               c.name as category_name, v.name as vendor_name, p.min_stock_threshold
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.name
        ''')
        products = cursor.fetchall()
        conn.close()
        return products
    
    def delete_product(self, product_id):
        """Delete product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
    
    def add_category(self, name, description="", color_code="#4A90E2"):
        """Add new category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO categories (name, description, color_code) VALUES (?, ?, ?)',
                          (name, description, color_code))
            conn.commit()
            category_id = cursor.lastrowid
            conn.close()
            return category_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def add_vendor(self, name, contact_person="", address="", phone="", email="", tax_info=""):
        """Add new vendor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO vendors (name, contact_person, address, phone, email, tax_info)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, contact_person, address, phone, email, tax_info))
        conn.commit()
        vendor_id = cursor.lastrowid
        conn.close()
        return vendor_id

class AddStockTypeDialog(QDialog):
    """Dialog for adding new stock types"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Stock Type")
        self.setFixedSize(400, 250)
        self.stock_type_data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout()
        
        # Stock type name
        layout.addWidget(QLabel("Stock Type Name:*"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Piece, Carton, Box")
        layout.addWidget(self.name_edit, 0, 1)
        
        # Abbreviation
        layout.addWidget(QLabel("Abbreviation:"), 1, 0)
        self.abbreviation_edit = QLineEdit()
        self.abbreviation_edit.setPlaceholderText("e.g., PC, CTN, BOX")
        layout.addWidget(self.abbreviation_edit, 1, 1)
        
        # Item type
        layout.addWidget(QLabel("Item Type:"), 2, 0)
        self.item_type_combo = QComboBox()
        item_types = ["Physical", "Digital", "Service", "Subscription", "Bundle"]
        self.item_type_combo.addItems(item_types)
        layout.addWidget(self.item_type_combo, 2, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_stock_type)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.setLayout(layout)
    
    def save_stock_type(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Stock type name is required!")
            return
        
        self.stock_type_data = {
            'name': self.name_edit.text().strip(),
            'abbreviation': self.abbreviation_edit.text().strip(),
            'item_type': self.item_type_combo.currentText()
        }
        self.accept()

class AddCategoryDialog(QDialog):
    """Dialog for adding new categories"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Category")
        self.setFixedSize(400, 200)
        self.category_data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Category name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Category Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter category name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        colors = [
            ("Blue", "#4A90E2"), ("Red", "#FF6B6B"), ("Green", "#4ECDC4"),
            ("Orange", "#FFA500"), ("Purple", "#8A2BE2"), ("Pink", "#FF69B4"),
            ("Teal", "#008080"), ("Brown", "#8B4513")
        ]
        for color_name, color_code in colors:
            self.color_combo.addItem(color_name, color_code)
        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_category)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_category(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Category name is required!")
            return
        
        self.category_data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.text().strip(),
            'color_code': self.color_combo.currentData()
        }
        self.accept()
    """Dialog for adding new categories"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Category")
        self.setFixedSize(400, 200)
        self.category_data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Category name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Category Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter category name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        colors = [
            ("Blue", "#4A90E2"), ("Red", "#FF6B6B"), ("Green", "#4ECDC4"),
            ("Orange", "#FFA500"), ("Purple", "#8A2BE2"), ("Pink", "#FF69B4"),
            ("Teal", "#008080"), ("Brown", "#8B4513")
        ]
        for color_name, color_code in colors:
            self.color_combo.addItem(color_name, color_code)
        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_category)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_category(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Category name is required!")
            return
        
        self.category_data = {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.text().strip(),
            'color_code': self.color_combo.currentData()
        }
        self.accept()

class AddVendorDialog(QDialog):
    """Dialog for adding new vendors"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Vendor")
        self.setFixedSize(500, 300)
        self.vendor_data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout()
        
        # Vendor fields
        fields = [
            ("Vendor Name:", "name_edit", True),
            ("Contact Person:", "contact_edit", False),
            ("Address:", "address_edit", False),
            ("Phone:", "phone_edit", False),
            ("Email:", "email_edit", False),
            ("Tax Info:", "tax_edit", False)
        ]
        
        self.field_widgets = {}
        
        for i, (label, field_name, required) in enumerate(fields):
            label_widget = QLabel(label)
            if required:
                label_widget.setStyleSheet("font-weight: bold; color: red;")
            
            if field_name == "address_edit":
                widget = QTextEdit()
                widget.setMaximumHeight(60)
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(f"Enter {label.lower().replace(':', '')}")
            
            self.field_widgets[field_name] = widget
            layout.addWidget(label_widget, i, 0)
            layout.addWidget(widget, i, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_vendor)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout, len(fields), 0, 1, 2)
        
        self.setLayout(layout)
    
    def save_vendor(self):
        name = self.field_widgets['name_edit'].text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Vendor name is required!")
            return
        
        self.vendor_data = {
            'name': name,
            'contact_person': self.field_widgets['contact_edit'].text().strip(),
            'address': self.field_widgets['address_edit'].toPlainText().strip(),
            'phone': self.field_widgets['phone_edit'].text().strip(),
            'email': self.field_widgets['email_edit'].text().strip(),
            'tax_info': self.field_widgets['tax_edit'].text().strip()
        }
        self.accept()

class ClearOnClickDoubleSpinBox(QDoubleSpinBox):
    """Custom QDoubleSpinBox that clears value when clicked for easy editing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clicked_once = False
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Clear the value on first click for easier data entry
            if not self.clicked_once or self.value() != 0:
                self.setValue(0)
                self.selectAll()
                self.clicked_once = True
        super().mousePressEvent(event)
    
    def focusInEvent(self, event):
        # Select all text when focused for easier editing
        super().focusInEvent(event)
        self.selectAll()
    
    def keyPressEvent(self, event):
        # Reset clicked_once when user starts typing
        if event.text().isdigit() or event.text() == '.':
            self.clicked_once = False
        super().keyPressEvent(event)

class ProductFormWidget(QWidget):
    """Product form widget for adding/editing products"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.product_id = None
        self.init_ui()
        self.load_combo_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Basic Information Group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QGridLayout()
        
        # Product Name
        basic_layout.addWidget(QLabel("Product Name:*"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter product name")
        basic_layout.addWidget(self.name_edit, 0, 1, 1, 2)
        
        # Barcode
        basic_layout.addWidget(QLabel("Barcode:*"), 1, 0)
        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("Enter or generate barcode")
        basic_layout.addWidget(self.barcode_edit, 1, 1)
        
        generate_barcode_btn = QPushButton("Generate")
        generate_barcode_btn.clicked.connect(self.generate_barcode)
        basic_layout.addWidget(generate_barcode_btn, 1, 2)
        
        # Stock Type
        basic_layout.addWidget(QLabel("Stock Type:*"), 2, 0)
        self.stock_type_combo = QComboBox()
        basic_layout.addWidget(self.stock_type_combo, 2, 1)
        
        add_stock_type_btn = QPushButton("Add New")
        add_stock_type_btn.clicked.connect(self.add_stock_type)
        basic_layout.addWidget(add_stock_type_btn, 2, 2)
        
        # Category
        basic_layout.addWidget(QLabel("Category:"), 3, 0)
        self.category_combo = QComboBox()
        basic_layout.addWidget(self.category_combo, 3, 1)
        
        add_category_btn = QPushButton("Add New")
        add_category_btn.clicked.connect(self.add_category)
        basic_layout.addWidget(add_category_btn, 3, 2)
        
        # Vendor
        basic_layout.addWidget(QLabel("Vendor:"), 4, 0)
        self.vendor_combo = QComboBox()
        basic_layout.addWidget(self.vendor_combo, 4, 1)
        
        add_vendor_btn = QPushButton("Add New")
        add_vendor_btn.clicked.connect(self.add_vendor)
        basic_layout.addWidget(add_vendor_btn, 4, 2)
        
        basic_group.setLayout(basic_layout)
        scroll_layout.addWidget(basic_group)
        
        # Pricing Information Group
        pricing_group = QGroupBox("Pricing Information")
        pricing_layout = QGridLayout()
        
        # Purchase Price
        pricing_layout.addWidget(QLabel("Purchase Price:"), 0, 0)
        self.purchase_price_spin = ClearOnClickDoubleSpinBox()
        self.purchase_price_spin.setRange(0, 999999.99)
        self.purchase_price_spin.setDecimals(2)
        self.purchase_price_spin.setSuffix(" Rs")
        self.purchase_price_spin.setToolTip("Click to clear and enter new price")
        pricing_layout.addWidget(self.purchase_price_spin, 0, 1)
        
        # Wholesale Price
        pricing_layout.addWidget(QLabel("Wholesale Price:"), 0, 2)
        self.wholesale_price_spin = ClearOnClickDoubleSpinBox()
        self.wholesale_price_spin.setRange(0, 999999.99)
        self.wholesale_price_spin.setDecimals(2)
        self.wholesale_price_spin.setSuffix(" Rs")
        self.wholesale_price_spin.setToolTip("Click to clear and enter new price")
        pricing_layout.addWidget(self.wholesale_price_spin, 0, 3)
        
        # Sale Price
        pricing_layout.addWidget(QLabel("Sale Price:*"), 1, 0)
        self.sale_price_spin = ClearOnClickDoubleSpinBox()
        self.sale_price_spin.setRange(0, 999999.99)
        self.sale_price_spin.setDecimals(2)
        self.sale_price_spin.setSuffix(" Rs")
        self.sale_price_spin.setToolTip("Click to clear and enter new price")
        pricing_layout.addWidget(self.sale_price_spin, 1, 1)
        
        pricing_group.setLayout(pricing_layout)
        scroll_layout.addWidget(pricing_group)
        
        # Inventory Information Group
        inventory_group = QGroupBox("Inventory Information")
        inventory_layout = QGridLayout()
        
        # Quantity
        inventory_layout.addWidget(QLabel("Quantity:"), 0, 0)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 999999)
        inventory_layout.addWidget(self.quantity_spin, 0, 1)
        
        # Sub-Quantity with checkbox
        self.sub_quantity_checkbox = QCheckBox("Has Sub-Quantity:")
        self.sub_quantity_checkbox.stateChanged.connect(self.toggle_sub_quantity)
        inventory_layout.addWidget(self.sub_quantity_checkbox, 0, 2)
        
        self.sub_quantity_spin = QSpinBox()
        self.sub_quantity_spin.setRange(1, 999999)
        self.sub_quantity_spin.setValue(1)
        self.sub_quantity_spin.setEnabled(False)  # Disabled by default
        inventory_layout.addWidget(self.sub_quantity_spin, 0, 3)
        
        # Minimum Stock Threshold
        inventory_layout.addWidget(QLabel("Min Stock Threshold:"), 1, 0)
        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setRange(0, 999999)
        inventory_layout.addWidget(self.min_stock_spin, 1, 1)
        
        # Shelf Number
        inventory_layout.addWidget(QLabel("Shelf Number:"), 1, 2)
        self.shelf_edit = QLineEdit()
        self.shelf_edit.setPlaceholderText("e.g., A1-B2")
        inventory_layout.addWidget(self.shelf_edit, 1, 3)
        
        inventory_group.setLayout(inventory_layout)
        scroll_layout.addWidget(inventory_group)
        
        # Dates Group
        dates_group = QGroupBox("Date Information")
        dates_layout = QGridLayout()
        
        # Manufacture Date
        dates_layout.addWidget(QLabel("Manufacture Date:"), 0, 0)
        self.manufacture_date = QDateEdit()
        self.manufacture_date.setDate(QDate.currentDate())
        self.manufacture_date.setCalendarPopup(True)
        dates_layout.addWidget(self.manufacture_date, 0, 1)
        
        # Expiry Date
        dates_layout.addWidget(QLabel("Expiry Date:"), 0, 2)
        self.expiry_date = QDateEdit()
        self.expiry_date.setDate(QDate.currentDate().addYears(1))
        self.expiry_date.setCalendarPopup(True)
        dates_layout.addWidget(self.expiry_date, 0, 3)
        
        dates_group.setLayout(dates_layout)
        scroll_layout.addWidget(dates_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Product")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
        """)
        self.save_btn.clicked.connect(self.save_product)
        
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF4444;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_form)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        scroll_layout.addLayout(button_layout)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
    
    def toggle_sub_quantity(self, state):
        """Toggle sub-quantity field based on checkbox state"""
        is_enabled = state == 2  # Qt.CheckState.Checked
        self.sub_quantity_spin.setEnabled(is_enabled)
        if not is_enabled:
            self.sub_quantity_spin.setValue(1)  # Reset to default when disabled
    
    def on_stock_type_changed(self):
        """Handle stock type change to suggest sub-quantity usage"""
        stock_type = self.stock_type_combo.currentData()
        if not stock_type:
            return
        
        # Stock types that typically have sub-quantities
        container_types = ['carton', 'box', 'case', 'pack', 'dozen']
        
        # Check if current stock type suggests sub-quantity
        should_suggest_sub_qty = any(container in stock_type.lower() for container in container_types)
        
        # Auto-suggest but don't force
        if should_suggest_sub_qty and not self.sub_quantity_checkbox.isChecked():
            # Show a subtle hint
            self.sub_quantity_checkbox.setToolTip(
                f"Consider enabling sub-quantity for {stock_type} (e.g., items per {stock_type.lower()})"
            )
            self.sub_quantity_checkbox.setStyleSheet("QCheckBox { color: #4A90E2; font-weight: bold; }")
        else:
            self.sub_quantity_checkbox.setToolTip("Enable if this stock type contains multiple units")
            self.sub_quantity_checkbox.setStyleSheet("")
    
    def load_combo_data(self):
        """Load data into combo boxes"""
        # Load stock types
        self.stock_type_combo.clear()
        self.stock_type_combo.addItem("-- Select Stock Type --", None)  # Add default option
        stock_types = self.db_manager.get_stock_types()
        for stock_type_id, name, abbreviation, item_type in stock_types:
            display_text = f"{name}"
            if abbreviation:
                display_text += f" ({abbreviation})"
            if item_type:
                display_text += f" - {item_type}"
            self.stock_type_combo.addItem(display_text, name)
        
        # Connect stock type change to update sub-quantity logic
        self.stock_type_combo.currentTextChanged.connect(self.on_stock_type_changed)
        
        # Load categories
        self.category_combo.clear()
        self.category_combo.addItem("-- Select Category --", None)
        categories = self.db_manager.get_categories()
        for cat_id, cat_name, color_code in categories:
            self.category_combo.addItem(cat_name, cat_id)
        
        # Load vendors
        self.vendor_combo.clear()
        self.vendor_combo.addItem("-- Select Vendor --", None)
        vendors = self.db_manager.get_vendors()
        for vendor_id, vendor_name in vendors:
            self.vendor_combo.addItem(vendor_name, vendor_id)
    
    def generate_barcode(self):
        """Generate a unique barcode"""
        barcode = self.db_manager.generate_barcode()
        self.barcode_edit.setText(barcode)
    
    def add_stock_type(self):
        """Add new stock type"""
        dialog = AddStockTypeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            stock_data = dialog.stock_type_data
            stock_id = self.db_manager.add_stock_type(
                stock_data['name'], 
                stock_data['abbreviation'], 
                stock_data['item_type']
            )
            if stock_id:
                self.load_combo_data()
                # Select the newly added stock type
                for i in range(self.stock_type_combo.count()):
                    if self.stock_type_combo.itemData(i) == stock_data['name']:
                        self.stock_type_combo.setCurrentIndex(i)
                        break
                QMessageBox.information(self, "Success", "Stock type added successfully!")
            else:
                QMessageBox.warning(self, "Error", "Stock type name already exists!")
    
    def add_category(self):
        """Add new category"""
        dialog = AddCategoryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cat_data = dialog.category_data
            cat_id = self.db_manager.add_category(
                cat_data['name'], 
                cat_data['description'], 
                cat_data['color_code']
            )
            if cat_id:
                self.load_combo_data()
                # Select the newly added category
                for i in range(self.category_combo.count()):
                    if self.category_combo.itemData(i) == cat_id:
                        self.category_combo.setCurrentIndex(i)
                        break
                QMessageBox.information(self, "Success", "Category added successfully!")
            else:
                QMessageBox.warning(self, "Error", "Category name already exists!")
    
    def add_vendor(self):
        """Add new vendor"""
        dialog = AddVendorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            vendor_data = dialog.vendor_data
            vendor_id = self.db_manager.add_vendor(
                vendor_data['name'],
                vendor_data['contact_person'],
                vendor_data['address'],
                vendor_data['phone'],
                vendor_data['email'],
                vendor_data['tax_info']
            )
            self.load_combo_data()
            # Select the newly added vendor
            for i in range(self.vendor_combo.count()):
                if self.vendor_combo.itemData(i) == vendor_id:
                    self.vendor_combo.setCurrentIndex(i)
                    break
            QMessageBox.information(self, "Success", "Vendor added successfully!")
    
    def validate_form(self):
        """Validate form data"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Product name is required!")
            self.name_edit.setFocus()
            return False
        
        if not self.barcode_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Barcode is required!")
            self.barcode_edit.setFocus()
            return False
        
        if self.stock_type_combo.currentIndex() <= 0 or not self.stock_type_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Stock type is required!")
            self.stock_type_combo.setFocus()
            return False
        
        if self.sale_price_spin.value() == 0:
            QMessageBox.warning(self, "Validation Error", "Sale price must be greater than 0!")
            self.sale_price_spin.setFocus()
            return False
        
        # Check if barcode already exists (when adding new product)
        if not self.product_id and self.db_manager.barcode_exists(self.barcode_edit.text().strip()):
            QMessageBox.warning(self, "Validation Error", "Barcode already exists!")
            self.barcode_edit.setFocus()
            return False
        
        return True
    
    def save_product(self):
        """Save product data"""
        if not self.validate_form():
            return
        
        # Get sub-quantity value (1 if checkbox not checked)
        sub_quantity = self.sub_quantity_spin.value() if self.sub_quantity_checkbox.isChecked() else 1
        
        # Prepare product data (removed description and image_path)
        product_data = (
            self.name_edit.text().strip(),
            self.barcode_edit.text().strip(),
            self.stock_type_combo.currentData(),
            self.quantity_spin.value(),
            sub_quantity,
            self.purchase_price_spin.value(),
            self.wholesale_price_spin.value(),
            self.sale_price_spin.value(),
            self.min_stock_spin.value(),
            self.manufacture_date.date().toString("yyyy-MM-dd"),
            self.expiry_date.date().toString("yyyy-MM-dd"),
            self.shelf_edit.text().strip(),
            self.category_combo.currentData(),
            "",  # description (empty)
            self.vendor_combo.currentData(),
            ""   # image_path (empty)
        )
        
        try:
            self.db_manager.save_product(product_data, self.product_id)
            if self.product_id:
                QMessageBox.information(self, "Success", "Product updated successfully!")
            else:
                QMessageBox.information(self, "Success", "Product saved successfully!")
                self.clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save product: {str(e)}")
    
    def clear_form(self):
        """Clear all form fields"""
        self.product_id = None
        self.name_edit.clear()
        self.barcode_edit.clear()
        self.stock_type_combo.setCurrentIndex(0)  # Reset to "-- Select Stock Type --"
        self.category_combo.setCurrentIndex(0)
        self.vendor_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(0)
        
        # Reset sub-quantity checkbox and value
        self.sub_quantity_checkbox.setChecked(False)
        self.sub_quantity_spin.setValue(1)
        self.sub_quantity_spin.setEnabled(False)
        
        self.purchase_price_spin.setValue(0)
        self.wholesale_price_spin.setValue(0)
        self.sale_price_spin.setValue(0)
        self.min_stock_spin.setValue(0)
        self.manufacture_date.setDate(QDate.currentDate())
        self.expiry_date.setDate(QDate.currentDate().addYears(1))
        self.shelf_edit.clear()
        
        # Reset the clicked_once flag for price fields
        self.purchase_price_spin.clicked_once = False
        self.wholesale_price_spin.clicked_once = False
        self.sale_price_spin.clicked_once = False
    
    def load_product(self, product_id):
        """Load product data for editing"""
        product = self.db_manager.get_product(product_id)
        if not product:
            QMessageBox.warning(self, "Error", "Product not found!")
            return
        
        self.product_id = product_id
        
        # Load product data into form
        self.name_edit.setText(product[1])
        self.barcode_edit.setText(product[2])
        
        # Set stock type
        if product[3]:  # stock_type
            for i in range(1, self.stock_type_combo.count()):  # Start from 1 to skip placeholder
                if self.stock_type_combo.itemData(i) == product[3]:
                    self.stock_type_combo.setCurrentIndex(i)
                    break
        
        self.quantity_spin.setValue(product[4])
        
        # Handle sub-quantity checkbox and value
        if product[5] and product[5] > 1:  # sub_quantity
            self.sub_quantity_checkbox.setChecked(True)
            self.sub_quantity_spin.setValue(product[5])
            self.sub_quantity_spin.setEnabled(True)
        else:
            self.sub_quantity_checkbox.setChecked(False)
            self.sub_quantity_spin.setValue(1)
            self.sub_quantity_spin.setEnabled(False)
        
        self.purchase_price_spin.setValue(product[6])
        self.wholesale_price_spin.setValue(product[7])
        self.sale_price_spin.setValue(product[8])
        self.min_stock_spin.setValue(product[9])
        
        # Set dates
        if product[10]:
            self.manufacture_date.setDate(QDate.fromString(product[10], "yyyy-MM-dd"))
        if product[11]:
            self.expiry_date.setDate(QDate.fromString(product[11], "yyyy-MM-dd"))
        
        self.shelf_edit.setText(product[12] or "")
        
        # Set category
        if product[13]:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == product[13]:
                    self.category_combo.setCurrentIndex(i)
                    break
        
        # Set vendor
        if product[15]:
            for i in range(self.vendor_combo.count()):
                if self.vendor_combo.itemData(i) == product[15]:
                    self.vendor_combo.setCurrentIndex(i)
                    break
        
        # Reset clicked_once flag for price fields
        self.purchase_price_spin.clicked_once = False
        self.wholesale_price_spin.clicked_once = False
        self.sale_price_spin.clicked_once = False

class ProductListWidget(QWidget):
    """Widget for displaying and managing product list"""
    
    product_selected = pyqtSignal(int)
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.count_label = None  # Initialize count label
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Search and filter controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(5)
        
        # Search
        search_label = QLabel("Search:")
        search_label.setFixedWidth(50)
        controls_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, barcode...")
        self.search_edit.textChanged.connect(self.filter_products)
        controls_layout.addWidget(self.search_edit)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.load_products)
        controls_layout.addWidget(refresh_btn)
        
        layout.addLayout(controls_layout)
        
        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(8)  # Reduced columns for smaller width
        self.products_table.setHorizontalHeaderLabels([
            'ID', 'Product Name', 'Barcode', 'Stock Type', 'Qty', 
            'Price (Rs)', 'Category', 'Min Stock'
        ])
        
        # Set column widths optimized for 700px width
        header = self.products_table.horizontalHeader()
        
        # Hide ID column
        self.products_table.setColumnHidden(0, True)
        
        # Set specific column widths
        self.products_table.setColumnWidth(1, 180)  # Product Name
        self.products_table.setColumnWidth(2, 100)  # Barcode
        self.products_table.setColumnWidth(3, 90)   # Stock Type
        self.products_table.setColumnWidth(4, 50)   # Quantity
        self.products_table.setColumnWidth(5, 80)   # Price
        self.products_table.setColumnWidth(6, 120)  # Category
        self.products_table.setColumnWidth(7, 70)   # Min Stock
        
        # Set resize modes
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Product Name
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Category
        
        # Style the table for smaller dialog
        self.products_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                font-size: 10px;
                padding: 6px;
                border: none;
                height: 25px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #e0e0e0;
                font-size: 11px;
            }
            QTableWidget::item:selected {
                background-color: #B3D9FF;
            }
        """)
        
        # Set row height
        self.products_table.verticalHeader().setDefaultSectionSize(28)
        self.products_table.verticalHeader().hide()
        
        # Connect double-click to edit
        self.products_table.doubleClicked.connect(self.edit_selected_product)
        
        layout.addWidget(self.products_table)
        
        # Action buttons - more compact
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        edit_btn = QPushButton("Edit Selected")
        edit_btn.setFixedSize(100, 30)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_product)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(80, 30)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #FF4444;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_product)
        button_layout.addWidget(delete_btn)
        
        # Add product count label
        self.count_label = QLabel("Products: 0")
        self.count_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        button_layout.addWidget(self.count_label)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_products(self):
        """Load products into the table"""
        products = self.db_manager.get_all_products()
        self.products_table.setRowCount(len(products))
        
        # Update product count if label exists
        if hasattr(self, 'count_label') and self.count_label:
            self.count_label.setText(f"Products: {len(products)}")
        
        for row, product in enumerate(products):
            # Adjust for reduced columns (removed vendor column)
            display_data = [
                product[0],  # ID
                product[1],  # Name
                product[2],  # Barcode
                product[3],  # Stock Type
                product[4],  # Quantity
                product[5],  # Sale Price
                product[6],  # Category
                product[8]   # Min Stock (skip vendor at index 7)
            ]
            
            for col, value in enumerate(display_data):
                if col == 5:  # Sale price
                    item = QTableWidgetItem(f"{value:.2f}" if value else "0.00")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif col == 6:  # Category name
                    item = QTableWidgetItem(str(value) if value else "Not Set")
                elif col in [4, 7]:  # Quantity and Min Stock
                    item = QTableWidgetItem(str(value) if value is not None else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item = QTableWidgetItem(str(value) if value is not None else "")
                
                # Highlight low stock items
                if col == 4 and display_data[7] and value and value <= display_data[7]:  # Quantity <= Min threshold
                    item.setBackground(Qt.GlobalColor.yellow)
                    item.setToolTip(f"Low Stock! Current: {value}, Minimum: {display_data[7]}")
                
                self.products_table.setItem(row, col, item)
    
    def filter_products(self):
        """Filter products based on search text"""
        search_text = self.search_edit.text().lower()
        visible_count = 0
        
        for row in range(self.products_table.rowCount()):
            visible = False
            if not search_text:  # Show all if search is empty
                visible = True
            else:
                # Search in visible columns (skip ID column)
                for col in range(1, self.products_table.columnCount()):
                    item = self.products_table.item(row, col)
                    if item and search_text in item.text().lower():
                        visible = True
                        break
            
            self.products_table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1
        
        # Update count label to show filtered results if label exists
        if hasattr(self, 'count_label') and self.count_label:
            if search_text:
                self.count_label.setText(f"Showing: {visible_count} of {self.products_table.rowCount()}")
            else:
                self.count_label.setText(f"Products: {self.products_table.rowCount()}")
    
    def edit_selected_product(self):
        """Edit the selected product"""
        current_row = self.products_table.currentRow()
        if current_row >= 0:
            product_id = int(self.products_table.item(current_row, 0).text())
            self.product_selected.emit(product_id)
    
    def delete_selected_product(self):
        """Delete the selected product"""
        current_row = self.products_table.currentRow()
        if current_row >= 0:
            product_name = self.products_table.item(current_row, 1).text()
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete '{product_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                product_id = int(self.products_table.item(current_row, 0).text())
                self.db_manager.delete_product(product_id)
                self.load_products()
                QMessageBox.information(self, "Success", "Product deleted successfully!")

class ProductManagementDialog(QDialog):
    """Main product management dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Product Management")
        self.setMinimumSize(700, 768)
        self.resize(700, 768)
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Add Product tab
        self.product_form = ProductFormWidget(self.db_manager)
        tab_widget.addTab(self.product_form, "Add/Edit Product")
        
        # Product List tab
        self.product_list = ProductListWidget(self.db_manager)
        self.product_list.product_selected.connect(self.edit_product)
        tab_widget.addTab(self.product_list, "Product List")
        
        layout.addWidget(tab_widget)
        self.setLayout(layout)
    
    def edit_product(self, product_id):
        """Switch to edit mode for the selected product"""
        self.product_form.load_product(product_id)
        # Switch to the Add/Edit tab
        tab_widget = self.findChild(QTabWidget)
        tab_widget.setCurrentIndex(0)

def main():
    """Test the product management dialog"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show dialog
    dialog = ProductManagementDialog()
    dialog.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()