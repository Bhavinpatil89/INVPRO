# INVPRO: Ultra-Modern Enterprise Inventory Management

INVPRO is a high-performance, industry-grade Inventory Management System (IMS) designed for multi-branch retail enterprises. It features a sophisticated hierarchical authority model, real-time analytics, and a premium POS interface.

## 🚀 Key Features

- **Enterprise Hierarchy**: Full data isolation between HQ (Business Admins) and operational Nodes (Branch Managers/Staff).
- **Intelligent POS**: Feature-rich checkout terminal with real-time tax resolution and batch quantity adjustments.
- **Dynamic Tax Engine**: HQ-controlled tax policies with category-specific mapping and hierarchical resolution.
- **Strategic Analytics**: Visualized sales trends, profit metrics, and inventory health reports using matplotlib.
- **Node Management**: Scalable infrastructure to manage multiple stores under a single unified chain.
- **Import/Export**: Robust Excel integration for mass inventory updates and financial reporting.

## 🛠️ Technology Stack

- **Backend**: Python 3.x / Flask (API-First Design)
- **Database**: High-Performance SQLite / Data Access Layer (DAL)
- **Frontend**: Ultra-Modern CSR (Client-Side Rendering) architecture
  - **Logic**: Vanilla JavaScript (ES6+)
  - **Styling**: Tailwind CSS & Bootstrap 5 (Glassmorphism UI)
  - **Icons**: Bootstrap Icons
- **Visuals**: Matplotlib (Server-side generated) & Chart.js (Client-side interactive)
- **Data Engineering**: OpenPyXL for Excel logic

## 📂 Project Structure

```text
├── app/
│   ├── blueprints/    # Modular API & View Handlers (Auth, POS, Inventory, etc.)
│   ├── core/          # Engine Core (Database, Auth Utilities, Charting)
│   ├── services/      # Business Logic Layer (Strict Clean Architecture)
│   ├── static/        # Core Assets (CSS, JS, Images)
│   ├── templates/     # Static HTML Shells (CSR-ready)
│   └── utils/         # shared performance utilities
├── instance/          # Secure Local Database Instance
├── run.py             # Enterprise Application Entry Point
└── requirements.txt   # Core Dependency Manifest
```

## 🏗️ Architecture Design

INVPRO transition to a **Client-Side Rendering (CSR)** model ensures:
- **Blazing Fast Performance**: Minimal server-side rendering overhead.
- **Dynamic UX**: Real-time UI updates without full page reloads.
- **API Parity**: Every action in the system is backed by a secure RESTful API.
- **Modern State**: Uses `localStorage` and `sessionContext` for persistent auth and theme synchronization.

## ⚙️ Quick Start

1. **Clone & Setup**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Application**:
   ```bash
   python run.py
   ```

3. **Initialize Enterprise**:
   - Navigate to `/auth/register` to establish your first HQ Node.
   - Securely log in to access the Enterprise Dashboard.

## 🔒 Security & Roles

- **Business Admin (HQ)**: Full strategic authority over the chain. Can sync between nodes and manage global registry.
- **Branch Admin (Manager)**: Operational authority. Manages local stock, overrides prices, and views local analytics.
- **Branch Staff (Operator)**: High-speed POS access with restricted inventory visibility.

---
*Developed by Antigravity - Advanced Agentic Systems*
