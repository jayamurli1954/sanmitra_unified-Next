"""Business route sub-modules.

Each module here registers its handlers on the shared ``router`` defined in
``app.modules.business.router`` (imported for side effects at the end of that
module). Split out per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md to keep
the main router file maintainable; route paths and behaviour are unchanged.
"""
