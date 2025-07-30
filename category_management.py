# Add these imports to your existing imports at the top of main.py

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, 
                             QFrame, QScrollArea, QCheckBox, QComboBox,
                             QMessageBox, QSplitter, QHeaderView, QMenuBar,
                             QDialog, QDialogButtonBox, QTextEdit, QSpinBox,
                             QDoubleSpinBox, QInputDialog, QFileDialog,
                             QListWidget, QColorDialog)  # Add QListWidget, QColorDialog

from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QAction, QKeySequence, QTextDocument
import sqlite3
import json
import os
import tempfile
import subprocess
from product_management import DatabaseManager
class CategoryManagementDialog(QDialog):
    """Category Management Dialog for adding, editing, and deleting categories"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db_manager = parent.db_manager if parent else DatabaseManager()
        self.init_ui()
        self.load_categories()
        
    def init_ui(self):
        self.setWindowTitle("Category Management")
        self.setMinimumSize(1000, 700)
        self.resize(1000, 700)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left panel - Category list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Search categories
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search categories...")
        self.search_input.textChanged.connect(self.filter_categories)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # Category list
        self.category_list = QTableWidget()
        self.category_list.setColumnCount(4)
        self.category_list.setHorizontalHeaderLabels(['ID', 'Name', 'Color', 'Products'])
        
        # Set column widths
        header = self.category_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.category_list.setColumnWidth(0, 50)   # ID
        self.category_list.setColumnWidth(2, 80)   # Color
        self.category_list.setColumnWidth(3, 80)   # Products count
        
        # Hide ID column
        self.category_list.setColumnHidden(0, True)
        
        self.category_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.category_list.setAlternatingRowColors(True)
        self.category_list.itemSelectionChanged.connect(self.on_category_selected)
        
        left_layout.addWidget(self.category_list)
        
        # Category list buttons
        list_buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add Category")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #228B22; }
        """)
        self.add_btn.clicked.connect(self.add_category)
        
        self.edit_btn = QPushButton("✏️ Edit Category")
        self.edit_btn.setStyleSheet("""
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
        self.edit_btn.clicked.connect(self.edit_category)
        self.edit_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("🗑️ Delete Category")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC143C;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #B22222; }
        """)
        self.delete_btn.clicked.connect(self.delete_category)
        self.delete_btn.setEnabled(False)
        
        list_buttons_layout.addWidget(self.add_btn)
        list_buttons_layout.addWidget(self.edit_btn)
        list_buttons_layout.addWidget(self.delete_btn)
        list_buttons_layout.addStretch()
        
        left_layout.addLayout(list_buttons_layout)
        left_panel.setLayout(left_layout)
        
        # Right panel - Category details
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Category details form
        details_group = QFrame()
        details_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        details_group.setStyleSheet("QFrame { border: 2px solid #ccc; border-radius: 10px; padding: 10px; }")
        details_layout = QVBoxLayout()
        
        details_title = QLabel("Category Details")
        details_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px;")
        details_layout.addWidget(details_title)
        
        # Category name
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setMinimumWidth(80)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter category name...")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        details_layout.addLayout(name_layout)
        
        # Category color
        color_layout = QHBoxLayout()
        color_label = QLabel("Color:")
        color_label.setMinimumWidth(80)
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("#4A90E2")
        self.color_input.setMaximumWidth(100)
        
        self.color_preview = QLabel()
        self.color_preview.setMinimumSize(30, 30)
        self.color_preview.setMaximumSize(30, 30)
        self.color_preview.setStyleSheet("background-color: #4A90E2; border: 1px solid #333; border-radius: 5px;")
        
        self.color_picker_btn = QPushButton("Pick Color")
        self.color_picker_btn.setMaximumWidth(100)
        self.color_picker_btn.clicked.connect(self.pick_color)
        
        self.color_input.textChanged.connect(self.update_color_preview)
        
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_input)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_picker_btn)
        color_layout.addStretch()
        details_layout.addLayout(color_layout)
        
        # Predefined colors
        predefined_label = QLabel("Quick Colors:")
        details_layout.addWidget(predefined_label)
        
        colors_layout = QHBoxLayout()
        predefined_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", 
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#A29BFE",
            "#FD79A8", "#FDCB6E", "#6C5CE7", "#00B894"
        ]
        
        for color in predefined_colors:
            color_btn = QPushButton()
            color_btn.setMinimumSize(25, 25)
            color_btn.setMaximumSize(25, 25)
            color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 1px solid #333;
                    border-radius: 3px;
                }}
                QPushButton:hover {{
                    border: 2px solid #000;
                }}
            """)
            color_btn.clicked.connect(lambda checked, c=color: self.set_color(c))
            colors_layout.addWidget(color_btn)
        
        colors_layout.addStretch()
        details_layout.addLayout(colors_layout)
        
        # Product count info
        self.product_count_label = QLabel("Products in this category: 0")
        self.product_count_label.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        details_layout.addWidget(self.product_count_label)
        
        # Save/Cancel buttons
        form_buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Category")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #228B22; }
        """)
        self.save_btn.clicked.connect(self.save_category)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #5A6268; }
        """)
        self.cancel_btn.clicked.connect(self.clear_form)
        
        form_buttons_layout.addWidget(self.save_btn)
        form_buttons_layout.addWidget(self.cancel_btn)
        form_buttons_layout.addStretch()
        details_layout.addLayout(form_buttons_layout)
        
        details_layout.addStretch()
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        # Products in category
        products_group = QFrame()
        products_group.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        products_group.setStyleSheet("QFrame { border: 2px solid #ccc; border-radius: 10px; padding: 10px; }")
        products_layout = QVBoxLayout()
        
        products_title = QLabel("Products in Category")
        products_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; margin-bottom: 5px;")
        products_layout.addWidget(products_title)
        
        self.products_list = QListWidget()
        self.products_list.setMaximumHeight(150)
        products_layout.addWidget(self.products_list)
        
        products_group.setLayout(products_layout)
        right_layout.addWidget(products_group)
        
        right_panel.setLayout(right_layout)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        # Dialog buttons
        dialog_buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_categories)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.clicked.connect(self.close)
        
        dialog_buttons_layout.addWidget(refresh_btn)
        dialog_buttons_layout.addStretch()
        dialog_buttons_layout.addWidget(close_btn)
        
        # Final layout
        final_layout = QVBoxLayout()
        final_layout.addLayout(main_layout)
        final_layout.addLayout(dialog_buttons_layout)
        
        self.setLayout(final_layout)
        
        # Initialize form state
        self.current_category_id = None
        self.clear_form()
    
    def load_categories(self):
        """Load all categories into the table"""
        try:
            categories = self.db_manager.get_categories()
            self.category_list.setRowCount(len(categories))
            
            for row, (cat_id, cat_name, color_code) in enumerate(categories):
                # ID (hidden)
                self.category_list.setItem(row, 0, QTableWidgetItem(str(cat_id)))
                
                # Name
                self.category_list.setItem(row, 1, QTableWidgetItem(cat_name))
                
                # Color preview
                color_item = QTableWidgetItem()
                color_item.setBackground(QColor(color_code or "#4A90E2"))
                color_item.setText(color_code or "#4A90E2")
                self.category_list.setItem(row, 2, color_item)
                
                # Product count
                product_count = self.get_category_product_count(cat_id)
                self.category_list.setItem(row, 3, QTableWidgetItem(str(product_count)))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load categories: {str(e)}")
    
    def get_category_product_count(self, category_id):
        """Get number of products in a category"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM products WHERE category_id = ?', (category_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def filter_categories(self):
        """Filter categories based on search text"""
        search_text = self.search_input.text().lower()
        for row in range(self.category_list.rowCount()):
            name_item = self.category_list.item(row, 1)
            if name_item:
                should_show = search_text in name_item.text().lower()
                self.category_list.setRowHidden(row, not should_show)
    
    def on_category_selected(self):
        """Handle category selection"""
        current_row = self.category_list.currentRow()
        if current_row >= 0:
            # Get category data
            cat_id = int(self.category_list.item(current_row, 0).text())
            cat_name = self.category_list.item(current_row, 1).text()
            cat_color = self.category_list.item(current_row, 2).text()
            
            # Populate form
            self.current_category_id = cat_id
            self.name_input.setText(cat_name)
            self.color_input.setText(cat_color)
            self.update_color_preview()
            
            # Enable edit/delete buttons
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            
            # Load products in this category
            self.load_category_products(cat_id)
            
            # Update product count
            count = self.get_category_product_count(cat_id)
            self.product_count_label.setText(f"Products in this category: {count}")
    
    def load_category_products(self, category_id):
        """Load products for selected category"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM products WHERE category_id = ?', (category_id,))
            products = cursor.fetchall()
            conn.close()
            
            self.products_list.clear()
            for (product_name,) in products:
                self.products_list.addItem(product_name)
                
        except Exception as e:
            print(f"Error loading category products: {e}")
    
    def pick_color(self):
        """Open color picker dialog"""
        try:
            from PyQt6.QtWidgets import QColorDialog
            color = QColorDialog.getColor()
            if color.isValid():
                self.set_color(color.name())
        except ImportError:
            QMessageBox.warning(self, "Color Picker", "Color picker not available. Please enter hex color manually.")
    
    def set_color(self, color_code):
        """Set color from predefined color buttons"""
        self.color_input.setText(color_code)
        self.update_color_preview()
    
    def update_color_preview(self):
        """Update color preview based on input"""
        color_code = self.color_input.text()
        if color_code and color_code.startswith('#') and len(color_code) == 7:
            try:
                self.color_preview.setStyleSheet(f"background-color: {color_code}; border: 1px solid #333; border-radius: 5px;")
            except:
                self.color_preview.setStyleSheet("background-color: #4A90E2; border: 1px solid #333; border-radius: 5px;")
        else:
            self.color_preview.setStyleSheet("background-color: #4A90E2; border: 1px solid #333; border-radius: 5px;")
    
    def add_category(self):
        """Start adding new category"""
        self.clear_form()
        self.name_input.setFocus()
    
    def edit_category(self):
        """Edit selected category (form is already populated)"""
        if self.current_category_id:
            self.name_input.setFocus()
    
    def delete_category(self):
        """Delete selected category"""
        if not self.current_category_id:
            return
        
        current_row = self.category_list.currentRow()
        if current_row < 0:
            return
            
        cat_name = self.category_list.item(current_row, 1).text()
        product_count = self.get_category_product_count(self.current_category_id)
        
        # Confirm deletion
        if product_count > 0:
            reply = QMessageBox.question(
                self, "Delete Category",
                f"Category '{cat_name}' contains {product_count} products.\n\n"
                f"Deleting this category will set all its products to 'General' category.\n\n"
                f"Are you sure you want to delete this category?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        else:
            reply = QMessageBox.question(
                self, "Delete Category",
                f"Are you sure you want to delete category '{cat_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(self.db_manager.db_path)
                cursor = conn.cursor()
                
                # First, update products to use General category (ID = 1)
                if product_count > 0:
                    cursor.execute('UPDATE products SET category_id = 1 WHERE category_id = ?', 
                                 (self.current_category_id,))
                
                # Then delete the category
                cursor.execute('DELETE FROM categories WHERE id = ?', (self.current_category_id,))
                conn.commit()
                conn.close()
                
                QMessageBox.information(self, "Success", f"Category '{cat_name}' deleted successfully!")
                self.load_categories()
                self.clear_form()
                
                # Refresh parent window if available
                if self.parent_window:
                    self.parent_window.load_products_from_database()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete category: {str(e)}")
    
    def save_category(self):
        """Save category (add or edit)"""
        name = self.name_input.text().strip()
        color = self.color_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name is required!")
            return
        
        if not color:
            color = "#4A90E2"
        
        if not (color.startswith('#') and len(color) == 7):
            QMessageBox.warning(self, "Validation Error", "Color must be in hex format (e.g., #4A90E2)!")
            return
        
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            if self.current_category_id:
                # Update existing category
                cursor.execute('UPDATE categories SET name = ?, color_code = ? WHERE id = ?',
                             (name, color, self.current_category_id))
                message = f"Category '{name}' updated successfully!"
            else:
                # Add new category
                cursor.execute('INSERT INTO categories (name, color_code) VALUES (?, ?)',
                             (name, color))
                message = f"Category '{name}' added successfully!"
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", message)
            self.load_categories()
            self.clear_form()
            
            # Refresh parent window if available
            if self.parent_window:
                self.parent_window.load_products_from_database()
            
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Error", f"Category '{name}' already exists!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save category: {str(e)}")
    
    def clear_form(self):
        """Clear the form"""
        self.current_category_id = None
        self.name_input.clear()
        self.color_input.setText("#4A90E2")
        self.update_color_preview()
        self.products_list.clear()
        self.product_count_label.setText("Products in this category: 0")
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.category_list.clearSelection()

# Update the POSMainWindow method
def open_category_management(self):
    """Open category management dialog"""
    try:
        dialog = CategoryManagementDialog(self)
        dialog.exec()
        # Refresh products and categories after dialog closes
        self.load_products_from_database()
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open category management: {str(e)}")