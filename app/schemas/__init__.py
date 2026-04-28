# app/schemas/ — Pydantic models for API I/O.
#
# - Request models: <Resource>Create, <Resource>Update
# - Response models: <Resource>Read
#       Use `model_config = ConfigDict(from_attributes=True)` to map from ORM.
#
# Never return SQLAlchemy ORM instances from API endpoints — always map
# through a schema here. ORM objects can leak internal columns (audit
# fields, soft-delete flags, fk ids) and tightly couple the wire format
# to the storage schema.
