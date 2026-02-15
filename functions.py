"""
E-Waste Management System - Core Functions
All database operations and business logic
"""

import sqlite3
import os

DB_PATH = "static/ewaste.db"

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize database with tables and sample data"""
    
    # Ensure static directory exists
    os.makedirs('static', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            disposal_recommendation TEXT NOT NULL,
            hazard_level TEXT NOT NULL,
            description TEXT,
            manufacturer TEXT,
            recyclable_components TEXT
        )
    ''')
    
    # Create recycling centers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recycling_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_name TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            zip_code TEXT,
            phone TEXT,
            email TEXT,
            accepted_items TEXT,
            operating_hours TEXT,
            website TEXT
        )
    ''')
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        # Insert sample products
        sample_products = [
            ('8901234567890', 'Samsung Galaxy S20', 'Smartphone', 'Recycle', 'High', 
             'Contains lithium-ion battery and rare earth metals', 'Samsung',
             'Battery, Screen, Circuit Board, Metals'),
            
            ('5901234123457', 'Dell XPS 13 Laptop', 'Laptop', 'Refurbish', 'High',
             'High-value components, repairable', 'Dell',
             'Battery, RAM, SSD, Display, Aluminum Body'),
            
            ('4006381333931', 'Apple iPhone 12', 'Smartphone', 'Recycle', 'High',
             'Contains valuable metals and hazardous materials', 'Apple',
             'Battery, Display, Motherboard, Camera Modules'),
            
            ('0012345678905', 'HP LaserJet Printer', 'Printer', 'Recycle', 'Medium',
             'Contains toner cartridges and plastic components', 'HP',
             'Toner Cartridge, Plastic Housing, Circuit Boards'),
            
            ('7501234567897', 'Sony LED TV 55 inch', 'Television', 'Recycle', 'Medium',
             'Contains LED panel and electronic components', 'Sony',
             'LED Panel, Circuit Boards, Plastic Housing, Metals'),
            
            ('6001234567894', 'Logitech Wireless Mouse', 'Peripherals', 'Dispose', 'Low',
             'Low-value item, minimal hazardous materials', 'Logitech',
             'Plastic, Small Battery, Circuit Board'),
            
            ('9001234567892', 'Canon DSLR Camera', 'Camera', 'Refurbish', 'Low',
             'High resale value, repairable', 'Canon',
             'Lens, Sensor, Battery, Circuit Boards'),
            
            ('3001234567899', 'Amazon Kindle E-Reader', 'E-Reader', 'Recycle', 'Low',
             'Contains e-ink display and battery', 'Amazon',
             'E-ink Display, Battery, Circuit Board'),
            
            ('2001234567898', 'Lenovo ThinkPad T480', 'Laptop', 'Refurbish', 'High',
             'Business-grade laptop, durable components', 'Lenovo',
             'Battery, RAM, HDD/SSD, Display, Keyboard'),
            
            ('1001234567891', 'Old CRT Monitor', 'Monitor', 'Dispose', 'Very High',
             'Contains hazardous lead and phosphor, requires special disposal', 'Various',
             'Lead-containing Glass, Phosphor Coating'),
        ]
        
        cursor.executemany('''
            INSERT INTO products (barcode, product_name, category, disposal_recommendation,
                                hazard_level, description, manufacturer, recyclable_components)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
        # Insert sample recycling centers
        sample_centers = [
            ('EcoTech Recycling Center', '123 Green Street', 'San Francisco', 'CA', 
             '94102', '415-555-0100', 'contact@ecotech.com',
             'Electronics, Batteries, Computers, Phones',
             'Mon-Sat: 8AM-6PM', 'www.ecotech-recycling.com'),
            
            ('TechWaste Solutions', '456 Recycle Avenue', 'Los Angeles', 'CA',
             '90001', '213-555-0200', 'info@techwaste.com',
             'All Electronics, Appliances',
             'Mon-Fri: 9AM-5PM', 'www.techwaste-solutions.com'),
            
            ('Green Electronics Recycling', '789 Eco Road', 'San Diego', 'CA',
             '92101', '619-555-0300', 'support@greenelectronics.com',
             'Computers, Phones, Tablets, Batteries',
             'Mon-Sun: 7AM-7PM', 'www.green-electronics.com'),
            
            ('E-Waste Warriors', '321 Sustainability Lane', 'San Jose', 'CA',
             '95101', '408-555-0400', 'help@ewastewarriors.com',
             'All Electronics, CRT Monitors, Printers',
             'Tue-Sat: 10AM-6PM', 'www.ewaste-warriors.com'),
            
            ('Circular Tech Recycling', '654 Future Boulevard', 'Sacramento', 'CA',
             '94203', '916-555-0500', 'info@circulartech.com',
             'Electronics, Appliances, Solar Panels',
             'Mon-Fri: 8AM-5PM, Sat: 9AM-2PM', 'www.circular-tech.com')
        ]
        
        cursor.executemany('''
            INSERT INTO recycling_centers (center_name, address, city, state, zip_code,
                                          phone, email, accepted_items, operating_hours, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_centers)
    
    conn.commit()
    conn.close()

def search_by_barcode(barcode):
    """Search for a product by barcode"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM products WHERE barcode = ?
    ''', (barcode,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def search_by_name(name):
    """Search for products by name (partial match)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM products WHERE product_name LIKE ?
    ''', (f'%{name}%',))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_all_centers(city=None):
    """Get all recycling centers, optionally filtered by city"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if city:
        cursor.execute('''
            SELECT * FROM recycling_centers WHERE city LIKE ?
        ''', (f'%{city}%',))
    else:
        cursor.execute('SELECT * FROM recycling_centers')
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def add_new_product(barcode, product_name, category, disposal, hazard,
                   description, manufacturer, components):
    """Add a new product to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO products (barcode, product_name, category, disposal_recommendation,
                                hazard_level, description, manufacturer, recyclable_components)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (barcode, product_name, category, disposal, hazard,
              description, manufacturer, components))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def classify_product(category, age_years, condition_score, working_status):
    """
    Classify a product and provide disposal recommendation
    Simple rule-based classification
    """
    
    # Category rules
    refurbish_categories = ['Laptop', 'Smartphone', 'Tablet', 'Camera', 'Gaming']
    recycle_categories = ['Television', 'Monitor', 'Printer', 'E-Reader', 'Battery']
    dispose_categories = ['Peripherals', 'Storage']
    
    # Age and condition thresholds
    if category in refurbish_categories:
        if age_years <= 3 and condition_score >= 7 and working_status == 'working':
            return 'Refurbish'
        else:
            return 'Recycle'
    
    elif category in recycle_categories:
        return 'Recycle'
    
    elif category in dispose_categories:
        if age_years > 5 or condition_score < 4:
            return 'Dispose'
        else:
            return 'Recycle'
    
    # Default
    return 'Recycle'

def get_disposal_guidelines(category, disposal_action):
    """Get detailed disposal guidelines for a product"""
    
    guidelines = {
        'preparation_steps': [
            "Backup and delete all personal data",
            "Perform factory reset if possible",
            "Remove SIM cards and memory cards"
        ],
        'what_to_remove': [],
        'where_to_take': [],
        'additional_tips': [
            "Get a receipt for disposal (for records)",
            "Check for manufacturer recycling programs",
            "Consider component harvesting for valuable parts"
        ]
    }
    
    # Category-specific removals
    if category in ['Smartphone', 'Laptop', 'Tablet', 'Camera']:
        guidelines['what_to_remove'].extend([
            "Battery (if removable)",
            "Storage devices (SSD/HDD)"
        ])
    
    # Action-specific locations
    if disposal_action == 'Refurbish':
        guidelines['where_to_take'] = [
            "Electronics resellers or trade-in programs",
            "Manufacturer buy-back programs",
            "Online marketplaces (after data wipe)",
            "Charity organizations"
        ]
    elif disposal_action == 'Recycle':
        guidelines['where_to_take'] = [
            "Authorized e-waste recycling centers",
            "Retailer take-back programs",
            "Municipal e-waste collection events"
        ]
    else:  # Dispose
        guidelines['where_to_take'] = [
            "Municipal hazardous waste facility",
            "E-waste collection points"
        ]
    
    return guidelines

def get_statistics():
    """Get database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total counts
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recycling_centers")
    total_centers = cursor.fetchone()[0]
    
    # Disposal stats
    cursor.execute("""
        SELECT disposal_recommendation, COUNT(*) 
        FROM products 
        GROUP BY disposal_recommendation
    """)
    disposal_stats = cursor.fetchall()
    
    # Hazard stats
    cursor.execute("""
        SELECT hazard_level, COUNT(*) 
        FROM products 
        GROUP BY hazard_level
    """)
    hazard_stats = cursor.fetchall()
    
    # Category stats
    cursor.execute("""
        SELECT category, COUNT(*) 
        FROM products 
        GROUP BY category 
        ORDER BY COUNT(*) DESC
    """)
    category_stats = cursor.fetchall()
    
    # Specific counts
    cursor.execute("SELECT COUNT(*) FROM products WHERE disposal_recommendation = 'Recycle'")
    recycle_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE hazard_level IN ('High', 'Very High')")
    high_hazard_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_products': total_products,
        'total_centers': total_centers,
        'disposal_stats': disposal_stats,
        'hazard_stats': hazard_stats,
        'category_stats': category_stats,
        'recycle_count': recycle_count,
        'high_hazard_count': high_hazard_count
    }