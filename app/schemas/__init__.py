"""
app/schemas/__init__.py
========================
Pydantic schema (DTO) package.

Schemas are the data transfer objects (DTOs) that define:
  - What JSON shape a client must send in a request body
  - What JSON shape the API returns in a response

Schemas are NEVER the same as ORM models. They exist separately to:
  - Decouple the API contract from the database schema
  - Allow different response shapes for the same data (e.g., list vs detail)
  - Enforce input validation at the API boundary

Naming convention:
  - Request bodies: end in `Request`  (e.g., CreateCompanyRequest)
  - Response shapes: end in `Response` (e.g., CompanyResponse)
  - DB-internal shapes: end in `Schema` (e.g., CompanySchema)
"""
