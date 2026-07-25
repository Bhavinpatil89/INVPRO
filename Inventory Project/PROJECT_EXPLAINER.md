# 🚀 INVPRO: Business Management System Explainer

This document explains **how the system works**, **why we built it this way**, and the **concepts (DSA/DBMS)** used behind the scenes.

---

### 🏛️ 1. The Business Hierarchy (Who is Who?)
We use a **Head Office -> Shop -> Staff** structure. 
- **Business HQ**: The owner who sees everything.
- **Shop (Branch)**: A physical location where items are sold.
- **Categories**: Groups like "Groceries" or "Electronics".

---

### 🔄 2. The Core Workflow (Step-by-Step)

| Step | Action | Why? | Example (Ex.) |
| :--- | :--- | :--- | :--- |
| **1** | **Setup Business** | To create the HQ Identity. | *Login as "Rahul's Mart" HQ.* |
| **2** | **Master List** | Create a central list of products. | *Add "Lays Chips" to the global list.* |
| **3** | **Open Shop** | Create branches to sell items. | *Create "Mumbai Branch" & "Delhi Branch".* |
| **4** | **Add Stock** | "Move" items from Master List to Shop. | *Add 50 pkts of Lays to Mumbai Shop.* |
| **5** | **Billing** | Sell items to customers. | *Customer buys 2 pkts; Stock becomes 48.* |

---

### 💻 3. The Technical Structure (Why this Code?)

Our code is separated so that if one thing breaks, the rest works:
1.  **`app/core/db.py` (The Soul)**: 
    *   **What**: Defines the Database tables.
    *   **DBMS Concept**: Uses **Relational Tables** with **Foreign Keys**.
    *   **Example**: If a Shop is deleted, we use `ON DELETE SET NULL` for bills so that **Sales History** is never lost!

2.  **`app/services/transaction.py` (The Brain)**: 
    *   **What**: Does the math for Billing.
    *   **DSA Concept**: Uses **Dictionaries (Hash Maps)** for fast lookup of product prices.
    *   **Logic**: It calculates `Subtotal + Tax = Total` and updates stock in one **Atomic Transaction** (all-or-nothing).

3.  **`app/templates` (The Face)**:
    *   **What**: The HTML pages you see.
    *   **Concept**: Uses **Client-Side Rendering (CSR)**. JavaScript (JS) fetches data silently without reloading the whole page.

---

### 🧠 4. Advanced Concepts (For your Sir)

#### **DBMS (Database Management System)**
*   **Normalized Data**: We don't store the same product name 100 times. We store it once and link it using IDs.
*   **ACID Properties**: We ensure that if the power goes out during a sale, your data doesn't get corrupted (either the sale is 100% done or 100% undone).
*   **Audit Snapshot**: When a bill is made, we save the **Store Name as a string**. Even if the store is deleted later, the bill still shows where it was sold!

#### **DSA (Data Structures & Algorithms)**
*   **Hash Maps (Dictionaries)**: Used to store Session Data for instant access to "Who is logged in?".
*   **List Iteration**: Used to loop through 1000s of products to find "Low Stock" items instantly.
*   **Time Series**: We use sorting algorithms to show you Sales Charts by Date.

---

### 📂 5. File Map (Which file does what?)
- `blueprints/auth.py`: **The Security Guard** (Handles Logins).
- `blueprints/inventory.py`: **The Warehouse Manager** (Moves items).
- `blueprints/billing.py`: **The Cashier** (Sales Counter).
- `services/reports.py`: **The Accountant** (Calculates Profits/Loss).

---

### 🌟 6. Why did we build it like this?
1.  **Scalable**: You can add 100 more shops without changing a single line of code.
2.  **History-Safe**: Deleting a branch doesn't delete your profit history.
3.  **Fast**: By using JavaScript (CSR), the app feels like a pro software, not a basic website.

---
*Created for: Project Demonstration & Exam Viva*
