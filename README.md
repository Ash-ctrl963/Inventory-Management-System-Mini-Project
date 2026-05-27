# Inventory-Management-System-Mini-Project
#Inventory Management System

A feature-rich desktop application for managing inventory, sales, purchases,
and analytics — built with Python, CustomTkinter, and MySQL.

---

## Technology Stack and Tools Used

| Layer        | Technology              |
|--------------|-------------------------|
| Language     | Python 3.x              |
| GUI Framework| CustomTkinter           |
| Database     | MySQL 8.0               |
| Charts       | Matplotlib              |
| IDE          | VS Code / PyCharm       |

---

##  Features and Functionalities Implemented

-  User Authentication (Login/Register with role-based access)
-  Dashboard with real-time stats and KPIs
-  Product Management (Add, Edit, Delete, Search)
-  Point of Sale (POS) Module
-  Purchase Order Management
-  Sales Analytics with Matplotlib charts
-  Low-stock and Expiry Alerts
-  User Management (Admin controls)
-  AI Companion (smart restock suggestions using sales velocity)

---

##  Installation / Execution Steps

### Prerequisites
- Python 3.9+
- MySQL 8.0
- pip

### Steps

1. **Clone the repository**
```bash
   git clone https://github.com/YOUR_USERNAME/inventory-management-system.git
   cd inventory-management-system
```

2. **Install dependencies**
```bash
   pip install -r requirements.txt
```

3. **Set up the database**
   - Open MySQL and run the schema file:
```bash
   mysql -u root -p < database/schema.sql
```

4. **Configure DB credentials**
   - Open `src/db_config.py` and update:
```python
   HOST = "localhost"
   USER = "root"
   PASSWORD = "your_password"
   DATABASE = "inventory_db"
```

5. **Run the application**
```bash
   python src/main.py
```

---

##  Team Members

| Name           | Enrollment No. | Role               |
|----------------|----------------|--------------------|
| AISHWARY YADAV | EN23CS301081   | Lead Developer     |


---

##  Screenshots

### Login Screen
<img width="1662" height="1017" alt="image" src="https://github.com/user-attachments/assets/edd883d7-abad-4396-a630-89e05f028904" />
