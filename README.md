# 📦 Inventory Manager — Desktop App
### CustomTkinter Dark Mode  ·  Python + MySQL

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install customtkinter mysql-connector-python
```

### 2. Setup the database
Run `database_setup.sql` in MySQL Workbench or terminal:
```bash
mysql -u root -p < database_setup.sql
```

### 3. Configure database credentials
Open `db_config.py` and set your MySQL password:
```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_PASSWORD",   # ← change this
    "database": "inventory_db",
    "port":     3306,
}
```

### 4. Launch the app
```bash
python main.py
```

---

## 🔑 Default Login

| Username  | Password    | Role    |
|-----------|-------------|---------|
| admin     | admin123    | Admin   |
| manager1  | manager123  | Manager |
| staff1    | staff123    | Staff   |

---

## 📁 Files

```
inv_desktop/
├── main.py              ← Run this
├── db_config.py         ← Database credentials
├── database_setup.sql   ← Run once in MySQL
└── README.md
```

---

## ✨ Features

| Page | Features |
|------|----------|
| 🏠 Dashboard | Live stat cards, active alerts table |
| 📦 Products | Add/Edit/Delete, expiry date, color-coded status, Stock In/Out |
| 🛒 Point of Sale | Real-time cart, discount, receipt preview, auto stock deduction |
| 📋 Purchase Orders | Create POs, mark received, auto stock increment |
| 📊 Sales History | Filter Today/Week/Month/All, drill-down view |
| ⚠️ Alerts | Expired · Expiring ≤30d · Low Stock <5 · Out of Stock |
| 👥 Users | Admin-only CRUD, roles |

---

## 🎨 UI Design
- **Framework:** CustomTkinter (modern, native-looking)
- **Theme:** Dark mode with blue accent
- **Color codes:**
  - 🔴 Red rows = Expired products
  - 🟡 Yellow rows = Expiring soon or low stock
  - ✅ Normal = OK products
- Rounded cards, smooth hover effects, sidebar navigation

---

## ⚠️ Alert Logic

| Condition | Alert |
|-----------|-------|
| `expiry_date < today` | 🚨 EXPIRED — shown in red |
| `expiry_date ≤ today + 30d` | ⏳ Expiring soon — shown in yellow |
| `quantity < 5` | ⚠️ Low Stock warning |
| `quantity = 0` | 📭 Out of Stock |
| App startup | Popup if any expired or low-stock items |
