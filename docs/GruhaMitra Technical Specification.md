# Technical Specification: GruhaMitra Platform

This document outlines the architectural blueprint, data layer strategy, technology stack, and cloud deployment topology for the **GruhaMitra** housing society management platform.

---

## 1. High-Level Architecture

GruhaMitra is built as a multi-tenant web application and Progressive Web App (PWA) using a modern decoupled architecture.

```mermaid
graph TD
    Client[Mobile/iPad PWA & Desktop Browser]
    Vercel[Vercel CDN / Frontend Host]
    FastAPI[FastAPI Backend Monolith]
    PostgreSQL[(PostgreSQL - Accounting DB)]
    MongoDB[(MongoDB - Domain DB)]
    WebPush[Web Push Service (APNs/FCM)]

    Client -->|Loads Static Assets| Vercel
    Client -->|HTTPS REST API / Authorization: Bearer| FastAPI
    FastAPI -->|Double-Entry Postings| PostgreSQL
    FastAPI -->|Tenant Domain & Logs| MongoDB
    FastAPI -->|Triggers Lock-Screen Alerts| WebPush
    WebPush -->|Delivers Notifications| Client
```

---

## 2. Technical Stack

| Component | Technology | Role / Details |
| :--- | :--- | :--- |
| **Frontend Core** | React 18 & JavaScript | Single-Page Application (SPA) logic. |
| **Frontend Build** | Vite 5 | Fast HMR, optimized esbuild bundler, and chunking. |
| **PWA Layer** | Service Worker API | Caches assets, handles background push notifications. |
| **QR Scanning** | Native BarcodeDetector API | Uses hardware-accelerated device camera (Safari/Chrome). |
| **Backend Core** | FastAPI (Python 3.11) | High-performance asynchronous ASGI framework. |
| **Authorization** | OAuth2 (JWT Bearer Tokens) | Secure stateless authentication. |
| **Push Engine** | `pywebpush` & `cryptography` | Encrypts and publishes push payloads using VAPID keys. |
| **Unit Testing** | `pytest` & `anyio` | Fast asynchronous test runner with tenant-isolation mocks. |

---

## 3. Split Database Strategy

GruhaMitra enforces strict data segregation between financial and flexible operational domain records:

### PostgreSQL (Financial Ledger)
* **Role:** Source of truth for financial balances and audit logs.
* **Architecture:** MitraBooks double-entry engine.
* **Key Invariants:** `sum(debits) - sum(credits) = 0`, immutable append-only ledger entries, tenant-scoped columns.
* **Tables:** Accounts, Journal Entries, Journal Lines, Financial Reports.

### MongoDB (Domain & Operational Storage)
* **Role:** Flexible document storage for unstructured or fast-changing domain objects.
* **Security:** All queries must be strictly tenant-isolated using index-optimized `tenant_id` scopes.
* **Collections:** Tenants, Users, Flat Registry, Complaints, Meetings, Visitor Registry, Staff Logs, Web Push Subscriptions.

---

## 4. Cloud Deployment & Hosting Topology

The production setup uses a serverless and managed infrastructure to scale independently:

```text
[Frontend Deployment: Vercel]
  └── Handles global CDN routing, SSL certification, and PWA manifest assets.
  └── Serves SPA code at: https://www.gruhamitra.sanmitratech.in/gruhamitra/

[Backend Deployment: Render / AWS ECS]
  └── Runs FastAPI inside a Docker container.
  └── Exposed via secured environment variables (JWT secrets, VAPID keys).
  └── Services API requests at: /api/v1/

[Database Layer: Managed Services]
  ├── MongoDB Atlas (Managed Document DB Cloud)
  └── Supabase / AWS RDS PostgreSQL (Managed Double-entry SQL Store)
```

---

## 5. Security & Isolation Controls

> [!IMPORTANT]
> **Tenant Isolation Invariant:** Every incoming request resolves a trusted `tenant_id` and `app_key` context from the authenticated JWT header. Access to flat, visitor, or billing data is blocked if the token's tenant identifier does not match the query scope.

* **API Authorization:** Tokens are passed strictly in the HTTP header: `Authorization: Bearer <JWT_TOKEN>`.
* **Zero Trust Gate:** The security guard interface is locked strictly to `/visitors`. Guards have no access to accounting, billing, or resident profiles.
* **Public Route Gate:** The public WhatsApp pass screen retrieves visitor data using a secure unauthenticated endpoint (`GET /visitors/public/{visitor_id}`) which exposes only the guest's name and validity time, omitting sensitive phone numbers or flat details.
