"""
app/middleware/__init__.py
===========================
Custom ASGI middleware package.

Middleware sits between the raw HTTP connection and the FastAPI application.
Every request passes through middleware IN ORDER (outermost first on the way
in, innermost first on the way out — like an onion).

Current middleware:
  - RequestLoggerMiddleware  → Logs method, path, status, response time

Future middleware to add:
  - RateLimitMiddleware      → Limit requests per IP/token
  - AuthMiddleware           → Optional: token validation at middleware level
  - CompressionMiddleware    → gzip responses (Starlette has this built-in)

Registration order in main.py matters:
    app.add_middleware(CORSMiddleware, ...)      # outer
    app.add_middleware(RequestLoggerMiddleware)  # inner
"""
